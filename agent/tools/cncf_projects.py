"""CNCF project catalog from the official landscape (cncf/landscape landscape.yml).

Scopes orders to CNCF open source projects and gives the agent each project's
homepage, repo and maturity so research stays on CNCF sources.

  python -m agent.tools.cncf_projects "Cilium"     # match a buyer's topic
  python -m agent.tools.cncf_projects --refresh    # re-download the landscape
  python -m agent.tools.cncf_projects --options    # topics to suggest at checkout
"""

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests
import yaml

LANDSCAPE_URL = "https://raw.githubusercontent.com/cncf/landscape/master/landscape.yml"
CACHE = Path(__file__).parent.parent / "cncf_projects.json"
MATURITY = ("graduated", "incubating", "sandbox")

# Shown as examples in the checkout question
CHECKOUT_OPTIONS = ["Kubernetes", "Cilium", "Argo", "OpenTelemetry", "Prometheus", "Envoy",
                    "Istio", "Kyverno", "kagent", "Agent Substrate"]

# CNCF's official YouTube channel name, as search results report it
CNCF_CHANNEL_HINTS = ("cncf", "cloud native computing foundation")


def refresh() -> list[dict]:
    resp = requests.get(LANDSCAPE_URL, timeout=30)
    resp.raise_for_status()
    items = []

    def walk(node):
        if isinstance(node, dict):
            if "item" in node and "name" in node:
                items.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(yaml.safe_load(resp.text))
    projects = sorted(
        ({"name": i["name"], "maturity": i["project"], "homepage": i.get("homepage_url", ""),
          "repo": i.get("repo_url", ""), "description": i.get("description", "")}
         for i in items if i.get("project") in MATURITY),
        key=lambda p: (MATURITY.index(p["maturity"]), p["name"].lower()),
    )
    # The same project can appear in several landscape categories
    unique = list({p["name"]: p for p in projects}.values())
    CACHE.write_text(json.dumps(unique, indent=1, ensure_ascii=False), encoding="utf-8")
    return unique


def load_projects() -> list[dict]:
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    return refresh()


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


# Repo names too generic to identify a project on their own (e.g. opcr-io/policy)
GENERIC_REPO_NAMES = {"policy", "operator", "server", "core", "api", "docs", "project", "controller",
                      "agent", "sdk", "cli", "community", "website", "spec", "network", "security",
                      "pack", "serving", "hub", "pipeline", "build", "kube", "slim", "spin"}


# Subprojects that live under a CNCF project but aren't listed in the landscape on their own
SUBPROJECTS = {
    "Kubernetes": {"agent sandbox", "gateway api", "cluster api", "kueue", "kustomize", "kind",
                   "jobset", "leaderworkerset", "karpenter", "kwok", "kubectl", "kubelet"},
    "Argo": {"argo cd", "argocd", "argo workflows", "argo rollouts", "argo events"},
}


def match_projects(topic: str) -> list[dict]:
    """CNCF projects named in the topic, best match first."""
    t = f" {_norm(topic)} "
    hits = []
    for p in load_projects():
        names = {_norm(p["name"]), _norm(re.sub(r"\(.*?\)", "", p["name"]))}
        names |= set(re.findall(r"\((.*?)\)", p["name"].lower()))  # e.g. "Open Policy Agent (OPA)"
        if p["repo"]:
            repo_name = _norm(p["repo"].rstrip("/").split("/")[-1])
            if repo_name not in GENERIC_REPO_NAMES:
                names.add(repo_name)
        names |= SUBPROJECTS.get(p["name"], set())
        names = {n for n in names if len(n) >= 3}
        if any(f" {n} " in t for n in names):
            hits.append(p)
    return sorted(hits, key=lambda p: -len(p["name"]))


def source_domains(projects: list[dict]) -> list[str]:
    """CNCF-owned domains plus each matched project's own site."""
    domains = ["cncf.io", "kubernetes.io", "landscape.cncf.io", "github.com"]
    for p in projects:
        host = urlparse(p.get("homepage") or "").netloc.removeprefix("www.")
        if host and host not in domains:
            domains.append(host)
    return domains


def main():
    args = sys.argv[1:]
    if args == ["--refresh"]:
        print(f"{len(refresh())} CNCF projects cached in {CACHE}")
    elif args == ["--options"]:
        print(", ".join(CHECKOUT_OPTIONS))
    elif args:
        hits = match_projects(" ".join(args))
        print(json.dumps(hits[:5], indent=1) if hits else "NO MATCH")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
