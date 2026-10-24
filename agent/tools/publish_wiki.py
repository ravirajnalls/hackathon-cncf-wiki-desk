"""Build the static wiki site and return the delivery URL.

mkdocs.yml lives at the project root (docs_dir: wiki, site_dir: site). The
hosted copy (GitHub Pages, see .github/workflows/pages.yml) rebuilds from GitHub on every push;
the local build here just checks the new page renders.
"""

import os
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
WIKI_DIR = PROJECT_ROOT / "wiki"
SITE_DIR = PROJECT_ROOT / "site"

# Override with WIKI_BASE_URL in .env if the site moves
DEFAULT_BASE_URL = "https://ravirajnalls.github.io/hackathon-cncf-wiki-desk"


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


GITHUB_REPO_URL = os.environ.get("GITHUB_REPO_URL", "https://github.com/ravirajnalls/hackathon-cncf-wiki-desk")


def topic_page_path(topic: str) -> str:
    """Where a topic's page lives in wiki/, without .md. Pages are grouped by CNCF project:

      projects/<project>/index      the project's overview ("Cilium")
      projects/<project>/<subtopic> e.g. "Kubernetes Agent Sandbox" -> projects/kubernetes/agent-sandbox
      guides/<topic>                topics that don't name a CNCF project
    """
    from agent.tools.cncf_projects import match_projects
    from agent.tools.compile_pages import _slugify

    slug = _slugify(topic.split("(")[0].strip())
    projects = match_projects(topic)
    if not projects:
        return f"guides/{slug}"
    project = _slugify(projects[0]["name"].split("(")[0].strip())
    if slug == project:
        return f"projects/{project}/index"
    sub = slug.removeprefix(project + "-") or slug
    return f"projects/{project}/{sub}"


def usage_instructions(topic: str) -> str:
    """The required Real-world usage section, shared by the order and seed prompts."""
    return f"""   - A "## Real-world usage" section is REQUIRED. Find use cases with
       python -m agent.tools.find_sources --use-cases "{topic}"
     (end-user KubeCon talks, CNCF case studies, and the project's ADOPTERS.md / USERS.md, which you
     can read with WebFetch; a 404 just means the project keeps no such file).
     Write 3-6 bullets, one per organization or use case:
       - **Organization**: what they use it for, at what scale, and what changed, with a citation.
     Cite at least 3 different sources, from at least 2 kinds (talk, case study, adopters list).
     Ingest end-user talks like any other talk so their claims get [▶ MM:SS] citations.
     Only name organizations a source names. A vendor describing its own product is not a use case.
     If you can't find 3 sourced use cases, say so in one line instead of padding.
"""


def index_instructions(path: str, project: str = "") -> str:
    """How the agent files a new page into wiki/index.md and its folder's index (shared by prompts)."""
    folder, _, name = path.rpartition("/")
    section = ("the \"## Guides\" section" if folder == "guides" else
               f"the \"### {project or 'project name'}\" heading under \"## CNCF projects\" (create it, in alphabetical order, if missing)")
    folder_index = ("" if name == "index" else
                    f"\n   Also list it in wiki/{folder}/index.md (for a project folder with no overview yet, create a"
                    f"\n   short index.md that introduces the project in two sentences with a [docs] citation, then lists its pages).")
    return (f"Add or update its line in wiki/index.md under {section}:"
            f"\n     \"- [Title]({path}.md) — one-line summary\"{folder_index}"
            f"\n   Links between pages are relative to the page's own folder, e.g. from wiki/{path}.md:"
            f"\n     [Agent Sandbox on CNCF]({'../' * path.count('/')}guides/agent-sandbox-on-cncf.md)")


def get_source_url(path: str) -> str:
    """GitHub URL of a page's markdown (its History tab shows every agent edit). path: wiki-relative, no .md"""
    return f"{GITHUB_REPO_URL}/blob/main/wiki/{path}.md"


def order_key(whop_id: str) -> str:
    """URL-safe folder name for an order, e.g. pay_AbC123 -> pay-abc123."""
    return "".join(c if c.isalnum() else "-" for c in whop_id.lower()).strip("-")


def order_page_path(whop_id: str, slug: str) -> str:
    """Each order gets its own page under wiki/orders/; later orders never change it."""
    return f"orders/{order_key(whop_id)}/{slug}"


def get_order_page_url(whop_id: str, slug: str) -> str:
    return get_page_url(order_page_path(whop_id, slug))


def get_order_source_url(whop_id: str, slug: str) -> str:
    return get_source_url(order_page_path(whop_id, slug))


def get_page_url(path: str) -> str:
    """Public URL of a page on the deployed site. path: wiki-relative, no .md (from topic_page_path)."""
    path = path.removesuffix("index").strip("/")
    return f"{get_base_url()}/{path}/" if path else f"{get_base_url()}/"
