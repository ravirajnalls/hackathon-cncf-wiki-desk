"""Send the wiki link to the buyer through Whop."""

from agent.tools.poll_orders import send_message


def deliver(order_id: str, slug: str, page_url: str) -> dict:
    """Deliver the wiki to the buyer via Whop message."""
    message = (
        f"✅ Your CNCF Wiki on '{slug}' is ready!\n\n"
        f"📖 View it here: {page_url}\n\n"
        f"Every claim is cited with a clickable video timestamp. "
        f"If you need a different topic, just order again."
    )

    result = send_message(order_id, message)
    return {"status": "delivered", "order_id": order_id, "page_url": page_url, "whop_result": result}
