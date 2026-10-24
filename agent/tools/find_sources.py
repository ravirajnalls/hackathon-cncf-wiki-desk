"""Exa discovery — find KubeCon/CNCF talks and docs on a topic."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env even when this module is run on its own (python -m agent.tools.…)
load_dotenv(Path(__file__).parent.parent.parent / ".env")

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


def find_sources(topic: str, max_results: int = 8) -> list[dict]:
    """Search for KubeCon/CNCF talks and official docs on a topic.

    Returns list of: {url, title, author, year, type}
    """
    client = _client()
    query = f"CNCF {topic} KubeCon talk OR keynote OR official documentation"

    response = client.search_and_contents(
        query=query,
        num_results=max_results,
        type="auto",
        text={"max_characters": 500},
    )

    sources = []
    for r in response.results:
        # Prefer YouTube video talks and CNCF blog/docs
        url = r.url or ""
        is_youtube = "youtube.com" in url or "youtu.be" in url
        is_cncf = "cncf.io" in url or "kubernetes.io" in url

        sources.append({
            "url": url,
            "title": r.title or "",
            "author": r.author or "",
            "published": r.published_date or "",
            "text": (r.text or "")[:500],
            "relevance": 2 if is_youtube else (1 if is_cncf else 0),
        })

    # Sort: YouTube talks first, then CNCF docs, then others
    sources.sort(key=lambda s: s["relevance"], reverse=True)
    return sources[:max_results]
