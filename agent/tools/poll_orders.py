"""Whop order intake — poll for new paid orders."""

import os
import requests

WHOP_API_KEY = os.environ.get("WHOP_API_KEY", "")
WHOP_BUSINESS_ID = os.environ.get("WHOP_BUSINESS_ID", "")
WHOP_MODE = os.environ.get("WHOP_MODE", "sandbox")
WHOP_BASE = "https://api.whop.com/v1"


def _headers():
    if not WHOP_API_KEY:
        raise RuntimeError("WHOP_API_KEY is not set: add it to .env")
    return {
        "Authorization": f"Bearer {WHOP_API_KEY}",
        "Content-Type": "application/json",
    }


def poll_orders(status: str = "paid") -> list[dict]:
    """Return recent paid orders from Whop.

    Response items include:
      - id (whop order id)
      - product_id
      - user_id
      - created_at
      - metadata / custom fields (may contain 'topic')
      - buyer email
    """
    resp = requests.get(
        f"{WHOP_BASE}/orders",
        headers=_headers(),
        params={"business_id": WHOP_BUSINESS_ID, "status": status, "limit": 20},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def get_order(order_id: str) -> dict:
    """Fetch a single order by id."""
    resp = requests.get(f"{WHOP_BASE}/orders/{order_id}", headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


def send_message(order_id: str, message: str) -> dict:
    """Send a message to the buyer through Whop."""
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
    print(f"Found {len(orders)} orders")
    for o in orders:
        print(f"  {o.get('id')} — status={o.get('status')} product={o.get('product_id')}")
