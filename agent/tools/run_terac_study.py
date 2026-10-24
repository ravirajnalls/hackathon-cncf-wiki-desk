"""Terac clarity A/B studies — the human-in-the-loop before/after.

Flow (each step is resumable; state lives in studies/round{N}.json):

  python -m agent.tools.run_terac_study launch --round 1   # original vs plain-language variant
  python -m agent.tools.run_terac_study collect --round 1  # pull submissions, score
  python -m agent.tools.run_terac_study apply              # agent rewrites wiki + style guide from feedback
  python -m agent.tools.run_terac_study launch --round 2   # original vs agent's rewrite
  python -m agent.tools.run_terac_study collect --round 2
  python -m agent.tools.run_terac_study report             # before/after -> output/terac_report.md

Terac's MCP authenticates with OAuth inside Claude Code, so every Terac call
runs through a `claude -p` subprocess (agent/claude_runner.py). Install once:
  claude mcp add --transport http terac https://terac.com/api/mcp
then run `/mcp` in Claude Code to sign in.

Terac MCP flow: terac_request_feasibility(role, task, count) -> poll
terac_get_feasibility_request until PRICED (cpi_usd) -> budget check ->
terac_launch_draft_opportunity(request_id) -> terac_get_submissions.
"""

import argparse
import json
import os
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
WIKI_DIR = PROJECT_ROOT / "wiki"
STUDIES_DIR = PROJECT_ROOT / "studies"
STYLE_GUIDE = PROJECT_ROOT / "agent" / "style_guide.md"
REPORT_FILE = PROJECT_ROOT / "output" / "terac_report.md"

DEFAULT_PAGE = "concepts/agent-sandbox-on-cncf.md"
ITEMS_PER_ROUND = int(os.environ.get("TERAC_ITEMS", "4"))
RESPONDENTS = int(os.environ.get("TERAC_COUNT", "15"))
ROUND_BUDGET_USD = float(os.environ.get("TERAC_ROUND_BUDGET_USD", "40"))
MAX_ITEM_CHARS = 700

ROLE = "General population adult. No technical or cloud computing background needed."

# Sections that are tables or meta, not prose explanations
SKIP_SECTIONS = {"Key patterns", "Disagreements"}


# ---------- wiki sections ----------

def split_sections(page_text: str) -> list[tuple[str, str]]:
    """Return [(heading, body)] for every '## ' section of a wiki page."""
    body = re.sub(r"\A---.*?---\s*", "", page_text, flags=re.S)
    parts = re.split(r"^## (.+)$", body, flags=re.M)
    return [(parts[i].strip(), parts[i + 1].strip()) for i in range(1, len(parts) - 1, 2)]


def readable(text: str) -> str:
    """Strip citation links and markdown so panelists see plain prose."""
    text = re.sub(r"\[▶[^\]]*\]\([^)]*\)", "", text)        # timestamp citations
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)    # other links -> label
    text = re.sub(r"[*_`#>]", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text).strip()
    return text[:MAX_ITEM_CHARS].rsplit(" ", 1)[0] + "…" if len(text) > MAX_ITEM_CHARS else text


def pick_items(page: str, n: int) -> list[dict]:
    text = (WIKI_DIR / page).read_text(encoding="utf-8")
    items = []
    for heading, body in split_sections(text):
        plain = readable(body)
        if heading in SKIP_SECTIONS or len(plain) < 200:
            continue
        items.append({"page": page, "section": heading, "original": plain})
    return items[:n]


def current_section_text(page: str, heading: str) -> str:
    text = (WIKI_DIR / page).read_text(encoding="utf-8")
    for h, body in split_sections(text):
        if h == heading:
            return readable(body)
    raise KeyError(f"Section '{heading}' not found in {page}")


# ---------- state ----------

def state_path(round_no: int) -> Path:
    return STUDIES_DIR / f"round{round_no}.json"


def load_state(round_no: int) -> dict:
    p = state_path(round_no)
    if not p.exists():
        sys.exit(f"No state for round {round_no}: run `launch --round {round_no}` first")
    return json.loads(p.read_text(encoding="utf-8"))


def save_state(round_no: int, state: dict):
    STUDIES_DIR.mkdir(exist_ok=True)
    state_path(round_no).write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def style_guide_text() -> str:
    """Lessons learned from Terac panels, injected into the compile prompt."""
    if not STYLE_GUIDE.exists():
        return ""
    return "\nWRITING STYLE (learned from reader clarity studies — follow it):\n" + STYLE_GUIDE.read_text(encoding="utf-8")


