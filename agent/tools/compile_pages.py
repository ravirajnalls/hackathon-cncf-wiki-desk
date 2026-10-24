"""Compile wiki pages — decide create / update / flag_conflict against the wiki index."""

import os
from datetime import datetime
from pathlib import Path

WIKI_DIR = Path(__file__).parent.parent.parent / "wiki"
INDEX_FILE = WIKI_DIR / "index.md"


def _ensure_dirs():
    for sub in ["projects", "concepts", "patterns", "talks", "debates", "timelines"]:
        (WIKI_DIR / sub).mkdir(parents=True, exist_ok=True)
    if not INDEX_FILE.exists():
        INDEX_FILE.write_text("# CNCF Wiki Desk — Index\n\n", encoding="utf-8")


def _read_index() -> dict[str, str]:
    """Read index.md into a dict of {slug: summary_line}."""
    _ensure_dirs()
    index = {}
    for line in INDEX_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("- "):
            # Format: "- [slug](path) — summary"
            parts = line[2:].split(" — ", 1)
            if len(parts) == 2:
                slug = parts[0].strip().lstrip("[").split("]")[0]
                index[slug] = parts[1].strip()
    return index


def _slugify(topic: str) -> str:
    return topic.lower().replace(" ", "-").replace("/", "-").replace(":", "")


def compile_pages(topic: str, sources: list[dict], transcript_results: list[dict]) -> dict:
    """Decide what wiki pages to create or update.

    Returns:
    {
        "slug": "...",
        "action": "create" | "update" | "flag_conflict",
        "content": "full markdown content",
        "reason": "why this action"
    }
    """
    _ensure_dirs()
    index = _read_index()
    slug = _slugify(topic)
    page_path = WIKI_DIR / "concepts" / f"{slug}.md"

    # Build frontmatter sources from transcript results
    frontmatter_sources = []
    body_sections = []

    for tr in transcript_results:
        vid = tr.get("video_id", "")
        if not vid or tr.get("error"):
            continue
        # Add a citation source entry
        frontmatter_sources.append({
            "video": vid,
            "t": 0,
            "speaker": "",
            "year": "",
        })

    # Build the page body from ingested transcript chunks
    from agent.db import search_chunks
    relevant_chunks = search_chunks(topic, limit=15)

    body_sections.append(f"# {topic}\n")
    body_sections.append(f"> Auto-compiled on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n")

    if relevant_chunks:
        body_sections.append("## Key Points\n")
        seen_texts = set()
        for chunk in relevant_chunks:
            text = chunk["text"]
            if text in seen_texts:
                continue
            seen_texts.add(text)
            link = f"[▶](https://youtube.com/watch?v={chunk['video_id']}&t={chunk['t_start']}s)"
            body_sections.append(f"- {text} {link}\n")

    # Flag conflicts if sources disagree (simplified — flag if multiple distinct speakers)
    speakers = set(s.get("author", "") for s in sources if s.get("author"))
    action = "create"
    reason = f"New topic: {topic}"

    if page_path.exists():
        existing = page_path.read_text(encoding="utf-8")
        if topic.lower() in existing.lower():
            action = "update"
            reason = f"Topic '{topic}' already has a page — adding new sources"
        if len(speakers) > 1:
            action = "flag_conflict"
            reason = f"Multiple speakers ({', '.join(speakers)}) — potential disagreements flagged"

    # Add disagreements section if conflict
    if action == "flag_conflict" and len(speakers) > 1:
        body_sections.append("\n## Disagreements\n")
        body_sections.append(f"> ⚠ Sources from {', '.join(speakers)} present differing viewpoints. Verify before relying on any single claim.\n")

    # Build frontmatter
    frontmatter_lines = [
        "---",
        f"title: {topic}",
        f"summary: Auto-compiled wiki on {topic} from CNCF talks and docs.",
        "sources:",
    ]
    for src in frontmatter_sources[:10]:
        frontmatter_lines.append(f"  - {{video: {src['video']}, t: {src['t']}, speaker: '{src['speaker']}', year: '{src['year']}'}}")
    frontmatter_lines.append(f"updated: {datetime.utcnow().strftime('%Y-%m-%d')}")
    frontmatter_lines.append(f"clarity_score: 0.0")
    frontmatter_lines.append("---\n")

    full_content = "\n".join(frontmatter_lines) + "\n".join(body_sections)

    return {
        "slug": slug,
        "action": action,
        "path": str(page_path.relative_to(WIKI_DIR.parent)),
        "content": full_content,
        "reason": reason,
    }


def write_page(slug: str, content: str):
    """Write a compiled page to disk and update the index."""
    _ensure_dirs()
    page_path = WIKI_DIR / "concepts" / f"{slug}.md"
    page_path.write_text(content, encoding="utf-8")

    # Update index
    index_content = INDEX_FILE.read_text(encoding="utf-8")
    summary_line = content.split("summary: ", 1)[1].split("\n")[0] if "summary: " in content else f"Wiki on {slug}"
    new_entry = f"- [{slug}](concepts/{slug}.md) — {summary_line}"

    # Replace existing entry or append
    if slug in index_content:
        lines = index_content.splitlines()
        lines = [l if slug not in l else new_entry for l in lines]
        index_content = "\n".join(lines) + "\n"
    else:
        index_content += new_entry + "\n"

    INDEX_FILE.write_text(index_content, encoding="utf-8")
