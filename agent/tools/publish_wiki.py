"""Build the static wiki site and return the delivery URL.

mkdocs.yml lives at the project root (docs_dir: wiki, site_dir: site). The
hosted copy (Netlify, see netlify.toml) rebuilds from GitHub on every push;
the local build here just checks the new page renders.
"""

import os
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
WIKI_DIR = PROJECT_ROOT / "wiki"
SITE_DIR = PROJECT_ROOT / "site"

# Set WIKI_BASE_URL in .env to the deployed site, e.g. https://cncf-wiki-desk.netlify.app
DEFAULT_BASE_URL = "https://cncf-wiki-desk.netlify.app"


def publish_wiki() -> dict:
    """Build the MkDocs site locally.

    Returns: {status, url, pages_built, warning?}
    """
    pages = [p for p in WIKI_DIR.rglob("*.md") if p.name not in ("index.md", "log.md")]
    if not pages:
        return {"status": "no_pages", "url": "", "pages_built": 0}

    try:
        result = subprocess.run(
            ["mkdocs", "build", "--quiet"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        return {"status": "mkdocs_missing", "url": get_base_url(), "pages_built": len(pages),
                "warning": "mkdocs not installed: pip install -r .requirements"}

    if result.returncode != 0:
        return {"status": "build_failed", "url": get_base_url(), "pages_built": 0,
                "warning": result.stderr[-1000:]}
    return {"status": "built", "url": get_base_url(), "pages_built": len(pages)}


def get_base_url() -> str:
    return os.environ.get("WIKI_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def get_page_url(slug: str) -> str:
    """Public URL of a concept page on the deployed site."""
    return f"{get_base_url()}/concepts/{slug}/"