# ---------- study text ----------

def build_task_text(items: list[dict]) -> str:
    """Natural-language task for Terac panelists. Labels A/B are shuffled per item."""
    lines = [
        f"You'll read {len(items)} short explanations about cloud computing. Each one comes in two "
        "versions, A and B, that say roughly the same thing. No technical background is needed — "
        "we want to know which is easier for a normal reader to understand.",
        "",
        "For EACH item, reply on its own line in exactly this format:",
        "Item <number>: A=<1-5>, B=<1-5>, Easier=<A or B>, Confusing=<one sentence on what confused you most>",
        "(1 = very confusing, 5 = crystal clear)",
        "",
    ]
    for i, item in enumerate(items, 1):
        lines += [f"=== Item {i} — {item['section']} ===",
                  f"Version A:\n{item[item['labels']['A']]}", "",
                  f"Version B:\n{item[item['labels']['B']]}", ""]
    return "\n".join(lines)


def assign_labels(items: list[dict], seed: int):
    """Randomize which version shows as A, so position doesn't bias the result."""
    rng = random.Random(seed)
    for item in items:
        first, second = ("original", "variant") if rng.random() < 0.5 else ("variant", "original")
        item["labels"] = {"A": first, "B": second}


# ---------- Claude prompts ----------

def variants_prompt(items: list[dict]) -> str:
    payload = [{"i": i, "section": it["section"], "text": it["original"]} for i, it in enumerate(items, 1)]
    return f"""You are the editor of CNCF Wiki Desk. Rewrite each explanation below in plain language
for a general reader with no cloud background: short sentences, define every term the first time,
use one concrete analogy, keep every fact, keep it no longer than the original. Do not use tools.

{json.dumps(payload, indent=2, ensure_ascii=False)}

Output ONLY a JSON object: {{"variants": [{{"i": 1, "text": "..."}}, ...]}}"""


def launch_prompt(task_text: str, count: int, budget: float) -> str:
    return f"""You are launching a human study on Terac for CNCF Wiki Desk using the Terac MCP tools.

1. Call terac_request_feasibility with:
   role: {json.dumps(ROLE)}
   count: {count}
   task: the exact text between the markers below (do not edit it)
2. Poll terac_get_feasibility_request (or terac_list_opportunities / terac_get_context if that tool
   is missing) until status is PRICED and cpi_usd is set. Wait between polls; give up after ~10 minutes.
3. Budget check: total = cpi_usd x {count}. If total > {budget:.2f} USD, DO NOT launch.
4. Otherwise call terac_launch_draft_opportunity with the request_id.

<<<TASK
{task_text}
TASK>>>

Output ONLY a JSON object at the end:
{{"status": "launched" | "over_budget" | "failed", "request_id": "...", "opportunity_id": "...",
  "cpi_usd": 0.0, "total_usd": 0.0, "reason": "..."}}"""


def collect_prompt(state: dict) -> str:
    n_items = len(state["items"])
    return f"""Use the Terac MCP to fetch submissions for this study:
request_id: {state.get('request_id')}
opportunity_id: {state.get('opportunity_id')}

Call terac_get_submissions (try status APPROVED, and also pending/submitted ones if the tool allows).
Each submission is a panelist's free-text answer with lines like
"Item <n>: A=<1-5>, B=<1-5>, Easier=<A or B>, Confusing=<sentence>" for items 1..{n_items}.
Normalize every submission; skip items a panelist left out. Do not invent data.

Output ONLY a JSON object at the end:
{{"status": "ok", "opportunity_status": "...", "submissions": [
  {{"submission_id": "...", "answers": [{{"item": 1, "a": 4, "b": 5, "easier": "B", "confusing": "..."}}]}}
]}}"""


def apply_prompt(r1: dict) -> str:
    feedback = [{"section": it["section"], "page": it["page"],
                 "original_score": it.get("scores", {}).get("original"),
                 "plain_variant_score": it.get("scores", {}).get("variant"),
                 "plain_variant_win_rate": it.get("variant_win_rate"),
                 "complaints": it.get("complaints", [])[:8]} for it in r1["items"]]
    return f"""You are the editor of CNCF Wiki Desk. A Terac panel of general readers rated sections of
our wiki. Results (scores are average clarity 1-5):

{json.dumps(feedback, indent=2, ensure_ascii=False)}

1. Rewrite each listed section IN PLACE in wiki/<page> to fix what confused readers. Keep the
   '## ' heading text exactly the same, keep every fact, and keep every [▶ MM:SS](...) citation
   attached to the claim it supports. Use the plain-language style where it won.
2. Write agent/style_guide.md: 5-8 short, concrete writing rules learned from this feedback
   (these rules get injected into every future wiki compile).
3. Update clarity_score in the page frontmatter to the panel's average original score.
4. git add the changed files and commit: "wiki: rewrite from Terac round 1 feedback".

Output ONLY a JSON object at the end:
{{"status": "applied", "sections_rewritten": N, "rules": ["..."]}}"""


