"""Whop order intake — poll for new paid orders."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env even when this module is run on its own (python -m agent.tools.…)
load_dotenv(Path(__file__).parent.parent.parent / ".env")
import requests

WHOP_API_KEY = os.environ.get("WHOP_API_KEY", "")
WHOP_BUSINESS_ID = os.environ.get("WHOP_BUSINESS_ID", "")
WHOP_MODE = os.environ.get("WHOP_MODE", "sandbox")
# Whop API v1 (docs.whop.com/api-reference/payments/list-payments)
WHOP_BASE = ("https://sandbox-api.whop.com/api/v1" if WHOP_MODE == "sandbox"
             else "https://api.whop.com/api/v1")


def _headers():
    if not WHOP_API_KEY:
        raise RuntimeError("WHOP_API_KEY is not set: add it to .env")
    return {
        "Authorization": f"Bearer {WHOP_API_KEY}",
        "Content-Type": "application/json",
    }


def poll_orders(status: str = "paid") -> list[dict]:
    """Return the most recent payments for the business, filtered to `status`.

    Payment fields used: id, status, paid_at, created_at, metadata (may hold
    'topic'), user {id, email}, product {id}.
    """
    resp = requests.get(
        f"{WHOP_BASE}/payments",
        headers=_headers(),
        params={"account_id": WHOP_BUSINESS_ID, "first": 20, "order": "created_at", "direction": "desc"},
        timeout=15,
    )
    resp.raise_for_status()
    return [p for p in resp.json().get("data", []) if p.get("status") == status]


def get_order(order_id: str) -> dict:
    """Fetch a single payment by id."""
    resp = requests.get(f"{WHOP_BASE}/payments/{order_id}", headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_checkout_answers(membership_id: str) -> list[dict]:
    """Buyer's answers to the plan's checkout questions: [{question, answer}].

    Add a required text custom field (e.g. "Which cloud-native topic?") to the
    $3 plan in the Whop dashboard; answers live on the membership.
    """
    resp = requests.get(f"{WHOP_BASE}/memberships/{membership_id}", headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json().get("custom_field_responses") or []


def send_message(order_id: str, message: str) -> dict:
    """Send a message to the buyer through Whop.

    Unverified endpoint: the fulfillment subprocess delivers through the Whop MCP
    instead, so this is only used by agent/tools/deliver.py.
    """
    resp = requests.post(
        f"{WHOP_BASE}/orders/{order_id}/message",
        headers=_headers(),
        json={"message": message},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    # quick test
    orders = poll_orders()
    print(f"Found {len(orders)} paid payments ({WHOP_MODE})")
    for o in orders:
        print(f"  {o.get('id')} — status={o.get('status')} product={o.get('product_id')}")
