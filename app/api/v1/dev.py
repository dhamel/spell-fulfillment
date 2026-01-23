"""Development-only endpoints for testing."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.config import get_settings
from app.models.order import Order
from app.models.spell_type import SpellType
from app.schemas.test_order import (
    TestOrderCreate,
    TestOrderBulkCreate,
    TestOrderResponse,
)
from app.services.test_orders import (
    create_test_order,
    create_bulk_test_orders,
)

settings = get_settings()
router = APIRouter()


async def get_valid_spell_types(db: AsyncSession) -> list[str]:
    """Get all valid spell type slugs from the database."""
    result = await db.execute(
        select(SpellType.slug, SpellType.name).where(SpellType.is_active == True)
    )
    rows = result.all()
    # Return both slugs and names (lowercase) as valid identifiers
    valid = []
    for slug, name in rows:
        valid.append(slug.lower())
        valid.append(name.lower())
    return valid


async def validate_spell_type(spell_type: str, db: AsyncSession) -> None:
    """Validate that a spell type exists in the database."""
    valid_types = await get_valid_spell_types(db)
    if spell_type.lower() not in valid_types:
        # Get display list of available types
        result = await db.execute(
            select(SpellType.name, SpellType.slug).where(SpellType.is_active == True)
        )
        available = [f"{name} ({slug})" for name, slug in result.all()]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid spell_type '{spell_type}'. Available types: {', '.join(available)}",
        )


def require_development() -> None:
    """Dependency that blocks access in production."""
    if settings.ENVIRONMENT == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available in development mode",
        )


@router.post("/test-orders", response_model=TestOrderResponse)
async def create_test_order_endpoint(
    order_data: TestOrderCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
    __: None = Depends(require_development),
) -> TestOrderResponse:
    """Create a single test order (development only).

    This endpoint simulates an Etsy order coming in without
    requiring a real Etsy connection.
    """
    # Validate spell type exists in database
    await validate_spell_type(order_data.spell_type, db)

    order = await create_test_order(
        db=db,
        customer_name=order_data.customer_name,
        customer_email=order_data.customer_email,
        spell_type=order_data.spell_type,
        intention=order_data.intention,
        personalization_data=order_data.personalization_data,
        order_total_cents=order_data.order_total_cents,
        currency_code=order_data.currency_code,
        cast_type=order_data.cast_type,
    )

    return TestOrderResponse(
        id=order.id,
        etsy_receipt_id=order.etsy_receipt_id,
        customer_name=order.customer_name,
        customer_email=order.customer_email,
        raw_spell_type=order.raw_spell_type,
        intention=order.intention,
        status=order.status.value,
        cast_type=order.cast_type.value,
        message=f"Test order created successfully with ID {order.id}",
    )


@router.post("/test-orders/bulk", response_model=list[TestOrderResponse])
async def create_bulk_test_orders_endpoint(
    request: TestOrderBulkCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
    __: None = Depends(require_development),
) -> list[TestOrderResponse]:
    """Create multiple test orders with random data (development only).

    Useful for populating the database with sample orders for testing.
    """
    # Validate all provided spell types exist in database
    if request.spell_types:
        for spell_type in request.spell_types:
            await validate_spell_type(spell_type, db)

    orders = await create_bulk_test_orders(
        db=db,
        count=request.count,
        spell_types=request.spell_types,
    )

    return [
        TestOrderResponse(
            id=order.id,
            etsy_receipt_id=order.etsy_receipt_id,
            customer_name=order.customer_name,
            customer_email=order.customer_email,
            raw_spell_type=order.raw_spell_type,
            intention=order.intention,
            status=order.status.value,
            cast_type=order.cast_type.value,
            message=f"Test order {i + 1} of {len(orders)} created",
        )
        for i, order in enumerate(orders)
    ]


@router.delete("/test-orders/{order_id}")
async def delete_test_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
    __: None = Depends(require_development),
) -> dict:
    """Delete a test order by ID (development only).

    Only deletes orders with etsy_receipt_id starting with 99 (test orders).
    """
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Safety check: only delete test orders (those starting with 99)
    if not str(order.etsy_receipt_id).startswith("99"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only delete test orders (etsy_receipt_id starting with 99)",
        )

    await db.delete(order)
    await db.commit()

    return {"message": f"Test order {order_id} deleted successfully"}