# ---------- scoring ----------

def score_round(state: dict, submissions: list[dict]):
    """Aggregate panel answers into per-item averages for each version."""
    for item in state["items"]:
        item["ratings"] = {"original": [], "variant": []}
        item["wins"] = {"original": 0, "variant": 0}
        item["complaints"] = []
    for sub in submissions:
        for ans in sub.get("answers", []):
            idx = int(ans.get("item", 0)) - 1
            if not 0 <= idx < len(state["items"]):
                continue
            item = state["items"][idx]
            for label in ("A", "B"):
                score = ans.get(label.lower())
                if isinstance(score, (int, float)) and 1 <= score <= 5:
                    item["ratings"][item["labels"][label]].append(score)
            easier = str(ans.get("easier", "")).strip().upper()[:1]
            if easier in ("A", "B"):
                item["wins"][item["labels"][easier]] += 1
            if ans.get("confusing"):
                item["complaints"].append(ans["confusing"])
    for item in state["items"]:
        item["scores"] = {k: round(sum(v) / len(v), 2) if v else None for k, v in item["ratings"].items()}
        votes = sum(item["wins"].values())
        item["variant_win_rate"] = round(item["wins"]["variant"] / votes, 2) if votes else None
    state["n_submissions"] = len(submissions)


def avg(values: list) -> float | None:
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 2) if values else None


# ---------- commands ----------

def cmd_launch(round_no: int, count: int, dry_run: bool):
    from agent.claude_runner import run_claude
    from agent.db import log_decision

    if state_path(round_no).exists() and load_state(round_no).get("status") == "launched":
        sys.exit(f"Round {round_no} is already launched; run collect")

    if round_no == 1:
        items = pick_items(DEFAULT_PAGE, ITEMS_PER_ROUND)
        result = run_claude(variants_prompt(items), timeout=300)
        variants = {v["i"]: v["text"] for v in result.get("variants", [])}
        if not all(i in variants for i in range(1, len(items) + 1)):
            sys.exit(f"Could not generate plain-language variants: {json.dumps(result)[:500]}")
        for i, item in enumerate(items, 1):
            item["variant"] = readable(variants[i])
        variant_kind = "plain-language variant written before any feedback"
    else:
        r1 = load_state(1)
        items = []
        for it in r1["items"]:
            items.append({"page": it["page"], "section": it["section"], "original": it["original"],
                          "variant": current_section_text(it["page"], it["section"])})
        variant_kind = "agent's rewrite after round 1 feedback"

    assign_labels(items, seed=round_no)
    task_text = build_task_text(items)
    state = {"round": round_no, "variant_kind": variant_kind, "count": count,
             "created_at": datetime.now(timezone.utc).isoformat(), "items": items, "task_text": task_text,
             "status": "draft"}
    save_state(round_no, state)

    if dry_run:
        print(task_text)
        print(f"\n[dry run] {len(items)} items, {count} respondents. Saved {state_path(round_no)}")
        return

    result = run_claude(launch_prompt(task_text, count, ROUND_BUDGET_USD), timeout=900)
    state.update({k: result.get(k) for k in ("request_id", "opportunity_id", "cpi_usd", "total_usd", "reason")})
    state["status"] = result.get("status", "failed")
    save_state(round_no, state)
    log_decision(
        f"Terac round {round_no}: {state['status']}",
        f"Clarity A/B on {len(items)} sections: original vs {variant_kind}",
        f"{count} general-population ratings within budget ${ROUND_BUDGET_USD:.0f}",
        json.dumps({k: result.get(k) for k in ("cpi_usd", "total_usd", "reason")}),
    )
    print(json.dumps(result, indent=2))


