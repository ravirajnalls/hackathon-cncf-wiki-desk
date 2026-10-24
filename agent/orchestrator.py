"""Python orchestrator — polls Whop, spawns Claude Code subprocess to fulfill.

Architecture:
  Python: polling loop, state machine, SQLite, resumability
  Claude subprocess (via `claude -p`): fulfillment using native MCP tools
    - Whop MCP: poll orders, send messages to buyers
    - Terac MCP: launch clarity A/B studies
    - Exa: discover KubeCon/CNCF talks
    - File tools: write/update wiki pages
    - Shell: fetch transcripts, publish site, git commit
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env before importing tools, which read env vars at import time
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from agent.db import record_order, mark_delivered, log_decision, get_order, set_order_status
from agent.tools.poll_orders import poll_orders as whop_poll
from agent.claude_runner import run_claude
from agent.tools.run_terac_study import style_guide_text
from agent.tools.compile_pages import _slugify
from agent.tools.publish_wiki import get_page_url


def build_fulfillment_prompt(order: dict) -> str:
    """Build the prompt for the Claude fulfillment subprocess."""
    whop_id = order.get("id", "unknown")
    topic = order.get("metadata", {}).get("topic", "")
    created_at = order.get("created_at", "")
    product_id = os.environ.get("WHOP_PRODUCT_ID", "prod_65oqcxlhZM93U")
    slug = _slugify(topic) if topic else ""
    page_url = get_page_url(slug) if topic else ""

    if not topic:
        return f"""You are fulfilling a CNCF Wiki Desk order via MCP tools.

Order ID: {whop_id}
Topic: NOT YET PROVIDED

Use the Whop MCP to send this message to the buyer:
"What cloud-native topic would you like the wiki on? (e.g. Cilium, Gateway API, Argo CD)"

Then report back that we're waiting for the topic."""

    return f"""You are the fulfillment agent for CNCF Wiki Desk — an autonomous, agent-run company.
Your job: research a cloud-native topic, compile a cited wiki, and deliver it to the buyer.

=== ORDER ===
Order ID: {whop_id}
Topic: {topic}
Product ID: {product_id}
Working directory: {PROJECT_ROOT}

=== YOUR TOOLS ===
You have access to:
- Whop MCP: whop_get_orders, whop_send_message, whop_update_product, etc.
- Exa: search for KubeCon/CNCF talks (via exa_py or Exa MCP)
- File tools: read, write, edit files in {PROJECT_ROOT}
- Shell: run commands (python, git, pip)

=== 6 STEPS — DO ALL OF THEM, IN ORDER ===

STEP 1 — DISCOVER SOURCES
Find 8-10 KubeCon/CNCF talks and official docs on "{topic}".
Use Exa search: query = "CNCF {topic} KubeCon talk OR keynote OR official documentation"
Prefer YouTube talks and CNCF blog/docs.

STEP 2 — INGEST TRANSCRIPTS
For each YouTube URL found, run this shell command:
  python -c "from agent.tools.get_transcript import get_transcript; print(get_transcript('URL'))"
This stores timestamped chunks in memory.db automatically. Skip videos that fail.

STEP 3 — COMPILE WIKI PAGE
Run this shell command to generate the wiki page:
  python -c "from agent.tools.compile_pages import compile_pages, write_page; import json; ..."
Or write the page directly to wiki/concepts/{slug}.md using the file tools.
Then add or update its line in wiki/index.md: "- [Title](concepts/{slug}.md) — one-line summary".

The page MUST have:
- YAML frontmatter: title, summary, sources, updated, clarity_score
- Every claim ends with a clickable timestamp link: [▶ MM:SS](https://youtube.com/watch?v=VID&t=SECONDSs)
- Disagreements section if multiple speakers conflict
{style_guide_text()}

STEP 4 — PUBLISH (commit + push; the hosted site rebuilds from GitHub)
Run:
  cd {PROJECT_ROOT}
  python -c "from agent.tools.publish_wiki import publish_wiki; print(publish_wiki())"
  git add wiki
  git commit -m "wiki: {topic} (order {whop_id[:8]})"
  git push
If mkdocs reports errors in the new page, fix them before pushing.

STEP 5 — LOG DECISION
Log your key decisions (sources chosen, what you reused from existing pages):
  python -c "from agent.db import log_decision; log_decision('...', '...', '...', '...')"

STEP 6 — DELIVER TO BUYER
Use Whop MCP to send the buyer this message:
  "✅ Your CNCF Wiki on '{topic}' is ready!

   📖 View it: {page_url}

   Every claim is cited with a clickable video timestamp. The page may take a minute to go live."

=== REPORT BACK ===
When done, output a JSON summary:
{{"status": "fulfilled", "order_id": "{whop_id}", "topic": "{topic}", "pages_created": N, "sources_used": N}}
If you cannot complete, output: {{"status": "failed", "reason": "..."}}
"""


