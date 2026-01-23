"""Spell management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.spell import Spell
from app.models.order import CastType, Order, OrderStatus
from app.models.satisfaction import Satisfaction
from app.schemas.spell import (
    SpellDetail,
    SpellUpdate,
    SpellList,
    SpellGenerateRequest,
    SpellGenerateResponse,
    SpellRegenerateRequest,
    SatisfactionCreate,
    SatisfactionDetail,
    EmailPreview,
)

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
    """Manually trigger spell delivery via email.

    The email content varies based on the order's cast_type:
    - CAST_BY_US: Boilerplate confirmation that spell was cast on their behalf
    - CUSTOMER_CAST: AI-generated spell instructions for customer
    - COMBINATION: Both cast confirmation + customer instructions
    """
    from datetime import datetime, timezone
    from app.services.fulfillment import (
        send_spell_email,
        send_cast_by_us_email,
        send_combination_email,
        EmailDeliveryError,
    )

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

    if spell.delivered_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Spell has already been delivered",
        )

    # Get the associated order for customer details
    order_result = await db.execute(select(Order).where(Order.id == spell.order_id))
    order = order_result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated order not found",
        )

    if not order.customer_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer email not available for this order",
        )

    # Send the appropriate email based on cast_type
    customer_name = order.customer_name or "Valued Customer"
    spell_type = order.raw_spell_type or "Personalized"
    intention = order.intention or ""

    try:
        if order.cast_type == CastType.CAST_BY_US:
            # Send cast-by-us confirmation email
            email_result = await send_cast_by_us_email(
                to_email=order.customer_email,
                customer_name=customer_name,
                spell_type=spell_type,
                intention=intention,
            )
        elif order.cast_type == CastType.COMBINATION:
            # Send combination email (cast confirmation + instructions)
            email_result = await send_combination_email(
                to_email=order.customer_email,
                customer_name=customer_name,
                spell_type=spell_type,
                intention=intention,
                spell_instructions=spell.content,
            )
        else:
            # Default: CUSTOMER_CAST - send AI-generated instructions
            email_result = await send_spell_email(
                to_email=order.customer_email,
                customer_name=customer_name,
                spell_content=spell.content,
                spell_type=spell_type,
            )

        if not email_result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Email delivery failed: {email_result.error}",
            )

        # Update spell with delivery info
        spell.delivered_at = datetime.now(timezone.utc)
        spell.delivery_method = "email"
        spell.delivery_reference = email_result.message_id

        # Update order status
        order.status = OrderStatus.DELIVERED

        await db.commit()
        await db.refresh(spell)

        return SpellDetail.model_validate(spell, from_attributes=True)

    except EmailDeliveryError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Email service error: {e.message}",
        )


@router.get("/{spell_id}/email-preview", response_model=EmailPreview)
async def get_spell_email_preview(
    spell_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> EmailPreview:
    """Get a preview of the email that was/will be sent for this spell.

    This endpoint reconstructs the email content based on the order's cast_type.
    Useful for viewing what the customer received after delivery.
    """
    from app.services.fulfillment import get_email_preview

    result = await db.execute(select(Spell).where(Spell.id == spell_id))
    spell = result.scalar_one_or_none()

    if not spell:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spell not found",
        )

    # Get the associated order for customer details
    order_result = await db.execute(select(Order).where(Order.id == spell.order_id))
    order = order_result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated order not found",
        )

    # Generate the email preview
    customer_name = order.customer_name or "Valued Customer"
    spell_type = order.raw_spell_type or "Personalized"
    intention = order.intention or ""
    cast_type = order.cast_type.value if order.cast_type else "customer_cast"

    preview = get_email_preview(
        cast_type=cast_type,
        customer_name=customer_name,
        spell_type=spell_type,
        intention=intention,
        spell_content=spell.content,
    )

    return EmailPreview(
        subject=preview.subject,
        html_content=preview.html_content,
        plain_content=preview.plain_content,
        sent_to=order.customer_email or "",
        sent_at=spell.delivered_at,
    )


@router.post("/{spell_id}/regenerate", response_model=SpellGenerateResponse)
async def regenerate_spell_endpoint(
    spell_id: int,
    request: SpellRegenerateRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> SpellGenerateResponse:
    """Regenerate a spell (create new version).

    Creates a new version of the spell using Claude AI.
    The new version becomes the current spell for the order.
    """
    from app.services.claude import regenerate_spell, SpellGenerationError

    result = await db.execute(select(Spell).where(Spell.id == spell_id))
    spell = result.scalar_one_or_none()

    if not spell:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spell not found",
        )

    try:
        new_spell = await regenerate_spell(db, spell_id, request.custom_prompt)
        return SpellGenerateResponse(
            id=new_spell.id,
            order_id=new_spell.order_id,
            version=new_spell.version,
            content=new_spell.content,
            prompt_used=new_spell.prompt_used,
            model_used=new_spell.model_used,
            is_current=new_spell.is_current,
            created_at=new_spell.created_at,
            message=f"Spell regenerated successfully (version {new_spell.version})",
        )
    except SpellGenerationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message,
        )


@router.get("/{spell_id}/satisfaction", response_model=SatisfactionDetail)
async def get_satisfaction(
    spell_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> SatisfactionDetail:
    """Get satisfaction rating for a spell."""
    result = await db.execute(
        select(Satisfaction).where(Satisfaction.spell_id == spell_id)
    )
    satisfaction = result.scalar_one_or_none()

    if not satisfaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No satisfaction rating found for this spell",
        )

    return SatisfactionDetail.model_validate(satisfaction, from_attributes=True)


@router.post("/{spell_id}/satisfaction", response_model=SatisfactionDetail)
async def create_or_update_satisfaction(
    spell_id: int,
    satisfaction_data: SatisfactionCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> SatisfactionDetail:
    """Create or update satisfaction rating for a spell."""
    # Verify spell exists
    spell_result = await db.execute(select(Spell).where(Spell.id == spell_id))
    spell = spell_result.scalar_one_or_none()

    if not spell:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spell not found",
        )

    # Validate star rating
    if not 1 <= satisfaction_data.star_rating <= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Star rating must be between 1 and 5",
        )

    # Check for existing satisfaction
    result = await db.execute(
        select(Satisfaction).where(Satisfaction.spell_id == spell_id)
    )
    satisfaction = result.scalar_one_or_none()

    if satisfaction:
        # Update existing
        satisfaction.star_rating = satisfaction_data.star_rating
        satisfaction.notes = satisfaction_data.notes
    else:
        # Create new
        satisfaction = Satisfaction(
            spell_id=spell_id,
            star_rating=satisfaction_data.star_rating,
            notes=satisfaction_data.notes,
        )
        db.add(satisfaction)

    await db.commit()
    await db.refresh(satisfaction)

    return SatisfactionDetail.model_validate(satisfaction, from_attributes=True)


@router.delete("/{spell_id}/satisfaction", status_code=status.HTTP_204_NO_CONTENT)
async def delete_satisfaction(
    spell_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> None:
    """Delete satisfaction rating for a spell."""
    result = await db.execute(
        select(Satisfaction).where(Satisfaction.spell_id == spell_id)
    )
    satisfaction = result.scalar_one_or_none()

    if not satisfaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No satisfaction rating found for this spell",
        )

    await db.delete(satisfaction)
    await db.commit()
