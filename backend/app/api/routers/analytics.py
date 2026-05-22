from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import plotly.graph_objects as go
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.api.schemas import FinanceByMethodPoint, FinanceSummaryOut, InventoryStatusPoint, KPIOut, SalesTrendPoint
from app.db.models import Delivery, Order, OrderItem, Payment, Product, User
from app.db.session import get_db
from app.services.cache import cache_get_json, cache_set_json

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _dec(v) -> Decimal:
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


@router.get("/kpis", response_model=KPIOut)
async def kpis(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("Admin", "Manager")),
) -> KPIOut:
    cache_key = "analytics:kpis:v1"
    cached = await cache_get_json(cache_key)
    if cached:
        return KPIOut(**cached)

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

    # delivery on-time rate: delivered_at <= promised_at
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

    payload = {
        "total_sales": str(total_sales),
        "total_profit": str(total_profit),
        "orders_count": orders_count,
        "avg_order_value": str(avg_order_value),
        "on_time_delivery_rate": on_time_rate,
    }
    await cache_set_json(cache_key, payload, ttl_seconds=15)
    return KPIOut(
        total_sales=total_sales,
        total_profit=total_profit,
        orders_count=orders_count,
        avg_order_value=avg_order_value,
        on_time_delivery_rate=on_time_rate,
    )


@router.get("/sales-trend", response_model=list[SalesTrendPoint])
async def sales_trend(
    days: int = 14,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("Admin", "Manager")),
) -> list[SalesTrendPoint]:
    days = max(1, min(days, 90))
    cache_key = f"analytics:sales_trend:v1:{days}"
    cached = await cache_get_json(cache_key)
    if cached:
        return [SalesTrendPoint(**p) for p in cached]

    since = datetime.now(timezone.utc) - timedelta(days=days)
    day = func.date_trunc("day", Order.created_at).label("day")
    q = (
        select(
            day,
            func.coalesce(func.sum(OrderItem.qty * OrderItem.unit_price), 0).label("sales"),
            func.coalesce(func.sum(OrderItem.qty * (OrderItem.unit_price - OrderItem.unit_cost)), 0).label("profit"),
        )
        .select_from(Order)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .where(Order.created_at >= since)
        .group_by(day)
        .order_by(day.asc())
    )
    rows = (await db.execute(q)).all()
    points: list[dict] = []
    for r in rows:
        points.append(
            {
                "day": r.day.date().isoformat(),
                "sales": str(_dec(r.sales)),
                "profit": str(_dec(r.profit)),
            }
        )
    await cache_set_json(cache_key, points, ttl_seconds=15)
    return [SalesTrendPoint(day=p["day"], sales=Decimal(p["sales"]), profit=Decimal(p["profit"])) for p in points]


@router.get("/sales-trend/plotly")
async def sales_trend_plotly(
    days: int = 14,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("Admin", "Manager")),
):
    """
    Plotly-compatible figure JSON for the sales/profit trend.

    This is a minimal demo endpoint to support Plotly-based visualization
    without changing the underlying analytics logic.
    """

    points = await sales_trend(days=days, db=db, _=_)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[p.day for p in points], y=[float(p.sales) for p in points], mode="lines", name="Sales"))
    fig.add_trace(go.Scatter(x=[p.day for p in points], y=[float(p.profit) for p in points], mode="lines", name="Profit"))
    fig.update_layout(margin=dict(l=20, r=20, t=30, b=20), template="plotly_dark", legend=dict(orientation="h"))
    return fig.to_dict()


@router.get("/inventory-status", response_model=list[InventoryStatusPoint])
async def inventory_status(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("Admin", "Manager")),
) -> list[InventoryStatusPoint]:
    q = select(Product.id, Product.sku, Product.name, Product.stock_qty).order_by(Product.stock_qty.asc(), Product.id.asc())
    rows = (await db.execute(q)).all()
    return [InventoryStatusPoint(product_id=r.id, sku=r.sku, name=r.name, stock_qty=r.stock_qty) for r in rows]


@router.get("/finance-summary", response_model=FinanceSummaryOut)
async def finance_summary(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("Admin", "Manager")),
) -> FinanceSummaryOut:
    """
    Lightweight finance analytics for the demo app.

    - `paid_total` / `payments_count`: derived from `payments` where status='paid'
    - `paid_by_method`: breakdown by payment method (e.g. card, cash)
    """

    cache_key = "analytics:finance_summary:v1"
    cached = await cache_get_json(cache_key)
    if cached:
        return FinanceSummaryOut(**cached)

    totals_q = select(
        func.coalesce(func.sum(Payment.amount), 0).label("paid_total"),
        func.count(Payment.id).label("payments_count"),
    ).where(Payment.status == "paid")
    totals = (await db.execute(totals_q)).one()
    paid_total = _dec(totals.paid_total)
    payments_count = int(totals.payments_count or 0)
    avg_payment = (paid_total / Decimal(payments_count)) if payments_count else Decimal("0")

    by_method_q = (
        select(
            Payment.method.label("method"),
            func.coalesce(func.sum(Payment.amount), 0).label("paid_total"),
            func.count(Payment.id).label("payments_count"),
        )
        .where(Payment.status == "paid")
        .group_by(Payment.method)
        .order_by(Payment.method.asc())
    )
    rows = (await db.execute(by_method_q)).all()
    points = [
        {"method": r.method, "paid_total": str(_dec(r.paid_total)), "payments_count": int(r.payments_count or 0)} for r in rows
    ]

    payload = {
        "paid_total": str(paid_total),
        "payments_count": payments_count,
        "avg_payment": str(avg_payment),
        "paid_by_method": points,
    }
    await cache_set_json(cache_key, payload, ttl_seconds=15)
    return FinanceSummaryOut(
        paid_total=paid_total,
        payments_count=payments_count,
        avg_payment=avg_payment,
        paid_by_method=[
            FinanceByMethodPoint(method=p["method"], paid_total=Decimal(p["paid_total"]), payments_count=p["payments_count"])
            for p in points
        ],
    )