def spawn_claude_fulfillment(order: dict) -> dict:
    """Spawn a Claude Code subprocess to fulfill an order."""
    prompt = build_fulfillment_prompt(order)
    return run_claude(prompt, timeout=600)  # 10 min max per order


def fulfill_order(order: dict) -> dict:
    """Fulfill a single order: record, spawn Claude subprocess, track result."""
    whop_id = order.get("id", "")
    topic = order.get("metadata", {}).get("topic", "")
    paid_at = order.get("created_at", datetime.utcnow().isoformat())

    record_order(whop_id, topic or "unknown", paid_at)
    set_order_status(whop_id, "in_progress")
    log_decision(
        f"Started fulfillment for order {whop_id[:8]}",
        f"Topic: {topic or 'TBD'}",
        "Claude subprocess fulfills and delivers wiki",
    )

    result = spawn_claude_fulfillment(order)

    if not topic:
        # Subprocess only asked the buyer for a topic; retry once one arrives
        set_order_status(whop_id, "awaiting_topic")
    elif result.get("status") == "fulfilled":
        mark_delivered(whop_id, get_page_url(_slugify(topic)), cost_usd=3.0)
        log_decision(
            f"Order {whop_id[:8]} fulfilled",
            f"Topic: {topic}",
            "Delivered",
            result.get("status"),
        )
    else:
        set_order_status(whop_id, "failed")
        log_decision(
            f"Order {whop_id[:8]} FAILED",
            result.get("reason", result.get("status", "unknown")),
            "Delivered",
            f"FAILED: {json.dumps(result)[:200]}",
        )

    return result


def should_fulfill(order: dict) -> bool:
    """Skip orders already handled, so each poll doesn't re-run fulfillment."""
    row = get_order(order.get("id", ""))
    if row is None:
        return True
    if row["status"] == "awaiting_topic":
        return bool(order.get("metadata", {}).get("topic"))
    # delivered, in_progress and failed orders are left alone; failed ones need a manual look
    return row["status"] == "pending"


def run_loop(poll_interval: int = 30):
    """Main polling loop — check for new orders, spawn Claude to fulfill."""
    log_decision(
        "Orchestrator started",
        "Python loop polling Whop, spawning Claude subprocesses for fulfillment",
        "All paid orders fulfilled autonomously",
    )

    print(f"[{datetime.utcnow().isoformat()}] CNCF Wiki Desk orchestrator started")
    print(f"  Polling Whop every {poll_interval}s")
    print(f"  Project: {PROJECT_ROOT}")
    print()

    while True:
        try:
            orders = whop_poll()
            paid = [o for o in orders if o.get("status") == "paid" and should_fulfill(o)]

            if paid:
                print(f"  [{datetime.utcnow().strftime('%H:%M:%S')}] {len(paid)} new paid order(s)")
                for order in paid:
                    whop_id = order.get("id", "?")
                    topic = order.get("metadata", {}).get("topic", "TBD")
                    print(f"    → Fulfilling {whop_id[:12]}... (topic: {topic})")
                    result = fulfill_order(order)
                    print(f"    ← Result: {result.get('status')}")
            else:
                print(f"  [{datetime.utcnow().strftime('%H:%M:%S')}] No new orders", end="\r")

        except KeyboardInterrupt:
            print("\n\nShutting down...")
            log_decision("Orchestrator stopped", "Keyboard interrupt", "clean shutdown", "stopped")
            break
        except Exception as e:
            print(f"  ERROR: {e}")
            log_decision("Loop error", str(e), "recover", "retrying")

        time.sleep(poll_interval)


if __name__ == "__main__":
    from agent.tools.write_copy import write_copy
    write_copy(str(PROJECT_ROOT / "output"))
    print("Marketing copy written.\n")
    run_loop()
