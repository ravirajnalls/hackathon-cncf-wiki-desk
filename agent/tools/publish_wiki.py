"""Build the static wiki site and return the delivery URL."""

import shutil
import subprocess
from pathlib import Path

WIKI_DIR = Path(__file__).parent.parent.parent / "wiki"
SITE_DIR = WIKI_DIR / "site"
DOCS_MKDOCS = WIKI_DIR / "mkdocs.yml"


def _ensure_mkdocs_config():
    """Create a minimal mkdocs.yml if it doesn't exist."""
    if DOCS_MKDOCS.exists():
        return
    config = f"""site_name: CNCF Wiki Desk
theme:
  name: material
  features:
    - navigation.instant
    - search.suggest
    - search.highlight
plugins:
  - search
docs_dir: {WIKI_DIR.name}
site_dir: site
"""
    DOCS_MKDOCS.write_text(config, encoding="utf-8")


def publish_wiki() -> dict:
    """Build the static MkDocs site.

    Returns: {url, status, pages_built}
    """
    _ensure_mkdocs_config()

    # Count pages
    pages = list((WIKI_DIR / "concepts").glob("*.md"))
    pages += list((WIKI_DIR / "projects").glob("*.md"))
    pages += list((WIKI_DIR / "talks").glob("*.md"))

    if not pages:
        return {"status": "no_pages", "url": "", "pages_built": 0}

    try:
        result = subprocess.run(
            ["mkdocs", "build"],
            cwd=str(WIKI_DIR),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            # Fallback: just copy markdown files as static HTML
            SITE_DIR.mkdir(exist_ok=True)
            for p in pages:
                shutil.copy2(p, SITE_DIR / p.name)
            return {
                "status": "fallback_copied",
                "url": str(SITE_DIR),
                "pages_built": len(pages),
                "warning": result.stderr[:500],
            }

        return {
            "status": "built",
            "url": str(SITE_DIR),
            "pages_built": len(pages),
        }
    except FileNotFoundError:
        # mkdocs not installed — fallback to copying
        SITE_DIR.mkdir(exist_ok=True)
        for p in pages:
            shutil.copy2(p, SITE_DIR / p.name)
        return {
            "status": "fallback_copied",
            "url": str(SITE_DIR),
            "pages_built": len(pages),
            "warning": "mkdocs not installed, using file copy fallback",
        }


def get_page_url(slug: str) -> str:
    """Return the URL path for a specific wiki page.

    In production this would be the deployed URL (Netlify/Vercel/Whop hosting).
    For hackathon, returns the local path or deployed base URL.
    """
    deployed_base = "https://cncf-wiki-desk.netlify.app"  # placeholder — update after deploy
    return f"{deployed_base}/concepts/{slug}/"
