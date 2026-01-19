"""Spell schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SpellUpdate(BaseModel):
    """Spell content update."""

    content: Optional[str] = None
    content_html: Optional[str] = None


class SpellSummary(BaseModel):
    """Spell summary for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    version: int
    is_current: bool
    is_approved: bool
    created_at: datetime


class SpellDetail(SpellSummary):
    """Spell detail with content."""

    content: str
    content_html: Optional[str]
    prompt_used: Optional[str]
    model_used: Optional[str]
    approved_at: Optional[datetime]
    delivered_at: Optional[datetime]
    delivery_method: Optional[str]


class SpellList(BaseModel):
    """List of spells (for order detail)."""

    items: list[SpellSummary]
