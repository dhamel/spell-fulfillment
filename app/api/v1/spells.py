"""Spell management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.spell import Spell
from app.models.order import Order, OrderStatus
from app.schemas.spell import SpellDetail, SpellUpdate, SpellList

router = APIRouter()


@router.get("/{spell_id}", response_model=SpellDetail)
async def get_spell(
    spell_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> SpellDetail:
    """Get spell detail."""
    result = await db.execute(select(Spell).where(Spell.id == spell_id))
    spell = result.scalar_one_or_none()

    if not spell:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spell not found",
        )

    return SpellDetail.model_validate(spell, from_attributes=True)


@router.put("/{spell_id}", response_model=SpellDetail)
async def update_spell(
    spell_id: int,
    spell_update: SpellUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> SpellDetail:
    """Update spell content."""
    result = await db.execute(select(Spell).where(Spell.id == spell_id))
    spell = result.scalar_one_or_none()

    if not spell:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spell not found",
        )

    if spell.is_approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot edit an approved spell",
        )

    update_data = spell_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(spell, field, value)

    await db.commit()
    await db.refresh(spell)

    return SpellDetail.model_validate(spell, from_attributes=True)


@router.post("/{spell_id}/approve", response_model=SpellDetail)
async def approve_spell(
    spell_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> SpellDetail:
    """Approve spell and trigger delivery."""
    from datetime import datetime, timezone

    result = await db.execute(select(Spell).where(Spell.id == spell_id))
    spell = result.scalar_one_or_none()

    if not spell:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spell not found",
        )

    if spell.is_approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Spell is already approved",
        )

    # Approve the spell
    spell.is_approved = True
    spell.approved_at = datetime.now(timezone.utc)

    # Update order status
    order_result = await db.execute(select(Order).where(Order.id == spell.order_id))
    order = order_result.scalar_one_or_none()
    if order:
        order.status = OrderStatus.APPROVED

    await db.commit()
    await db.refresh(spell)

    # TODO: Trigger email delivery
    # from app.services.fulfillment.email import send_spell_email
    # await send_spell_email(spell, order)

    return SpellDetail.model_validate(spell, from_attributes=True)


@router.post("/{spell_id}/deliver", response_model=SpellDetail)
async def deliver_spell(
    spell_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> SpellDetail:
    """Manually trigger spell delivery."""
    from datetime import datetime, timezone

    result = await db.execute(select(Spell).where(Spell.id == spell_id))
    spell = result.scalar_one_or_none()

    if not spell:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spell not found",
        )

    if not spell.is_approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Spell must be approved before delivery",
        )

    # TODO: Implement actual email delivery
    # from app.services.fulfillment.email import send_spell_email
    # result = await send_spell_email(spell)

    spell.delivered_at = datetime.now(timezone.utc)
    spell.delivery_method = "email"

    # Update order status
    order_result = await db.execute(select(Order).where(Order.id == spell.order_id))
    order = order_result.scalar_one_or_none()
    if order:
        order.status = OrderStatus.DELIVERED

    await db.commit()
    await db.refresh(spell)

    return SpellDetail.model_validate(spell, from_attributes=True)
