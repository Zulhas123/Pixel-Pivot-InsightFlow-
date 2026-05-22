from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.base import Base
from app.db.models import Customer, Delivery, Order, OrderItem, Payment, Product, User


def main() -> None:
    url = os.getenv("SYNC_DATABASE_URL")
    if not url:
        raise RuntimeError("SYNC_DATABASE_URL is required")
    engine = create_engine(url, pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)

    with Session(engine) as s:
        _ensure_user(s, "admin@local", "Admin User", "Admin", "Admin1234!")
        _ensure_user(s, "manager@local", "Manager User", "Manager", "Manager1234!")
        agent = _ensure_user(s, "agent@local", "Delivery Agent", "DeliveryAgent", "Agent1234!")

        cust = _ensure_customer(s, name="Acme Corp", email="billing@acme.test", phone="+1-555-0100")

        p1 = _ensure_product(
            s,
            sku="SKU-001",
            name="Wireless Mouse",
            category="Electronics",
            price=Decimal("25.00"),
            cost=Decimal("12.00"),
            stock_qty=200,
        )
        p2 = _ensure_product(
            s,
            sku="SKU-002",
            name="Keyboard",
            category="Electronics",
            price=Decimal("45.00"),
            cost=Decimal("25.00"),
            stock_qty=150,
        )
        p3 = _ensure_product(
            s,
            sku="SKU-003",
            name="USB-C Cable",
            category="Accessories",
            price=Decimal("10.00"),
            cost=Decimal("3.00"),
            stock_qty=500,
        )

        existing_order_id = s.execute(select(Order.id).where(Order.customer_id == cust.id).limit(1)).scalar_one_or_none()
        if existing_order_id is not None:
            s.commit()
            return

        now = datetime.now(timezone.utc)
        for i in range(25):
            order = Order(customer_id=cust.id, status="paid", currency="USD", created_at=now - timedelta(days=i))
            s.add(order)
            s.flush()
            s.add_all(
                [
                    OrderItem(order_id=order.id, product_id=p1.id, qty=1 + (i % 3), unit_price=p1.price, unit_cost=p1.cost),
                    OrderItem(order_id=order.id, product_id=p3.id, qty=2, unit_price=p3.price, unit_cost=p3.cost),
                ]
            )
            total = (1 + (i % 3)) * p1.price + 2 * p3.price
            s.add(Payment(order_id=order.id, method="card", amount=total, status="paid", paid_at=order.created_at))
            promised = order.created_at + timedelta(days=3)
            delivered = promised - timedelta(hours=2) if i % 4 != 0 else promised + timedelta(hours=6)
            s.add(
                Delivery(
                    order_id=order.id,
                    agent_user_id=agent.id,
                    status="delivered",
                    promised_at=promised,
                    delivered_at=delivered,
                    created_at=order.created_at,
                )
            )
        s.commit()


def _ensure_user(s: Session, email: str, full_name: str, role: str, password: str) -> User:
    user = s.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user:
        return user
    user = User(email=email, full_name=full_name, role=role, hashed_password=hash_password(password), is_active=True)
    s.add(user)
    s.flush()
    return user


def _ensure_customer(s: Session, name: str, email: str, phone: str) -> Customer:
    cust = s.execute(select(Customer).where(Customer.email == email)).scalar_one_or_none()
    if cust is None:
        cust = Customer(name=name, email=email, phone=phone)
        s.add(cust)
        s.flush()
        return cust

    cust.name = name
    cust.phone = phone
    s.flush()
    return cust


def _ensure_product(
    s: Session,
    sku: str,
    name: str,
    category: str,
    price: Decimal,
    cost: Decimal,
    stock_qty: int,
) -> Product:
    product = s.execute(select(Product).where(Product.sku == sku)).scalar_one_or_none()
    if product is None:
        product = Product(sku=sku, name=name, category=category, price=price, cost=cost, stock_qty=stock_qty)
        s.add(product)
        s.flush()
        return product

    product.name = name
    product.category = category
    product.price = price
    product.cost = cost
    product.stock_qty = stock_qty
    s.flush()
    return product


if __name__ == "__main__":
    main()

