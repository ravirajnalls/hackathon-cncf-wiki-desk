"""Run a headless Claude Code subprocess (`claude -p`) and parse its JSON result.

Shared by the order orchestrator and the Terac study flow. MCP tools (Whop,
Terac, Exa) live in the user's Claude Code config, so anything that needs
them goes through here.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Tools the headless Claude subprocess may use without a permission prompt.
# MCP entries must match your server names (check with `claude mcp list`).
DEFAULT_ALLOWED_TOOLS = "Bash Read Write Edit Glob Grep WebFetch mcp__whop mcp__terac mcp__exa"
ALLOWED_TOOLS = os.environ.get("CLAUDE_ALLOWED_TOOLS", DEFAULT_ALLOWED_TOOLS).split()


def parse_last_json(text: str) -> dict | None:
    """Return the last top-level JSON object in text, even if it spans several lines."""
    decoder = json.JSONDecoder()
    last = None
    pos = text.find("{")
    while pos != -1:
        try:
            obj, end = decoder.raw_decode(text, pos)
        except json.JSONDecodeError:
            pos = text.find("{", pos + 1)
            continue
        if isinstance(obj, dict):
            last = obj
        pos = text.find("{", end)
    return last


def run_claude(prompt: str, timeout: int = 600) -> dict:
    """Run `claude -p` with the prompt on stdin; return its final JSON object."""
    # Resolve claude.cmd on Windows, which subprocess can't find by bare name
    claude_bin = shutil.which("claude")
    if not claude_bin:
        return {"status": "claude_not_found", "reason": "claude CLI not found in PATH. Install Claude Code CLI."}

    try:
        result = subprocess.run(
            # Prompt goes via stdin to avoid command-line length/quoting limits
            [claude_bin, "-p", "--allowedTools", *ALLOWED_TOOLS],
            input=prompt,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
            env={**os.environ, "CLAUDE_PROJECT_DIR": str(PROJECT_ROOT)},
        )
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "reason": f"Claude subprocess exceeded {timeout // 60} minutes"}
    except FileNotFoundError:
        return {"status": "claude_not_found", "reason": "claude CLI not found in PATH. Install Claude Code CLI."}

    output = result.stdout.strip()
    parsed = parse_last_json(output)
    if parsed is not None:
        return parsed

    return {
        "status": "unknown",
        "stdout": output[-2000:],
        "stderr": result.stderr[-1000:] if result.stderr else "",
        "returncode": result.returncode,
    }
