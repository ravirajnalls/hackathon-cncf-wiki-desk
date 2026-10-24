"""CNCF Wiki Desk MCP server: use the wiki from inside Claude, and order new topics.

Tools:
  list_topics()        every wiki page with its one-line summary
  search_wiki(query)   full-text search over the live wiki
  get_page(slug)       a page's markdown, with its timestamp citations
  order_wiki(topic)    Whop checkout link to have the agent research a new topic

Add to Claude Code:
  claude mcp add wiki-desk -- uvx --with "mcp>=1.2,<2" --with requests python mcp_server/wiki_desk_mcp.py
or, with the project requirements installed:
  claude mcp add wiki-desk -- python mcp_server/wiki_desk_mcp.py
"""

import os
import re

import requests
from mcp.server.fastmcp import FastMCP

SITE = os.environ.get("WIKI_BASE_URL", "https://ravirajnalls.github.io/hackathon-cncf-wiki-desk").rstrip("/")
RAW = os.environ.get("WIKI_RAW_URL",
                     "https://raw.githubusercontent.com/ravirajnalls/hackathon-cncf-wiki-desk/main/wiki")
CHECKOUT_URL = os.environ.get("WHOP_CHECKOUT_URL", "https://whop.com/github-9154/cloud-native-wiki-on-demand")
PRICE = os.environ.get("WHOP_PRICE_USD", "3")

mcp = FastMCP("cncf-wiki-desk")


def _get(url: str) -> requests.Response:
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp


def _topics() -> list[dict]:
    """Parse wiki/index.md lines like '- [Title](concepts/slug.md) — summary'."""
    topics = []
    for line in _get(f"{RAW}/index.md").text.splitlines():
        m = re.match(r"- \[(.+?)\]\((?:wiki/)?([\w/-]+)\.md\)\s*—\s*(.*)", line.strip())
        if m:
            title, path, summary = m.groups()
            topics.append({"title": title, "slug": path.split("/")[-1], "path": path,
                           "summary": summary, "url": f"{SITE}/{path}/"})
    return topics


@mcp.tool()
def list_topics() -> list[dict]:
    """List every cloud-native topic in the CNCF Wiki Desk wiki, with a one-line summary and URL."""
    return _topics()


@mcp.tool()
def search_wiki(query: str, limit: int = 8) -> list[dict]:
    """Full-text search the CNCF Wiki Desk wiki (KubeCon/CNCF talks, cited with video timestamps).

    Returns matching sections with their URLs. If nothing matches, suggest order_wiki.
    """
    docs = _get(f"{SITE}/search/search_index.json").json().get("docs", [])
    terms = [t for t in re.findall(r"\w+", query.lower()) if len(t) > 2]
    scored = []
    for doc in docs:
        text = f"{doc.get('title', '')} {doc.get('text', '')}".lower()
        score = sum(text.count(t) for t in terms)
        if score:
            snippet = re.sub(r"<[^>]+>", "", doc.get("text", ""))[:300]
            scored.append((score, {"title": doc.get("title"), "url": f"{SITE}/{doc.get('location', '')}",
                                   "snippet": snippet}))
    scored.sort(key=lambda s: s[0], reverse=True)
    return [item for _, item in scored[:limit]]


@mcp.tool()
def get_page(slug: str) -> str:
    """Return a wiki page's full markdown. Every claim ends with a [▶ MM:SS](youtube...) citation.

    slug comes from list_topics or search_wiki, e.g. 'agent-sandbox-on-cncf'.
    """
    for topic in _topics():
        if topic["slug"] == slug:
            return _get(f"{RAW}/{topic['path']}.md").text
    return f"No page '{slug}'. Use list_topics to see what exists, or order_wiki to commission it."


@mcp.tool()
def order_wiki(topic: str) -> dict:
    """Commission a new cited wiki on a cloud-native topic. Returns the Whop checkout link.

    After paying, the buyer names the topic; the agent researches KubeCon/CNCF talks and
    delivers the page link through Whop within minutes. Give the user the checkout link.
    """
    try:
        existing = [t for t in _topics() if topic.lower() in t["title"].lower()]
    except requests.RequestException:
        existing = []  # the checkout link matters more than the lookup
    return {
        "topic": topic,
        "price_usd": PRICE,
        "checkout_url": CHECKOUT_URL,
        "instructions": f"Pay on Whop, then send the topic '{topic}' when asked. Delivery is a link on {SITE}.",
        "already_in_wiki": existing,
    }


if __name__ == "__main__":
    mcp.run()
