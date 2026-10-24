"""Exa discovery, scoped to CNCF: talks from the CNCF YouTube channel (KubeCon +
CloudNativeCon) and docs from cncf.io, kubernetes.io and the matched projects' own sites.

  python -m agent.tools.find_sources "Cilium network policy"
  python -m agent.tools.find_sources --use-cases "Cilium"     # who runs it in production
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env even when this module is run on its own (python -m agent.tools.…)
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from agent.tools.cncf_projects import CNCF_CHANNEL_HINTS, match_projects, source_domains

try:
    from exa_py import Exa
except ImportError:
    Exa = None

EXA_API_KEY = os.environ.get("EXA_API_KEY", "")
_exa_client = None


def _client():
    global _exa_client
    if _exa_client is None:
        if Exa is None:
            raise RuntimeError("exa-py not installed: pip install exa-py")
        _exa_client = Exa(api_key=EXA_API_KEY)
    return _exa_client


def _is_cncf_talk(r) -> bool:
    """A talk from the CNCF channel, or a KubeCon/CloudNativeCon recording."""
    blob = f"{r.author or ''} {r.title or ''}".lower()
    return any(h in blob for h in CNCF_CHANNEL_HINTS) or "kubecon" in blob or "cloudnativecon" in blob


def _source(r, kind: str) -> dict:
    return {
        "url": r.url or "",
        "title": r.title or "",
        "author": r.author or "",
        "published": r.published_date or "",
        "text": (r.text or "")[:500],
        "type": kind,
    }


def find_sources(topic: str, max_results: int = 8) -> list[dict]:
    """Find CNCF talks and docs on a topic. Raises ValueError if it isn't a CNCF project.

    Returns list of: {url, title, author, published, text, type: "talk" | "docs", project}
    """
    projects = match_projects(topic)
    if not projects:
        raise ValueError(f"'{topic}' does not match a CNCF project (see python -m agent.tools.cncf_projects --options)")
    names = ", ".join(p["name"] for p in projects)
    client = _client()

    talks = client.search_and_contents(
        query=f"KubeCon CloudNativeCon talk on {topic} ({names}) from the CNCF YouTube channel",
        num_results=max_results * 2,
        include_domains=["youtube.com"],
        text={"max_characters": 500},
    )
    docs = client.search_and_contents(
        query=f"{topic} {names} official documentation and CNCF blog",
        num_results=max_results,
        include_domains=source_domains(projects),
        text={"max_characters": 500},
    )

    found_talks = [_source(r, "talk") for r in talks.results if _is_cncf_talk(r)]
    found_docs = [_source(r, "docs") for r in docs.results]
    # Talks first (they carry the timestamp citations); keep room for a few docs
    keep_talks = max(max_results - len(found_docs), max_results * 2 // 3)
    found = (found_talks[:keep_talks] + found_docs)[:max_results]
    for s in found:
        s["project"] = names
    return found

def find_use_cases(topic: str, max_results: int = 10) -> list[dict]:
    """Find named organizations using the project, from three kinds of CNCF source:
    end-user KubeCon talks, CNCF case studies / end-user blog posts, and the project's
    own adopters list. Returns the same shape as find_sources, type "talk" | "case_study" | "adopters".
    """
    projects = match_projects(topic)
    if not projects:
        raise ValueError(f"'{topic}' does not match a CNCF project")
    names = ", ".join(p["name"] for p in projects)
    client = _client()

    talks = client.search_and_contents(
        query=f"KubeCon end user talk: how our company runs {names} in production, lessons learned",
        num_results=max_results,
        include_domains=["youtube.com"],
        text={"max_characters": 500},
    )
    cases = client.search_and_contents(
        query=f"{names} case study: company adopts {names} in production, results",
        num_results=max_results,
        include_domains=["cncf.io"] + [d for d in source_domains(projects) if d not in ("github.com", "kubernetes.io")],
        text={"max_characters": 500},
    )
    found = [_source(r, "talk") for r in talks.results if _is_cncf_talk(r)]
    found += [_source(r, "case_study") for r in cases.results]
    # Most CNCF projects keep a list of production users in their repo
    for p in projects:
        if p.get("repo", "").startswith("https://github.com/"):
            for name in ("ADOPTERS.md", "USERS.md"):
                found.append({"url": f"{p['repo'].rstrip('/')}/blob/main/{name}", "title": f"{p['name']} {name}",
                              "author": p["name"], "published": "", "text": "", "type": "adopters"})
    for s in found:
        s["project"] = names
    return found


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--use-cases":
        print(json.dumps(find_use_cases(" ".join(args[1:])), indent=1))
    else:
        print(json.dumps(find_sources(" ".join(args), 10), indent=1))
