# CNCF Wiki Desk

Agent-run company that sells on-demand, cited wikis on cloud-native topics.

- Buyer pays $3 on Whop, names a topic
- Agent researches KubeCon/CNCF talks via Exa
- Agent compiles a wiki with clickable video timestamps
- Agent delivers the link back through Whop
- Every order makes the next one faster (compounding memory)

## Setup

```bash
pip install -r .requirements
cp .env.example .env   # fill in keys
python -m agent.orchestrator
```

## Terac clarity study (human in the loop)

General-population panelists on Terac compare wiki sections in two versions and rate
clarity 1-5. The agent rewrites the wiki from their feedback, learns writing rules
(`agent/style_guide.md`, injected into every future compile), and a second round
measures the result.

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

Round state is saved in `studies/round{N}.json`, scores in the `studies` table.

## Project structure

```
agent/
  orchestrator.py      # main tool-calling loop
  tools/
    poll_orders.py     # Whop order intake
    find_sources.py    # Exa discovery
    get_transcript.py  # YouTube captions + timestamps
    compile_pages.py   # wiki ops (create/update/flag_conflict)
    publish_wiki.py    # build static MkDocs site
    deliver.py         # send link via Whop
    run_terac_study.py # Terac clarity A/B studies (launch/collect/apply/report)
  claude_runner.py     # runs `claude -p` with MCP tools, parses its JSON result
    write_copy.py      # marketing copy
    log_decision.py    # decision memory
wiki/                  # the product + semantic memory (git)
memory.db              # SQLite episodic + operational memory
```
