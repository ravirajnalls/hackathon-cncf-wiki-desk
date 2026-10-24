"""Main orchestrator — runs the 7-step fulfillment loop for each order.

Steps:
  1. poll_orders    — find paid orders
  2. find_sources   — discover KubeCon/CNCF talks via Exa
  3. get_transcript — pull captions with timestamps
  4. compile_pages  — decide create/update/conflict, write wiki
  5. publish_wiki   — build static site, get delivery URL
  6. deliver        — send link to buyer via Whop
  7. log_decision   — record outcome for compounding memory

On any step failure, the loop can be resumed from where it left off.
"""

import json
import os
import sys
import time
from datetime import datetime

from anthropic import Anthropic

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.db import pending_orders, record_order, mark_delivered, log_decision
from agent.tools.poll_orders import poll_orders as whop_poll
from agent.tools.find_sources import find_sources
from agent.tools.get_transcript import get_transcript
from agent.tools.compile_pages import compile_pages, write_page
from agent.tools.publish_wiki import publish_wiki, get_page_url
from agent.tools.deliver import deliver
from agent.tools.write_copy import write_copy

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

SYSTEM_PROMPT = """You are the orchestrator for CNCF Wiki Desk — an agent-run company.
You fulfill orders autonomously. For each order, you:
  1. Discover sources (KubeCon talks, CNCF docs) via Exa
  2. Ingest transcripts with timestamps
  3. Compile a wiki page (create, update, or flag conflicts)
  4. Publish and deliver the wiki
  5. Log your decisions

You have access to tools. Use them. Be efficient — the buyer is waiting.
When you log a decision, include: what you decided, why, and what you expected."""


def _tool_specs():
    """Return Anthropic tool definitions."""
    return [
        {
            "name": "find_sources",
            "description": "Search for KubeCon/CNCF talks and docs on a topic via Exa. Returns 8-10 sources sorted by relevance.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Cloud-native topic to research"},
                    "max_results": {"type": "integer", "description": "Max sources to return (default 8)"},
                },
                "required": ["topic"],
            },
        },
        {
            "name": "get_transcript",
            "description": "Fetch YouTube captions with timestamps for a video. Stores chunks in SQLite. Idempotent — skips already-ingested videos.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "video_url": {"type": "string", "description": "YouTube URL"},
                    "metadata": {"type": "object", "description": "Optional {title, author, year}"},
                },
                "required": ["video_url"],
            },
        },
        {
            "name": "compile_pages",
            "description": "Decide wiki page operations (create/update/flag_conflict) and generate markdown content. Checks existing wiki index for duplicates.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "object"}},
                    "transcript_results": {"type": "array", "items": {"type": "object"}},
                },
                "required": ["topic", "sources", "transcript_results"],
            },
        },
        {
            "name": "publish_wiki",
            "description": "Build the static MkDocs site. Returns delivery URL and status.",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "deliver",
            "description": "Send the wiki link to the buyer via Whop message.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "slug": {"type": "string"},
                    "page_url": {"type": "string"},
                },
                "required": ["order_id", "slug", "page_url"],
            },
        },
        {
            "name": "log_decision",
            "description": "Log a decision with reason, expected outcome, and actual outcome.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "decision": {"type": "string"},
                    "reason": {"type": "string"},
                    "expected": {"type": "string"},
                    "outcome": {"type": "string"},
                },
                "required": ["decision", "reason", "expected"],
            },
        },
    ]


