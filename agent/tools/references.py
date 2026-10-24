"""Write a "## References" section at the end of every wiki page, listing every source it cites.

Talks are listed once each, with the moments the page cites; docs, case studies and other
links are listed once each. The section is regenerated from the page's own citations, so
running it again after an edit keeps it in sync.

  python -m agent.tools.references            # update every page
  python -m agent.tools.references --check    # exit 1 if any page is out of date
"""

import argparse
import re
import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).parent.parent.parent
WIKI_DIR = PROJECT_ROOT / "wiki"
DB_PATH = PROJECT_ROOT / "memory.db"

HEADING = "## References"
# Generated (References) or hand-written (Sources) source lists at the end of a page
OLD_SECTION = re.compile(r"\n## (?:References|Sources)\s*\n.*?(?=\n## |\Z)", re.S)
CITATION = re.compile(r"\[▶ ([\d:]+)\]\((https?://[^)\s]*?[?&]v=([\w-]+)[^)\s]*)\)")
LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
FRONT_SOURCE = re.compile(r"video:\s*\"?([\w-]+)\"?.*?speaker:\s*\"([^\"]*)\".*?year:\s*\"?(\d{4})")


def _video_titles() -> dict[str, str]:
    if not DB_PATH.exists():
        return {}
    try:
        with sqlite3.connect(DB_PATH) as conn:
            return {vid: title for vid, title in conn.execute("SELECT video_id, title FROM videos") if title}
    except sqlite3.Error:
        return {}


def _seconds(label: str) -> int:
    total = 0
    for part in label.split(":"):
        total = total * 60 + int(part)
    return total


def build_references(text: str, titles: dict[str, str]) -> str:
    """The References section for a page body (frontmatter included), or "" if it cites nothing."""
    front = text.split("\n---", 1)[0] if text.startswith("---") else ""
    speakers = {vid: (spk, yr) for vid, spk, yr in FRONT_SOURCE.findall(front)}
    body = OLD_SECTION.sub("", text[len(front):])

    talks: dict[str, list[str]] = {}
    for label, _, vid in CITATION.findall(body):
        if label not in talks.setdefault(vid, []):
            talks[vid].append(label)
    others: dict[str, str] = {}
    for label, url in LINK.findall(body):
        if label.startswith("▶") or "youtube.com/watch" in url or "youtu.be/" in url:
            continue
        others.setdefault(url.rstrip("/"), label)

    if not talks and not others:
        return ""
    lines = [HEADING, ""]
    if talks:
        lines += ["**Talks**", ""]
        for n, (vid, labels) in enumerate(talks.items(), 1):
            speaker, year = speakers.get(vid, ("", ""))
            name = titles.get(vid) or (f"{speaker}, {year}" if speaker else f"YouTube video {vid}")
            moments = ", ".join(f"[{lab}](https://www.youtube.com/watch?v={vid}&t={_seconds(lab)}s)"
                                for lab in sorted(labels, key=_seconds))
            lines.append(f"{n}. [{name}](https://www.youtube.com/watch?v={vid}), cited at {moments}")
        lines.append("")
    if others:
        lines += ["**Documentation, case studies and articles**", ""]
        for n, url in enumerate(others, 1):
            host = urlparse(url).netloc.removeprefix("www.")
            path = urlparse(url).path.strip("/")
            lines.append(f"{n}. [{host}/{path}]({url})" if path else f"{n}. [{host}]({url})")
        lines.append("")
    return "\n".join(lines)


def update_page(path: Path, titles: dict[str, str], write: bool = True) -> bool:
    """Regenerate the page's References section. Returns True if the page changed."""
    text = path.read_text(encoding="utf-8")
    refs = build_references(text, titles)
    if not refs:
        return False
    new_text = OLD_SECTION.sub("", text).rstrip() + "\n\n" + refs
    if new_text == text:
        return False
    if write:
        path.write_text(new_text, encoding="utf-8")
    return True


def pages() -> list[Path]:
    return [p for p in sorted(WIKI_DIR.rglob("*.md"))
            if p.relative_to(WIKI_DIR).as_posix() not in ("index.md", "log.md") and "Research" not in p.parts]


def update_all(write: bool = True) -> list[str]:
    titles = _video_titles()
    return [p.relative_to(WIKI_DIR).as_posix() for p in pages() if update_page(p, titles, write)]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="report out-of-date pages without writing")
    args = parser.parse_args()
    changed = update_all(write=not args.check)
    verb = "Out of date" if args.check else "Updated"
    print("\n".join(f"{verb}: {p}" for p in changed) if changed else "All References sections are current.")
    sys.exit(1 if args.check and changed else 0)


if __name__ == "__main__":
    main()
