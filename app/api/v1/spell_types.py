"""Spell type management endpoints."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.config import get_settings
from app.models.spell_type import SpellType
from app.schemas.spell_type import (
    SpellTypeCreate,
    SpellTypeDetail,
    SpellTypeList,
    SpellTypeUpdate,
)

router = APIRouter()
settings = get_settings()


@router.get("", response_model=SpellTypeList)
async def list_spell_types(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> SpellTypeList:
    """List all spell types with PDF status."""
    result = await db.execute(
        select(SpellType).where(SpellType.is_active == True).order_by(SpellType.display_order)
    )
    spell_types = result.scalars().all()

    return SpellTypeList(items=spell_types)


def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from a name."""
    import re
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    slug = slug.strip("-")
    return slug


DEFAULT_PROMPT_TEMPLATE = """You are a skilled spell crafter creating a personalized {spell_type} spell.

Customer Name: {customer_name}
Customer's Intention: {intention}

Create a meaningful, personalized spell that:
1. Addresses the customer by name
2. Incorporates their specific intention
3. Uses appropriate magical language and imagery
4. Provides clear instructions for the ritual
5. Includes any necessary materials or timing recommendations

Write the spell in a warm, mystical tone that feels authentic and personal."""


@router.post("", response_model=SpellTypeDetail, status_code=status.HTTP_201_CREATED)
async def create_spell_type(
    spell_type_data: SpellTypeCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> SpellTypeDetail:
    """Create a new spell type."""
    # Generate slug from name
    slug = generate_slug(spell_type_data.name)

    # Check if name or slug already exists
    existing = await db.execute(
        select(SpellType).where(
            (SpellType.name == spell_type_data.name) | (SpellType.slug == slug)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A spell type with this name already exists",
        )

    # Get max display order
    max_order_result = await db.execute(
        select(SpellType.display_order).order_by(SpellType.display_order.desc()).limit(1)
    )
    max_order = max_order_result.scalar() or 0

    # Create the spell type
    spell_type = SpellType(
        name=spell_type_data.name,
        slug=slug,
        description=spell_type_data.description,
        prompt_template=spell_type_data.prompt_template or DEFAULT_PROMPT_TEMPLATE,
        is_active=True,
        display_order=max_order + 1,
    )

    db.add(spell_type)
    await db.commit()
    await db.refresh(spell_type)

    return SpellTypeDetail.model_validate(spell_type, from_attributes=True)


@router.get("/{spell_type_id}", response_model=SpellTypeDetail)
async def get_spell_type(
    spell_type_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> SpellTypeDetail:
    """Get spell type detail with prompt template."""
    result = await db.execute(select(SpellType).where(SpellType.id == spell_type_id))
    spell_type = result.scalar_one_or_none()

    if not spell_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spell type not found",
        )

    return SpellTypeDetail.model_validate(spell_type, from_attributes=True)


@router.put("/{spell_type_id}", response_model=SpellTypeDetail)
async def update_spell_type(
    spell_type_id: int,
    spell_type_update: SpellTypeUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> SpellTypeDetail:
    """Update spell type (name, prompt template, etc.)."""
    result = await db.execute(select(SpellType).where(SpellType.id == spell_type_id))
    spell_type = result.scalar_one_or_none()

    if not spell_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spell type not found",
        )

    update_data = spell_type_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(spell_type, field, value)

    await db.commit()
    await db.refresh(spell_type)

    return SpellTypeDetail.model_validate(spell_type, from_attributes=True)


@router.post("/{spell_type_id}/pdf", response_model=SpellTypeDetail)
async def upload_stock_pdf(
    spell_type_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> SpellTypeDetail:
    """Upload stock PDF for a spell type."""
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed",
        )

    # Check file size
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit",
        )

    # Get spell type
    result = await db.execute(select(SpellType).where(SpellType.id == spell_type_id))
    spell_type = result.scalar_one_or_none()

    if not spell_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spell type not found",
        )

    # Save file
    upload_dir = Path(settings.UPLOAD_DIR) / "stock_pdfs"
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{spell_type.slug}_{spell_type_id}.pdf"
    file_path = upload_dir / filename

    with open(file_path, "wb") as f:
        f.write(content)

    # Update spell type with PDF path
    spell_type.stock_pdf_path = str(file_path)

    await db.commit()
    await db.refresh(spell_type)

    return SpellTypeDetail.model_validate(spell_type, from_attributes=True)


@router.delete("/{spell_type_id}/pdf", response_model=SpellTypeDetail)
async def delete_stock_pdf(
    spell_type_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> SpellTypeDetail:
    """Delete stock PDF for a spell type."""
    result = await db.execute(select(SpellType).where(SpellType.id == spell_type_id))
    spell_type = result.scalar_one_or_none()

    if not spell_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spell type not found",
        )

    if spell_type.stock_pdf_path:
        # Delete file if exists
        file_path = Path(spell_type.stock_pdf_path)
        if file_path.exists():
            file_path.unlink()

        spell_type.stock_pdf_path = None
        await db.commit()
        await db.refresh(spell_type)

    return SpellTypeDetail.model_validate(spell_type, from_attributes=True)
