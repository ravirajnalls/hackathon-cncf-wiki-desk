"""Check every [▶ MM:SS](...&t=Ns) citation in the wiki.

Two checks:
  1. The label (MM:SS) matches the link's t= seconds.
  2. With transcripts ingested in memory.db, a quoted sentence next to the
     citation actually appears in the transcript near that time. If it appears
     elsewhere, the correct timestamp is suggested.

  python -m agent.tools.verify_citations          # report
  python -m agent.tools.verify_citations --fix    # rewrite labels/links to the suggested time
"""

import argparse
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
WIKI_DIR = PROJECT_ROOT / "wiki"

CITATION = re.compile(r"\[▶ (\d+):(\d{2})\]\((https?://[^)]*?[?&]v=([\w-]+)[^)]*?[?&]t=(\d+)s)\)")
QUOTE = re.compile(r"\"([^\"]{20,})\"")
NEAR_SECONDS = 90


def label(seconds: int) -> str:
    return f"{seconds // 60}:{seconds % 60:02d}"


def find_quote_time(video_id: str, quote: str) -> int | None:
    """Return the chunk start time whose text contains the quote's opening words."""
    from agent.db import get_db

    words = re.sub(r"[^\w\s]", "", quote.lower()).split()[:6]
    if len(words) < 3:
        return None
    needle = " ".join(words)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT t_start, text FROM chunks WHERE video_id = ? ORDER BY CAST(t_start AS INTEGER)",
            (video_id,),
        ).fetchall()
    for row in rows:
        if needle in re.sub(r"[^\w\s]", "", row["text"].lower()):
            return int(row["t_start"])
    return None


def check_page(path: Path, fix: bool) -> list[str]:
    text = path.read_text(encoding="utf-8")
    problems = []
    replacements = []
    for line in text.splitlines():
        quotes = QUOTE.findall(line)
        for m in CITATION.finditer(line):
            mins, secs, url, vid, t = m.groups()
            t = int(t)
            shown = int(mins) * 60 + int(secs)
            suggested = None
            if shown != t:
                problems.append(f"{path.name}: label {mins}:{secs} but link jumps to {label(t)} ({vid})")
            for q in quotes:
                found = find_quote_time(vid, q)
                if found is not None and abs(found - t) > NEAR_SECONDS:
                    problems.append(f"{path.name}: quote \"{q[:50]}…\" is at {label(found)}, cited at {label(t)}")
                    suggested = found
            if suggested is not None:
                new_url = re.sub(r"([?&]t=)\d+s", rf"\g<1>{suggested}s", url)
                replacements.append((m.group(0), f"[▶ {label(suggested)}]({new_url})"))
    if fix and replacements:
        for old, new in replacements:
            text = text.replace(old, new, 1)
        path.write_text(text, encoding="utf-8")
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fix", action="store_true", help="move citations to where the quote was found")
    args = parser.parse_args()
    problems = []
    for page in sorted(WIKI_DIR.rglob("*.md")):
        problems += check_page(page, args.fix)
    print("\n".join(problems) if problems else "All citations check out.")
    sys.exit(1 if problems and not args.fix else 0)


if __name__ == "__main__":
    sys.path.insert(0, str(PROJECT_ROOT))
    main()
