"""Have the agent research and publish a cluster of related wiki pages (no buyer, no Whop).

Grows the wiki around a hub page so orders on nearby topics reuse existing memory.

  python -m agent.seed_wiki                      # default Agent Sandbox cluster
  python -m agent.seed_wiki "gVisor" "Kata Containers"
  python -m agent.seed_wiki --list               # show the default topics
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent.claude_runner import run_claude
from agent.db import log_decision
from agent.tools.compile_pages import _slugify
from agent.tools.publish_wiki import get_page_url
from agent.tools.run_terac_study import style_guide_text

HUB = "concepts/agent-sandbox-on-cncf.md"

# Subtopics a reader of the Agent Sandbox page asks about next
AGENT_SANDBOX_TOPICS = [
    "Kubernetes Agent Sandbox (kubernetes-sigs/agent-sandbox)",
    "gVisor for AI agent isolation",
    "Kata Containers for AI agents",
    "Firecracker microVMs for agent sandboxes",
    "kagent: AI agents on Kubernetes",
    "Securing MCP tool calls in agent sandboxes",
]


def topic_slug(topic: str) -> str:
    return _slugify(topic.split("(")[0].strip())


def seed_prompt(topic: str) -> str:
    slug = topic_slug(topic)
    return f"""You are the research agent for CNCF Wiki Desk, an autonomous company that sells cited
wikis on cloud-native topics. Grow the wiki around the hub page wiki/{HUB}.
Working directory: {PROJECT_ROOT}

TOPIC: {topic}

1. READ FIRST: wiki/index.md and wiki/{HUB}. Reuse what's there; don't repeat it, link to it.
   If wiki/concepts/{slug}.md already exists, update it instead of rewriting.

2. DISCOVER: find 5-8 sources: KubeCon / CNCF talks on YouTube first, then official project docs
   and CNCF blog posts. Prefer 2024-2026 material. Use the Exa MCP if available, otherwise:
     python -c "from agent.tools.find_sources import find_sources; import json; print(json.dumps(find_sources('{topic}', 10), indent=1))"

3. INGEST: for each YouTube talk run
     python -c "from agent.tools.get_transcript import get_transcript; print(get_transcript('URL'))"
   Then find exact moments with
     python -c "from agent.db import search_chunks; [print(dict(r)) for r in search_chunks('KEYWORDS', 10)]"

4. WRITE wiki/concepts/{slug}.md:
   - YAML frontmatter: title, summary (one line), sources (video id, t, speaker, year),
     links (slugs of related pages), updated, clarity_score: 0.0
   - Sections: what it is (plain language first), how it works, when to use it vs alternatives,
     real-world usage, Disagreements (if sources conflict).
   - Every claim from a talk ends with [▶ MM:SS](https://www.youtube.com/watch?v=VID&t=SECONDSs),
     where MM:SS is exactly SECONDS and the quote really appears in the transcript chunk at that time.
     Claims from docs end with [docs](URL). Never invent a timestamp or a number.
   - Link related wiki pages with relative links like [Agent Sandbox on CNCF](agent-sandbox-on-cncf.md).
{style_guide_text()}
5. CONNECT: add or update the line for this page in wiki/index.md:
     "- [Title](concepts/{slug}.md) — summary"
   and add a bullet linking it under a "## Related pages" section at the end of wiki/{HUB}
   (create the section if missing; keep one bullet per page).

6. CHECK + PUBLISH:
     python -m agent.tools.verify_citations
     mkdocs build --strict
   Fix anything they report, then:
     git add wiki
     git commit -m "wiki: {topic}"
     git push

Output ONLY a JSON object at the end:
{{"status": "published" | "failed", "slug": "{slug}", "sources_used": N, "talks_cited": N, "reason": "..."}}"""


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("topics", nargs="*", help="topics to research (default: Agent Sandbox cluster)")
    parser.add_argument("--list", action="store_true", help="print the default topics and exit")
    args = parser.parse_args()

    topics = args.topics or AGENT_SANDBOX_TOPICS
    if args.list:
        print("\n".join(topics))
        return

    for i, topic in enumerate(topics, 1):
        print(f"[{i}/{len(topics)}] Researching: {topic}", flush=True)
        result = run_claude(seed_prompt(topic), timeout=900)
        status = result.get("status")
        slug = result.get("slug") or topic_slug(topic)
        print(f"    -> {status}: {get_page_url(slug) if status == 'published' else result.get('reason') or result.get('stderr') or result.get('stdout', '')[-300:]}", flush=True)
        log_decision(
            f"Seeded wiki page: {topic}",
            "Grow the Agent Sandbox cluster so related orders reuse memory",
            "Cited page published and linked from the hub",
            f"{status}: sources={result.get('sources_used')} talks={result.get('talks_cited')}",
        )


if __name__ == "__main__":
    main()
