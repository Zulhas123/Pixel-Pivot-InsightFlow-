from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.api.schemas import CustomerCreate, CustomerOut
from app.db.models import Customer, User
from app.db.session import get_db

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("", response_model=CustomerOut)
async def create_customer(
    body: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("Admin", "Manager")),
) -> Customer:
    customer = Customer(name=body.name, email=body.email, phone=body.phone)
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer


@router.get("", response_model=list[CustomerOut])
async def list_customers(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("Admin", "Manager")),
) -> list[Customer]:
    return (await db.execute(select(Customer).order_by(Customer.id.desc()))).scalars().all()

