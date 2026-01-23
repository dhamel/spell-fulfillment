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


class SpellGenerateRequest(BaseModel):
    """Request to generate a spell for an order."""

    custom_prompt: Optional[str] = None


class SpellGenerateResponse(BaseModel):
    """Response from spell generation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    version: int
    content: str
    prompt_used: Optional[str]
    model_used: Optional[str]
    is_current: bool
    created_at: datetime
    message: str = "Spell generated successfully"


class SpellRegenerateRequest(BaseModel):
    """Request to regenerate a spell (create new version)."""

    custom_prompt: Optional[str] = None


class SatisfactionCreate(BaseModel):
    """Create/update satisfaction rating."""

    star_rating: int
    notes: Optional[str] = None


class SatisfactionDetail(BaseModel):
    """Satisfaction rating detail."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    spell_id: int
    star_rating: int
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class EmailPreview(BaseModel):
    """Email preview for delivered spells."""

    subject: str
    html_content: str
    plain_content: str
    sent_to: str
    sent_at: Optional[datetime] = None
