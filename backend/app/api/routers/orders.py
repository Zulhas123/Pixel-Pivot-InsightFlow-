from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_roles
from app.api.schemas import OrderCreate, OrderOut
from app.db.models import Customer, Order, OrderItem, Product, User
from app.db.session import get_db

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderOut)
async def create_order(
    body: OrderCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("Admin", "Manager")),
) -> Order:
    customer = (await db.execute(select(Customer).where(Customer.id == body.customer_id))).scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    order = Order(customer_id=body.customer_id, status="created", currency="USD")
    db.add(order)
    await db.flush()

    for item in body.items:
        product = (await db.execute(select(Product).where(Product.id == item.product_id))).scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        if product.stock_qty < item.qty:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for product {product.sku}")
        product.stock_qty -= item.qty
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                qty=item.qty,
                unit_price=Decimal(product.price),
                unit_cost=Decimal(product.cost),
            )
        )

    await db.commit()
    order = (
        await db.execute(select(Order).where(Order.id == order.id).options(selectinload(Order.items)))
    ).scalar_one()
    return order


@router.get("", response_model=list[OrderOut])
async def list_orders(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("Admin", "Manager")),
) -> list[Order]:
    q = select(Order).options(selectinload(Order.items)).order_by(Order.id.desc())
    return (await db.execute(q)).scalars().all()

