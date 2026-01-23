"""Order schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import CastType, OrderStatus
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
    cast_type: CastType = CastType.CUSTOMER_CAST
    created_at: datetime
    updated_at: datetime
    is_test_order: bool = False


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


class ManualOrderCreate(BaseModel):
    """Request schema for creating a manual production order.

    This is for real orders entered manually before Etsy integration is ready.
    Unlike test orders, these are flagged as real orders and included in metrics.
    """

    customer_name: str = Field(..., min_length=1, max_length=255)
    customer_email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")

    spell_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Spell type slug (must exist in database)",
    )
    intention: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Customer's intention/wish for the spell",
    )
    personalization_data: Optional[dict] = Field(
        default=None,
        description="Additional personalization key-value pairs",
    )

    order_total_cents: int = Field(..., ge=0, description="Price paid in cents")
    currency_code: str = Field(default="USD", max_length=10)

    etsy_order_date: datetime = Field(
        ...,
        description="When the order was received from Etsy (copy from Etsy receipt)",
    )

    cast_type: CastType = Field(
        default=CastType.CUSTOMER_CAST,
        description="How the spell should be fulfilled: cast_by_us, customer_cast, or combination",
    )


class ManualOrderResponse(BaseModel):
    """Response schema for created manual order."""

    id: int
    etsy_receipt_id: int
    customer_name: str
    customer_email: str
    raw_spell_type: str
    intention: str
    status: str
    order_total_cents: int
    etsy_order_date: datetime
    created_at: datetime
    is_test_order: bool
    cast_type: str
    message: str