def _handle_tool(name: str, inputs: dict) -> str:
    """Execute a tool call and return the result as a string."""
    if name == "find_sources":
        results = find_sources(inputs["topic"], inputs.get("max_results", 8))
        return json.dumps(results, ensure_ascii=False)

    elif name == "get_transcript":
        results = get_transcript(inputs["video_url"], inputs.get("metadata"))
        return json.dumps(results, ensure_ascii=False)

    elif name == "compile_pages":
        results = compile_pages(inputs["topic"], inputs["sources"], inputs["transcript_results"])
        # Write the page to disk
        if results.get("content"):
            write_page(results["slug"], results["content"])
        return json.dumps(results, ensure_ascii=False)

    elif name == "publish_wiki":
        results = publish_wiki()
        return json.dumps(results, ensure_ascii=False)

    elif name == "deliver":
        results = deliver(inputs["order_id"], inputs["slug"], inputs["page_url"])
        # Mark as delivered in DB
        mark_delivered(inputs["order_id"], inputs["page_url"], cost_usd=3.0)
        return json.dumps(results, ensure_ascii=False)

    elif name == "log_decision":
        log_decision(inputs["decision"], inputs["reason"], inputs.get("expected", ""), inputs.get("outcome", ""))
        return json.dumps({"status": "logged"}, ensure_ascii=False)

    return json.dumps({"error": f"unknown tool: {name}"})


def fulfill_order(order: dict) -> dict:
    """Run the 7-step fulfillment loop for a single order."""
    whop_id = order.get("id", "")
    topic = order.get("metadata", {}).get("topic", "")
    if not topic:
        # Fallback: ask the buyer
        from agent.tools.poll_orders import send_message
        send_message(whop_id, "What cloud-native topic would you like the wiki on? (e.g. Cilium, Gateway API, Argo CD)")
        return {"status": "waiting_for_topic", "order_id": whop_id}

    paid_at = order.get("created_at", datetime.utcnow().isoformat())
    record_order(whop_id, topic, paid_at)

    messages = [
        {
            "role": "user",
            "content": f"New paid order! Order ID: {whop_id}, Topic: '{topic}'. "
                       f"Research this topic, compile a wiki, publish it, and deliver the link to the buyer. "
                       f"Log your key decisions as you go.",
        }
    ]

    # Run the tool-calling loop (max 15 tool calls to prevent runaway)
    compiled_result = None
    for _ in range(15):
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=_tool_specs(),
            max_tokens=4096,
        )

        # Collect tool calls
        tool_calls = []
        for block in response.content:
            if block.type == "tool_use":
                tool_calls.append(block)

        if not tool_calls:
            # No more tools — agent is done
            break

        # Execute tools and build next message
        tool_results = []
        for tc in tool_calls:
            result = _handle_tool(tc.name, tc.input if isinstance(tc.input, dict) else {})
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc.id,
                "content": result,
            })

        # Append assistant response and tool results
        messages.append({"role": "assistant", "content": [
            block.model_dump() if hasattr(block, "model_dump") else block
            for block in response.content
        ]})
        messages.append({"role": "user", "content": tool_results})

    # Git commit the wiki changes
    try:
        import subprocess
        subprocess.run(["git", "add", "."], capture_output=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        subprocess.run(["git", "commit", "-m", f"wiki: {topic} (order {whop_id[:8]})"], capture_output=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    except Exception:
        pass

    return {"status": "fulfilled", "order_id": whop_id, "topic": topic}


def run_loop(poll_interval: int = 30):
    """Main polling loop — checks for new orders and fulfills them."""
    log_decision(
        "Started orchestrator loop",
        "Begin polling for paid orders",
        "Process all pending orders and deliver wikis",
    )

    print(f"[{datetime.utcnow().isoformat()}] CNCF Wiki Desk agent started. Polling every {poll_interval}s...")

    while True:
        try:
            orders = whop_poll()
            paid = [o for o in orders if o.get("status") == "paid"]

            if paid:
                print(f"  Found {len(paid)} new paid order(s)")
                for order in paid:
                    print(f"  Fulfilling order {order.get('id', '?')}...")
                    result = fulfill_order(order)
                    print(f"  Result: {result.get('status')}")
            else:
                print(f"  [{datetime.utcnow().strftime('%H:%M:%S')}] No new orders")

        except KeyboardInterrupt:
            print("\nShutting down...")
            break
        except Exception as e:
            print(f"  Error in loop: {e}")
            log_decision("Loop error", str(e), "recover", "retrying")

        time.sleep(poll_interval)


if __name__ == "__main__":
    # Write marketing copy on startup
    write_copy("./output")
    print("Marketing copy written to ./output/")

    # Start the fulfillment loop
    run_loop()
