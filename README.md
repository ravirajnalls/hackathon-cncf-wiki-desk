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
    run_terac_study.py # clarity A/B studies
    write_copy.py      # marketing copy
    log_decision.py    # decision memory
wiki/                  # the product + semantic memory (git)
memory.db              # SQLite episodic + operational memory
```