def cmd_collect(round_no: int):
    from agent.claude_runner import run_claude
    from agent.db import get_db

    state = load_state(round_no)
    result = run_claude(collect_prompt(state), timeout=300)
    submissions = result.get("submissions")
    if submissions is None:
        sys.exit(f"Could not read submissions: {json.dumps(result)[:500]}")
    score_round(state, submissions)
    state["opportunity_status"] = result.get("opportunity_status")
    state["collected_at"] = datetime.now(timezone.utc).isoformat()
    save_state(round_no, state)

    with get_db() as conn:
        conn.execute("DELETE FROM studies WHERE version LIKE ?", (f"r{round_no}-%",))
        for item in state["items"]:
            for kind in ("original", "variant"):
                conn.execute(
                    "INSERT INTO studies (page, version, terac_id, score, n) VALUES (?, ?, ?, ?, ?)",
                    (f"{item['page']}#{item['section']}", f"r{round_no}-{kind}",
                     state.get("opportunity_id") or state.get("request_id"),
                     item["scores"][kind], len(item["ratings"][kind])),
                )

    print(f"Round {round_no}: {state['n_submissions']} submissions")
    for item in state["items"]:
        print(f"  {item['section'][:40]:40}  original={item['scores']['original']}  "
              f"variant={item['scores']['variant']}  variant_win_rate={item['variant_win_rate']}")


def cmd_apply():
    from agent.claude_runner import run_claude
    from agent.db import log_decision

    r1 = load_state(1)
    if "scores" not in r1["items"][0]:
        sys.exit("Round 1 has no results yet: run `collect --round 1` first")
    result = run_claude(apply_prompt(r1), timeout=600)
    log_decision(
        "Rewrote wiki sections from Terac round 1 feedback",
        f"Panel avg clarity: original {avg([i['scores']['original'] for i in r1['items']])}, "
        f"plain variant {avg([i['scores']['variant'] for i in r1['items']])}",
        "Round 2 clarity beats round 1 original",
        json.dumps(result)[:300],
    )
    print(json.dumps(result, indent=2))


def cmd_report():
    r1 = load_state(1)
    r2 = load_state(2) if state_path(2).exists() else None
    before = avg([i.get("scores", {}).get("original") for i in r1["items"]])
    plain = avg([i.get("scores", {}).get("variant") for i in r1["items"]])
    after = avg([i.get("scores", {}).get("variant") for i in r2["items"]]) if r2 else None
    win = avg([i.get("variant_win_rate") for i in r2["items"]]) if r2 else None

    lines = [
        "# Terac clarity study — before and after", "",
        f"Panels of general readers on Terac rated wiki sections 1 (confusing) to 5 (crystal clear).", "",
        "| Metric | Value |", "| --- | --- |",
        f"| Before: original wiki sections (round 1) | {before} |",
        f"| Plain-language variant, no feedback yet (round 1) | {plain} |",
        f"| After: agent's rewrite from feedback (round 2) | {after if after is not None else 'pending'} |",
        f"| Readers preferring the rewrite over the original (round 2) | "
        f"{f'{win:.0%}' if win is not None else 'pending'} |",
        f"| Submissions | round 1: {r1.get('n_submissions', 0)}, round 2: {r2.get('n_submissions', 0) if r2 else 'pending'} |",
        "", "## Per section", "",
        "| Section | Before | After | Top complaint (round 1) |", "| --- | --- | --- | --- |",
    ]
    r2_by_section = {i["section"]: i for i in r2["items"]} if r2 else {}
    for item in r1["items"]:
        after_item = r2_by_section.get(item["section"], {})
        complaint = (item.get("complaints") or ["—"])[0].replace("|", "/")
        lines.append(f"| {item['section']} | {item.get('scores', {}).get('original')} | "
                     f"{after_item.get('scores', {}).get('variant', '—')} | {complaint} |")
    if STYLE_GUIDE.exists():
        lines += ["", "## Rules the agent learned (now part of every compile)", "",
                  STYLE_GUIDE.read_text(encoding="utf-8").strip()]

    REPORT_FILE.parent.mkdir(exist_ok=True)
    REPORT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="Terac clarity A/B studies")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_launch = sub.add_parser("launch")
    p_launch.add_argument("--round", type=int, choices=[1, 2], required=True)
    p_launch.add_argument("--count", type=int, default=RESPONDENTS)
    p_launch.add_argument("--dry-run", action="store_true", help="build the study text without calling Terac")
    p_collect = sub.add_parser("collect")
    p_collect.add_argument("--round", type=int, choices=[1, 2], required=True)
    sub.add_parser("apply")
    sub.add_parser("report")
    args = parser.parse_args()

    if args.cmd == "launch":
        cmd_launch(args.round, args.count, args.dry_run)
    elif args.cmd == "collect":
        cmd_collect(args.round)
    elif args.cmd == "apply":
        cmd_apply()
    else:
        cmd_report()


if __name__ == "__main__":
    sys.path.insert(0, str(PROJECT_ROOT))
    main()
