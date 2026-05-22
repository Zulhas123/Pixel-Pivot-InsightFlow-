from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.db.models import Customer, Delivery, Order, OrderItem, Payment, Product, User
from app.db.session import get_db
from app.services.cache import cache_delete, cache_delete_prefix

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/activity")
async def create_demo_activity(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("Admin", "Manager")),
):
    """
    Create a small unit of demo activity that changes KPIs within the next poll:

    - new Order (+ 1 OrderItem)
    - new paid Payment
    - new delivered Delivery

    Also clears analytics caches so the next request reflects the change immediately.
    """

    cust = (await db.execute(select(Customer).order_by(Customer.id.asc()).limit(1))).scalar_one_or_none()
    if cust is None:
        raise HTTPException(status_code=400, detail="No customers found. Run seed first.")

    product = (await db.execute(select(Product).order_by(Product.id.asc()).limit(1))).scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=400, detail="No products found. Run seed first.")

    agent = (
        await db.execute(select(User).where(User.role == "DeliveryAgent").order_by(User.id.asc()).limit(1))
    ).scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=400, detail="No DeliveryAgent found. Run seed first.")

    qty = 1
    if product.stock_qty < qty:
        raise HTTPException(status_code=400, detail=f"Insufficient stock for product {product.sku}")
    product.stock_qty -= qty

    now = datetime.now(timezone.utc)
    order = Order(customer_id=cust.id, status="paid", currency="USD", created_at=now)
    db.add(order)
    await db.flush()

    unit_price = Decimal(product.price)
    unit_cost = Decimal(product.cost)
    db.add(OrderItem(order_id=order.id, product_id=product.id, qty=qty, unit_price=unit_price, unit_cost=unit_cost))

    amount = qty * unit_price
    db.add(Payment(order_id=order.id, method="card", amount=amount, status="paid", paid_at=now))

    promised = now + timedelta(days=3)
    db.add(
        Delivery(
            order_id=order.id,
            agent_user_id=agent.id,
            status="delivered",
            promised_at=promised,
            delivered_at=now,
            created_at=now,
        )
    )

    await db.commit()

    # Clear analytics caches so KPIs change immediately (no waiting for TTL).
    await cache_delete("analytics:kpis:v1")
    await cache_delete("analytics:finance_summary:v1")
    await cache_delete_prefix("analytics:sales_trend:v1:")

    return {"order_id": order.id, "product_id": product.id, "customer_id": cust.id, "amount": str(amount)}

