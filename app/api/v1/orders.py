"""Order management endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.order import Order, OrderStatus
from app.schemas.order import OrderList, OrderDetail, OrderUpdate
from app.schemas.spell import SpellGenerateRequest, SpellGenerateResponse

router = APIRouter()


@router.get("", response_model=OrderList)
async def list_orders(
    status: Optional[OrderStatus] = None,
    spell_type_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> OrderList:
    """List orders with optional filters and pagination."""
    query = select(Order)

    # Apply filters
    if status:
        query = query.where(Order.status == status)
    if spell_type_id:
        query = query.where(Order.spell_type_id == spell_type_id)
    if date_from:
        query = query.where(Order.created_at >= date_from)
    if date_to:
        query = query.where(Order.created_at <= date_to)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Apply pagination
    query = query.order_by(Order.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    orders = result.scalars().all()

    return OrderList(
        items=orders,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page,
    )


@router.get("/{order_id}", response_model=OrderDetail)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> OrderDetail:
    """Get order detail with current spell."""
    from app.models.spell import Spell
    from app.schemas.spell import SpellDetail

    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Get current spell
    spell_result = await db.execute(
        select(Spell).where(Spell.order_id == order_id, Spell.is_current == True)
    )
    current_spell = spell_result.scalar_one_or_none()

    # Build response manually to avoid lazy loading issues
    spell_detail = None
    if current_spell:
        spell_detail = SpellDetail(
            id=current_spell.id,
            order_id=current_spell.order_id,
            version=current_spell.version,
            is_current=current_spell.is_current,
            is_approved=current_spell.is_approved,
            created_at=current_spell.created_at,
            content=current_spell.content,
            content_html=current_spell.content_html,
            prompt_used=current_spell.prompt_used,
            model_used=current_spell.model_used,
            approved_at=current_spell.approved_at,
            delivered_at=current_spell.delivered_at,
            delivery_method=current_spell.delivery_method,
        )

    return OrderDetail(
        id=order.id,
        etsy_receipt_id=order.etsy_receipt_id,
        customer_name=order.customer_name,
        raw_spell_type=order.raw_spell_type,
        status=order.status,
        created_at=order.created_at,
        updated_at=order.updated_at,
        customer_email=order.customer_email,
        etsy_listing_id=order.etsy_listing_id,
        etsy_transaction_id=order.etsy_transaction_id,
        spell_type_id=order.spell_type_id,
        intention=order.intention,
        personalization_data=order.personalization_data,
        etsy_order_date=order.etsy_order_date,
        order_total_cents=order.order_total_cents,
        currency_code=order.currency_code,
        current_spell=spell_detail,
    )


@router.patch("/{order_id}", response_model=OrderDetail)
async def update_order(
    order_id: int,
    order_update: OrderUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> OrderDetail:
    """Update order details (e.g., intention)."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    update_data = order_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order, field, value)

    await db.commit()
    await db.refresh(order)

    return OrderDetail.model_validate(order, from_attributes=True)


@router.post("/{order_id}/spells/generate", response_model=SpellGenerateResponse)
async def generate_spell_for_order(
    order_id: int,
    request: SpellGenerateRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> SpellGenerateResponse:
    """Generate a spell for an order using Claude AI.

    Creates a new spell version for the specified order.
    If the order already has spells, the new one becomes the current version.
    """
    from app.services.claude import generate_spell_for_order, SpellGenerationError

    try:
        spell = await generate_spell_for_order(db, order_id, request.custom_prompt)
        return SpellGenerateResponse(
            id=spell.id,
            order_id=spell.order_id,
            version=spell.version,
            content=spell.content,
            prompt_used=spell.prompt_used,
            model_used=spell.model_used,
            is_current=spell.is_current,
            created_at=spell.created_at,
            message=f"Spell generated successfully (version {spell.version})",
        )
    except SpellGenerationError as e:
        if "not found" in e.message.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=e.message,
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message,
        )


@router.post("/sync")
async def sync_orders(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> dict:
    """Manually trigger Etsy order sync."""
    from app.services.etsy import sync_new_orders, rate_limiter, EtsyAPIError

    try:
        new_orders = await sync_new_orders(db)
        return {
            "message": "Order sync completed",
            "new_orders": len(new_orders),
            "daily_api_calls_remaining": rate_limiter.daily_remaining,
        }
    except EtsyAPIError as e:
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=str(e),
        )
