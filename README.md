# CNCF Wiki Desk

**An agent-run research desk.** Pay $3 on Whop, pick a CNCF open source project (Kubernetes,
Cilium, Argo, OpenTelemetry, Prometheus, Envoy, Istio, Kyverno, kagent, Agent Substrate, or any
other project in the CNCF landscape), and an agent researches KubeCon/CNCF talks and delivers a wiki where every claim links to the
exact moment in the talk. Every order makes the next one faster and better.

Built solo for Terac's Zero Human Company Hackathon NYC (Oct 24, 2026).

- **Buy:** https://whop.com/github-9154/cloud-native-wiki-on-demand
- **Live wiki:** https://ravirajnalls.github.io/hackathon-cncf-wiki-desk/
- **Terac before/after:** [`output/terac_report.md`](output/terac_report.md)
- **Agent decision log:** [`wiki/log.md`](wiki/log.md)

## What the agent does (no humans)

| Job | How |
| --- | --- |
| Sell | Whop checkout; the orchestrator polls paid orders and asks for a topic if missing |
| Scope | The topic is matched against the 231 CNCF projects in the official landscape (`agent/tools/cncf_projects.py`); anything else gets a polite reply with options |
| Research | CNCF sources only: Exa searches the CNCF YouTube channel (KubeCon + CloudNativeCon) plus cncf.io, kubernetes.io and the project's own docs; captions are pulled with timestamps into SQLite FTS5 |
| Build | Claude compiles a wiki page: YAML frontmatter, a `[▶ MM:SS]` citation on every claim, a Disagreements section when talks conflict |
| Publish & deliver | Commits and pushes the wiki (GitHub Pages rebuilds the MkDocs site), then messages the buyer the link on Whop |
| Improve with humans | Terac general-population panels rate clarity; the agent rewrites the wiki and learns writing rules from their feedback |
| Marketing & legal | Writes landing copy, the launch post, terms, refund policy and CNCF source attribution (`output/`) |
| Decide | Every choice is logged with reason, expectation and outcome, mirrored to `wiki/log.md` |

## Memory that compounds

- **Semantic memory = the product:** markdown wiki in git (`wiki/`). `index.md` lists every
  page; the compiler reads it to update existing pages instead of re-researching. Each
  compile is a commit, so "the wiki updated itself" is a visible diff.
- **Episodic memory:** SQLite (`memory.db`) holds orders, ingested talks, transcript chunks,
  Terac study scores and decisions. Talks are never ingested twice.
- **Learned style:** `agent/style_guide.md`, written from Terac feedback, is injected into
  every future compile.

## Human in the loop: Terac clarity study

1. **Round 1:** panelists compare wiki sections in two versions (original vs plain-language),
   rate each 1–5, pick the easier one and say what confused them. A/B order is randomized.
2. **Apply:** the agent rewrites those sections in place (keeping every citation) and writes
   writing rules to `agent/style_guide.md`.
3. **Round 2:** original vs the agent's rewrite. The headline metric is average clarity
   before vs after.

```bash
claude mcp add --transport http terac https://terac.com/api/mcp   # then /mcp to sign in
python -m agent.tools.run_terac_study launch --round 1 --dry-run   # preview the study text
python -m agent.tools.run_terac_study launch --round 1             # quote, budget check, launch
python -m agent.tools.run_terac_study collect --round 1            # once submissions arrive
python -m agent.tools.run_terac_study apply                        # agent rewrites wiki + style guide
python -m agent.tools.run_terac_study launch --round 2
python -m agent.tools.run_terac_study collect --round 2
python -m agent.tools.run_terac_study report                       # output/terac_report.md
```

The agent refuses to launch a round quoted above `TERAC_ROUND_BUDGET_USD` (default $40).
Round state is saved in `studies/round{N}.json`, scores in the `studies` table.

## Run it

```bash
pip install -r .requirements
cp .env.example .env                 # Whop key/IDs, Exa key, WIKI_BASE_URL
claude mcp list                      # Whop, Terac and Exa MCP servers must be connected
python -m agent.orchestrator         # polls Whop and fulfills orders
streamlit run dashboard.py           # orders, revenue, clarity before/after, decisions, wiki diff
mkdocs serve                         # preview the wiki site locally
python -m agent.tools.verify_citations   # check every timestamp citation
python -m agent.seed_wiki                # agent researches + publishes the Agent Sandbox page cluster
```

**Deploy the wiki:** GitHub Pages builds the MkDocs site on every push to `main`
(`.github/workflows/pages.yml`). The agent pushes after each order, so each new page goes
live a minute later.

## Use it inside Claude (MCP server)

`mcp_server/wiki_desk_mcp.py` lets Claude search and read the wiki, and order new topics:
`list_topics`, `search_wiki`, `get_page` (markdown with timestamp citations) and `order_wiki`
(returns the Whop checkout link).

```bash
claude mcp add wiki-desk -- uvx --with "mcp>=1.2,<2" --with requests python mcp_server/wiki_desk_mcp.py
```

## Architecture

Python owns the loop, state and resumability; a headless Claude Code subprocess
(`claude -p`) does the research and writing with MCP tools (Whop, Terac, Exa).

```
Whop order ──> orchestrator.py (poll, dedupe, state in SQLite)
                   │
                   └─> claude -p (claude_runner.py)
                         ├─ Exa: find talks          ─> find_sources.py
                         ├─ captions -> SQLite FTS5  ─> get_transcript.py
                         ├─ compile wiki page        ─> wiki/concepts/*.md (+ style_guide.md)
                         ├─ mkdocs build, git push   ─> publish_wiki.py ─> GitHub Pages
                         ├─ log decisions            ─> memory.db + wiki/log.md
                         └─ Whop: message buyer the link
Terac panels <── run_terac_study.py (launch / collect / apply / report)
```

## Project structure

```
agent/
  orchestrator.py        # order loop: poll Whop, dedupe, spawn Claude to fulfill
  claude_runner.py       # runs `claude -p` with MCP tools, parses its JSON result
  db.py                  # SQLite schema + decision log export
  style_guide.md         # writing rules learned from Terac (created by `apply`)
  tools/
    poll_orders.py       # Whop order intake
    cncf_projects.py     # CNCF landscape: project matching + allowed source domains
    find_sources.py      # Exa discovery (CNCF YouTube channel + CNCF/project docs)
    get_transcript.py    # YouTube captions + timestamps
    compile_pages.py     # wiki ops (create/update/flag_conflict)
    publish_wiki.py      # MkDocs build + public page URLs
    deliver.py           # send link via Whop
    run_terac_study.py   # Terac clarity A/B studies
    verify_citations.py  # check timestamp citations against transcripts
    write_copy.py        # marketing + policy copy
    log_decision.py      # decision memory
dashboard.py             # Streamlit demo dashboard
wiki/                    # the product + semantic memory (git)
studies/                 # Terac round state
output/                  # landing copy, launch post, policy, Terac report
memory.db                # SQLite episodic + operational memory (not committed)
```

Wiki content is compiled from public KubeCon/CNCF talks, and every claim links to its
source. CNCF, KubeCon and project names are trademarks of the Linux Foundation.
