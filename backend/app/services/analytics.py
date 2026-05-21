from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Delivery, Order, OrderItem


def _dec(v) -> Decimal:
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


async def compute_kpis(db: AsyncSession) -> dict:
    sales_q = select(
        func.coalesce(func.sum(OrderItem.qty * OrderItem.unit_price), 0).label("sales"),
        func.coalesce(func.sum(OrderItem.qty * (OrderItem.unit_price - OrderItem.unit_cost)), 0).label("profit"),
        func.count(func.distinct(Order.id)).label("orders_count"),
    ).select_from(Order).join(OrderItem, OrderItem.order_id == Order.id)
    row = (await db.execute(sales_q)).one()

    total_sales = _dec(row.sales)
    total_profit = _dec(row.profit)
    orders_count = int(row.orders_count or 0)
    avg_order_value = (total_sales / Decimal(orders_count)) if orders_count else Decimal("0")

    delivered_total = (await db.execute(select(func.count(Delivery.id)).where(Delivery.status == "delivered"))).scalar_one()
    on_time = (
        await db.execute(
            select(func.count(Delivery.id)).where(
                Delivery.status == "delivered",
                Delivery.promised_at.is_not(None),
                Delivery.delivered_at.is_not(None),
                Delivery.delivered_at <= Delivery.promised_at,
            )
        )
    ).scalar_one()
    on_time_rate = (float(on_time) / float(delivered_total)) if delivered_total else 0.0

    return {
        "total_sales": total_sales,
        "total_profit": total_profit,
        "orders_count": orders_count,
        "avg_order_value": avg_order_value,
        "on_time_delivery_rate": on_time_rate,
    }


def compute_kpis_sync(session) -> dict:
    sales_q = select(
        func.coalesce(func.sum(OrderItem.qty * OrderItem.unit_price), 0).label("sales"),
        func.coalesce(func.sum(OrderItem.qty * (OrderItem.unit_price - OrderItem.unit_cost)), 0).label("profit"),
        func.count(func.distinct(Order.id)).label("orders_count"),
    ).select_from(Order).join(OrderItem, OrderItem.order_id == Order.id)
    row = session.execute(sales_q).one()

    total_sales = _dec(row.sales)
    total_profit = _dec(row.profit)
    orders_count = int(row.orders_count or 0)
    avg_order_value = (total_sales / Decimal(orders_count)) if orders_count else Decimal("0")

    delivered_total = session.execute(select(func.count(Delivery.id)).where(Delivery.status == "delivered")).scalar_one()
    on_time = session.execute(
        select(func.count(Delivery.id)).where(
            Delivery.status == "delivered",
            Delivery.promised_at.is_not(None),
            Delivery.delivered_at.is_not(None),
            Delivery.delivered_at <= Delivery.promised_at,
        )
    ).scalar_one()
    on_time_rate = (float(on_time) / float(delivered_total)) if delivered_total else 0.0

    return {
        "total_sales": total_sales,
        "total_profit": total_profit,
        "orders_count": orders_count,
        "avg_order_value": avg_order_value,
        "on_time_delivery_rate": on_time_rate,
    }
