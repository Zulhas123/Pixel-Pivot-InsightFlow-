from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.api.schemas import PaymentCreate, PaymentOut
from app.db.models import Order, Payment, User
from app.db.session import get_db

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("", response_model=PaymentOut)
async def create_payment(
    body: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("Admin", "Manager")),
) -> Payment:
    order = (await db.execute(select(Order).where(Order.id == body.order_id))).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    existing = (await db.execute(select(Payment).where(Payment.order_id == body.order_id))).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=400, detail="Payment already exists for order")
    payment = Payment(
        order_id=body.order_id,
        method=body.method,
        amount=body.amount,
        status=body.status,
        paid_at=datetime.now(timezone.utc) if body.status == "paid" else None,
    )
    order.status = "paid" if body.status == "paid" else order.status
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


@router.get("", response_model=list[PaymentOut])
async def list_payments(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("Admin", "Manager")),
) -> list[Payment]:
    return (await db.execute(select(Payment).order_by(Payment.id.desc()))).scalars().all()
