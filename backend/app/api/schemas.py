from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str = Field(min_length=8)
    role: str = Field(pattern="^(Admin|Manager|DeliveryAgent)$")


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class CustomerCreate(BaseModel):
    name: str
    email: EmailStr | None = None
    phone: str | None = None


class CustomerOut(CustomerCreate):
    id: int
    created_at: datetime


class ProductCreate(BaseModel):
    sku: str
    name: str
    category: str | None = None
    price: Decimal
    cost: Decimal
    stock_qty: int = 0


class ProductOut(ProductCreate):
    id: int
    created_at: datetime


class OrderItemIn(BaseModel):
    product_id: int
    qty: int = Field(gt=0)


class OrderCreate(BaseModel):
    customer_id: int
    items: list[OrderItemIn]


class OrderItemOut(BaseModel):
    id: int
    product_id: int
    qty: int
    unit_price: Decimal
    unit_cost: Decimal


class OrderOut(BaseModel):
    id: int
    customer_id: int
    status: str
    currency: str
    created_at: datetime
    items: list[OrderItemOut]


class PaymentCreate(BaseModel):
    order_id: int
    method: str = "card"
    amount: Decimal
    status: str = "paid"


class PaymentOut(BaseModel):
    id: int
    order_id: int
    method: str
    amount: Decimal
    status: str
    paid_at: datetime | None
    created_at: datetime


class DeliveryCreate(BaseModel):
    order_id: int
    agent_user_id: int | None = None
    status: str = "assigned"
    promised_at: datetime | None = None
    delivered_at: datetime | None = None


class DeliveryOut(BaseModel):
    id: int
    order_id: int
    agent_user_id: int | None
    status: str
    promised_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime


class KPIOut(BaseModel):
    total_sales: Decimal
    total_profit: Decimal
    orders_count: int
    avg_order_value: Decimal
    on_time_delivery_rate: float


class SalesTrendPoint(BaseModel):
    day: str
    sales: Decimal
    profit: Decimal


class InventoryStatusPoint(BaseModel):
    product_id: int
    sku: str
    name: str
    stock_qty: int

