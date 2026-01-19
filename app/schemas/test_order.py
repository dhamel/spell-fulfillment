"""Schemas for test order creation (development only)."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class TestOrderCreate(BaseModel):
    """Request schema for creating a test order."""

    customer_name: str = Field(..., min_length=1, max_length=255)
    customer_email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")

    spell_type: str = Field(
        default="love",
        description="Spell type: love, prosperity, protection, healing",
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

    @field_validator("spell_type")
    @classmethod
    def validate_spell_type(cls, v: str) -> str:
        valid_types = ["love", "prosperity", "protection", "healing"]
        if v.lower() not in valid_types:
            raise ValueError(f"spell_type must be one of: {valid_types}")
        return v.lower()


class TestOrderBulkCreate(BaseModel):
    """Request schema for creating multiple test orders."""

    count: int = Field(default=5, ge=1, le=50)
    spell_types: Optional[list[str]] = Field(
        default=None,
        description="If provided, cycles through these types. Otherwise random.",
    )

    @field_validator("spell_types")
    @classmethod
    def validate_spell_types(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return None
        valid_types = ["love", "prosperity", "protection", "healing"]
        for spell_type in v:
            if spell_type.lower() not in valid_types:
                raise ValueError(f"Invalid spell_type '{spell_type}'. Must be one of: {valid_types}")
        return [t.lower() for t in v]


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
