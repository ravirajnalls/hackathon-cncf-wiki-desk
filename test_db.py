from agent.db import get_db, log_decision, record_order, pending_orders, mark_delivered

log_decision("test", "verify db works", "no errors")
record_order("test-order-123", "Cilium", "2026-10-24T12:00:00")
orders = pending_orders()
print(f"Pending orders: {len(orders)}")
for o in orders:
    print(f"  {o['whop_id']} — {o['topic']}")

mark_delivered("test-order-123", "https://example.com/wiki/cilium", 3.0)
orders_after = pending_orders()
print(f"After delivery, pending: {len(orders_after)}")
print("DB OK")
