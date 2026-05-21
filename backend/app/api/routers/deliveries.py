from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.api.schemas import DeliveryCreate, DeliveryOut
from app.db.models import Delivery, Order, User
from app.db.session import get_db

router = APIRouter(prefix="/deliveries", tags=["deliveries"])


@router.post("", response_model=DeliveryOut)
async def create_delivery(
    body: DeliveryCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("Admin", "Manager")),
) -> Delivery:
    order = (await db.execute(select(Order).where(Order.id == body.order_id))).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    existing = (await db.execute(select(Delivery).where(Delivery.order_id == body.order_id))).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=400, detail="Delivery already exists for order")
    delivery = Delivery(
        order_id=body.order_id,
        agent_user_id=body.agent_user_id,
        status=body.status,
        promised_at=body.promised_at,
        delivered_at=body.delivered_at,
    )
    db.add(delivery)
    await db.commit()
    await db.refresh(delivery)
    return delivery


@router.get("", response_model=list[DeliveryOut])
async def list_deliveries(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Delivery]:
    q = select(Delivery).order_by(Delivery.id.desc())
    if user.role == "DeliveryAgent":
        q = q.where(Delivery.agent_user_id == user.id)
    return (await db.execute(q)).scalars().all()


@router.post("/{delivery_id}/mark-delivered", response_model=DeliveryOut)
async def mark_delivered(
    delivery_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Delivery:
    delivery = (await db.execute(select(Delivery).where(Delivery.id == delivery_id))).scalar_one_or_none()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    if user.role == "DeliveryAgent" and delivery.agent_user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    delivery.status = "delivered"
    delivery.delivered_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(delivery)
    return delivery
