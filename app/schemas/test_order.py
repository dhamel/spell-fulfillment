"""Schemas for test order creation (development only)."""

from typing import Optional

from pydantic import BaseModel, Field


class TestOrderCreate(BaseModel):
    """Request schema for creating a test order."""

    customer_name: str = Field(..., min_length=1, max_length=255)
    customer_email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")

    spell_type: str = Field(
        default="love",
        min_length=1,
        max_length=100,
        description="Spell type slug or name (any custom type is allowed)",
    )
    intention: str = Field(
        default="For testing purposes",
        min_length=1,
        max_length=2000,
    )
    personalization_data: Optional[dict] = Field(
        default=None,
        description="Additional personalization key-value pairs",
    )

    order_total_cents: int = Field(default=2999, ge=0)
    currency_code: str = Field(default="USD", max_length=10)


class TestOrderBulkCreate(BaseModel):
    """Request schema for creating multiple test orders."""

    count: int = Field(default=5, ge=1, le=50)
    spell_types: Optional[list[str]] = Field(
        default=None,
        description="If provided, cycles through these types. Otherwise uses defaults.",
    )


class TestOrderResponse(BaseModel):
    """Response schema for created test order."""

    id: int
    etsy_receipt_id: int
    customer_name: str
    customer_email: str
    raw_spell_type: str
    intention: str
    status: str
    message: str
