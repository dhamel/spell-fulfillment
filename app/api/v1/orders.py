"""Order management endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.order import Order, OrderStatus
from app.models.spell_type import SpellType
from app.schemas.order import OrderList, OrderDetail, OrderUpdate, ManualOrderCreate, ManualOrderResponse
from app.schemas.spell import SpellGenerateRequest, SpellGenerateResponse

router = APIRouter()


@router.get("", response_model=OrderList)
async def list_orders(
    status: Optional[OrderStatus] = None,
    spell_type_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    include_test_orders: bool = Query(False, description="Include test orders in results"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> OrderList:
    """List orders with optional filters and pagination.

    By default, test orders are excluded. Set include_test_orders=true to include them.
    """
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

    # Filter out test orders unless explicitly requested
    if not include_test_orders:
        query = query.where(Order.is_test_order == False)

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
        cast_type=order.cast_type,
        created_at=order.created_at,
        updated_at=order.updated_at,
        is_test_order=order.is_test_order,
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


@router.post("/manual", response_model=ManualOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_manual_order(
    order_data: ManualOrderCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> ManualOrderResponse:
    """Create a manual production order.

    Use this endpoint to manually enter real Etsy orders before the Etsy API
    integration is fully set up. These orders are treated as real production
    orders and included in all metrics.

    A unique receipt ID is generated using the prefix 88 (to distinguish from
    test orders which use 99 and real Etsy orders which use their actual IDs).
    """
    import random
    import time

    # Validate spell type exists in database
    result = await db.execute(
        select(SpellType).where(
            SpellType.slug == order_data.spell_type.lower(),
            SpellType.is_active == True
        )
    )
    spell_type_obj = result.scalar_one_or_none()

    if not spell_type_obj:
        # Try matching by name as fallback
        result = await db.execute(
            select(SpellType).where(
                func.lower(SpellType.name) == order_data.spell_type.lower(),
                SpellType.is_active == True
            )
        )
        spell_type_obj = result.scalar_one_or_none()

    if not spell_type_obj:
        # Get available types for error message
        result = await db.execute(
            select(SpellType.name, SpellType.slug).where(SpellType.is_active == True)
        )
        available = [f"{name} ({slug})" for name, slug in result.all()]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid spell_type '{order_data.spell_type}'. Available types: {', '.join(available)}",
        )

    # Generate unique receipt ID with prefix 88 (manual orders)
    timestamp_part = int(time.time() * 1000) % 1000000000
    random_part = random.randint(1000, 9999)
    receipt_id = int(f"88{timestamp_part}{random_part}")

    # Build raw_spell_type name
    raw_spell_type = f"{spell_type_obj.name} Spell - Personalized"

    # Build personalization data with source marker
    final_personalization = {"source": "manual_order"}
    if order_data.personalization_data:
        final_personalization.update(order_data.personalization_data)

    order = Order(
        etsy_receipt_id=receipt_id,
        customer_name=order_data.customer_name,
        customer_email=order_data.customer_email,
        spell_type_id=spell_type_obj.id,
        raw_spell_type=raw_spell_type,
        intention=order_data.intention,
        personalization_data=final_personalization,
        etsy_order_date=order_data.etsy_order_date,
        order_total_cents=order_data.order_total_cents,
        currency_code=order_data.currency_code,
        status=OrderStatus.PENDING,
        is_test_order=False,  # This is a real production order
        cast_type=order_data.cast_type,
    )

    db.add(order)
    await db.commit()
    await db.refresh(order)

    return ManualOrderResponse(
        id=order.id,
        etsy_receipt_id=order.etsy_receipt_id,
        customer_name=order.customer_name,
        customer_email=order.customer_email,
        raw_spell_type=order.raw_spell_type,
        intention=order.intention,
        status=order.status.value,
        order_total_cents=order.order_total_cents,
        etsy_order_date=order.etsy_order_date,
        created_at=order.created_at,
        is_test_order=order.is_test_order,
        cast_type=order.cast_type.value,
        message="Manual order created successfully. Ready for spell generation.",
    )
