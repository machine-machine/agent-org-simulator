# PR #1250: Add order summary endpoint
def get_order_summaries(db, customer_id: int):
    """Get all orders with their line items for a customer."""
    orders = db.execute(
        "SELECT * FROM orders WHERE customer_id = ?", (customer_id,)
    ).fetchall()
    
    summaries = []
    for order in orders:
        items = db.execute(
            "SELECT * FROM order_items WHERE order_id = ?", (order["id"],)
        ).fetchall()
        total = sum(item["price"] * item["quantity"] for item in items)
        summaries.append({
            "order_id": order["id"],
            "date": order["created_at"],
            "item_count": len(items),
            "total": total,
        })
    return summaries
