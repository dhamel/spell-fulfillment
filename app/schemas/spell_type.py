"""Spell type schemas."""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class SpellTypeUpdate(BaseModel):
    """Spell type update schema."""

    name: Optional[str] = None
    description: Optional[str] = None
    prompt_template: Optional[str] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


class SpellTypeSummary(BaseModel):
    """Spell type summary for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: Optional[str]
    is_active: bool
    has_stock_pdf: bool


class SpellTypeDetail(SpellTypeSummary):
    """Spell type detail with prompt template."""

    prompt_template: str
    stock_pdf_path: Optional[str]
    display_order: int


class SpellTypeList(BaseModel):
    """List of spell types."""

    items: list[SpellTypeSummary]
