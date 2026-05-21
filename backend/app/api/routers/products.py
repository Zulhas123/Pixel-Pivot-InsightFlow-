from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.api.schemas import ProductCreate, ProductOut
from app.db.models import Product, User
from app.db.session import get_db

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=ProductOut)
async def create_product(
    body: ProductCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("Admin", "Manager")),
) -> Product:
    exists = (await db.execute(select(Product).where(Product.sku == body.sku))).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail="SKU already exists")
    product = Product(
        sku=body.sku,
        name=body.name,
        category=body.category,
        price=body.price,
        cost=body.cost,
        stock_qty=body.stock_qty,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.get("", response_model=list[ProductOut])
async def list_products(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("Admin", "Manager")),
) -> list[Product]:
    return (await db.execute(select(Product).order_by(Product.id.desc()))).scalars().all()

