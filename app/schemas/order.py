"""Order schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.order import OrderStatus
from app.schemas.spell import SpellDetail


class OrderBase(BaseModel):
    """Base order schema."""

    customer_name: Optional[str] = None
    intention: Optional[str] = None


class OrderUpdate(BaseModel):
    """Order update schema."""

    intention: Optional[str] = None
    spell_type_id: Optional[int] = None


class OrderSummary(BaseModel):
    """Order summary for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    etsy_receipt_id: int
    customer_name: Optional[str]
    raw_spell_type: Optional[str]
    status: OrderStatus
    created_at: datetime
    updated_at: datetime


class OrderDetail(OrderSummary):
    """Order detail with all fields."""

    customer_email: Optional[str]
    etsy_listing_id: Optional[int]
    etsy_transaction_id: Optional[int]
    spell_type_id: Optional[int]
    intention: Optional[str]
    personalization_data: Optional[dict]
    etsy_order_date: Optional[datetime]
    order_total_cents: Optional[int]
    currency_code: str
    current_spell: Optional[SpellDetail] = None


class OrderList(BaseModel):
    """Paginated order list."""

    items: list[OrderSummary]
    total: int
    page: int
    per_page: int
    pages: int
