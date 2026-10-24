"""Write marketing copy — landing page, launch post, policy page."""

import json
from pathlib import Path

LANDING_COPY = """# Cloud Native Brain

**Get cited cloud-native research delivered in minutes.**

Pay $3. Name any CNCF or cloud-native topic. Get a wiki with clickable
video timestamps pulled from KubeCon talks and official docs.

→ Every claim cites a source. Every source links to a video timestamp.

[Order Now](#checkout)

## How it works

1. Pay $3 on Whop
2. Tell us your topic (e.g. "Cilium", "Gateway API", "Argo CD")
3. Our agent researches talks and docs
4. You get a wiki with cited, timestamped sources — within minutes
5. Order again on the same topic and it arrives faster (we remember)
"""

LAUNCH_POST = """🚀 Just launched at the Terac Zero Human Company Hackathon!

Cloud Native Brain: pay $3, name any cloud-native topic, get a cited wiki with
clickable video timestamps — delivered by an agent in minutes.

No humans. No waiting. Just sourced knowledge.

👉 https://whop.com/github-9154/cloud-native-wiki-on-demand

#ZeroHuman #CNCF #KubeCon #Hackathon"""

POLICY_PAGE = """# Terms, Refund Policy & Attribution

## Terms of Service

Cloud Native Brain provides AI-compiled wikis on cloud-native topics. Wikis are
generated from publicly available KubeCon talks and official documentation.

By purchasing, you receive a single-use license to view and share the wiki.

## Refund Policy

If your wiki is not delivered within 30 minutes, contact us on Whop for a
full refund. We stand behind every order.

## Source Attribution & Licensing

Every claim in every wiki is cited with a clickable timestamp linking to the
original source (typically a KubeCon talk on the CNCF YouTube channel).

All source content is the property of their respective speakers and the CNCF.
We compile and cite; we do not claim ownership of the underlying talks.

CNCF, KubeCon, and project names are trademarks of the Linux Foundation.
"""


def write_copy(output_dir: str = ".") -> dict:
    """Write all marketing copy to files."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    files = {
        "landing.md": LANDING_COPY,
        "launch_post.md": LAUNCH_POST,
        "policy.md": POLICY_PAGE,
    }

    for name, content in files.items():
        (out / name).write_text(content, encoding="utf-8")

    return {"status": "written", "files": list(files.keys())}


if __name__ == "__main__":
    result = write_copy("./output")
    print(json.dumps(result, indent=2))
