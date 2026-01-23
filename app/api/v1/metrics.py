"""Metrics and dashboard endpoints."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.order import Order, OrderStatus
from app.models.spell import Spell
from app.models.task import Task, TaskStatus
from app.models.satisfaction import Satisfaction
from app.schemas.metrics import DashboardMetrics, OrderMetrics, SatisfactionMetrics

router = APIRouter()


@router.get("/dashboard", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    include_test_orders: bool = Query(False, description="Include test orders in metrics"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> DashboardMetrics:
    """Get overview dashboard metrics.

    By default, test orders are excluded from metrics.
    Set include_test_orders=true to include them.
    """
    from app.services.etsy import oauth_service, rate_limiter

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    # Build base filter for test orders
    test_filter = [] if include_test_orders else [Order.is_test_order == False]

    # Order counts by status
    pending_count = (
        await db.execute(
            select(func.count()).where(
                Order.status == OrderStatus.PENDING,
                *test_filter
            )
        )
    ).scalar() or 0

    review_count = (
        await db.execute(
            select(func.count()).where(
                Order.status == OrderStatus.REVIEW,
                *test_filter
            )
        )
    ).scalar() or 0

    delivered_today = (
        await db.execute(
            select(func.count()).where(
                Order.status == OrderStatus.DELIVERED,
                Order.updated_at >= today_start,
                *test_filter
            )
        )
    ).scalar() or 0

    delivered_week = (
        await db.execute(
            select(func.count()).where(
                Order.status == OrderStatus.DELIVERED,
                Order.updated_at >= week_start,
                *test_filter
            )
        )
    ).scalar() or 0

    # Task counts
    pending_tasks = (
        await db.execute(
            select(func.count()).where(Task.status == TaskStatus.PENDING)
        )
    ).scalar() or 0

    overdue_tasks = (
        await db.execute(
            select(func.count()).where(
                Task.status == TaskStatus.PENDING,
                Task.due_date < now,
            )
        )
    ).scalar() or 0

    # Satisfaction stats
    satisfaction_result = await db.execute(
        select(
            func.avg(Satisfaction.star_rating),
            func.count(Satisfaction.id),
        )
    )
    satisfaction_row = satisfaction_result.one()
    avg_rating = float(satisfaction_row[0]) if satisfaction_row[0] else 0.0
    total_ratings = satisfaction_row[1] or 0

    # Check Etsy connection status
    etsy_token = await oauth_service.get_valid_token(db)
    etsy_connected = etsy_token is not None

    return DashboardMetrics(
        orders={
            "pending": pending_count,
            "in_review": review_count,
            "delivered_today": delivered_today,
            "delivered_this_week": delivered_week,
        },
        tasks={
            "pending": pending_tasks,
            "overdue": overdue_tasks,
        },
        satisfaction={
            "average_rating": round(avg_rating, 2),
            "total_ratings": total_ratings,
        },
        api_status={
            "etsy_connected": etsy_connected,
            "etsy_requests_today": rate_limiter.daily_count,
            "etsy_rate_limit_remaining": rate_limiter.daily_remaining,
        },
    )


@router.get("/orders", response_model=OrderMetrics)
async def get_order_metrics(
    period: str = Query("week", pattern="^(day|week|month|year)$"),
    include_test_orders: bool = Query(False, description="Include test orders in metrics"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> OrderMetrics:
    """Get order metrics by period.

    By default, test orders are excluded from metrics.
    Set include_test_orders=true to include them.
    """
    now = datetime.now(timezone.utc)

    if period == "day":
        start_date = now - timedelta(days=1)
    elif period == "week":
        start_date = now - timedelta(weeks=1)
    elif period == "month":
        start_date = now - timedelta(days=30)
    else:  # year
        start_date = now - timedelta(days=365)

    # Build base filter for test orders
    test_filter = [] if include_test_orders else [Order.is_test_order == False]

    # Orders by status in period
    result = await db.execute(
        select(Order.status, func.count())
        .where(Order.created_at >= start_date, *test_filter)
        .group_by(Order.status)
    )
    by_status = {str(row[0].value): row[1] for row in result.all()}

    # Orders by spell type in period
    result = await db.execute(
        select(Order.spell_type_id, func.count())
        .where(Order.created_at >= start_date, *test_filter)
        .group_by(Order.spell_type_id)
    )
    by_spell_type = {str(row[0]): row[1] for row in result.all() if row[0]}

    # Total in period
    total = (
        await db.execute(
            select(func.count()).where(Order.created_at >= start_date, *test_filter)
        )
    ).scalar() or 0

    return OrderMetrics(
        period=period,
        total=total,
        by_status=by_status,
        by_spell_type=by_spell_type,
    )


@router.get("/satisfaction", response_model=SatisfactionMetrics)
async def get_satisfaction_metrics(
    include_test_orders: bool = Query(False, description="Include test order satisfactions in metrics"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> SatisfactionMetrics:
    """Get satisfaction rating breakdown.

    By default, test order satisfactions are excluded from metrics.
    Set include_test_orders=true to include them.
    """
    # Build query with join to filter by test order status
    if include_test_orders:
        # Rating distribution
        result = await db.execute(
            select(Satisfaction.star_rating, func.count())
            .group_by(Satisfaction.star_rating)
            .order_by(Satisfaction.star_rating)
        )
        distribution = {str(row[0]): row[1] for row in result.all()}

        # Overall stats
        stats_result = await db.execute(
            select(
                func.avg(Satisfaction.star_rating),
                func.count(Satisfaction.id),
            )
        )
    else:
        # Filter out test orders by joining through Spell -> Order
        # Rating distribution
        result = await db.execute(
            select(Satisfaction.star_rating, func.count())
            .join(Spell, Satisfaction.spell_id == Spell.id)
            .join(Order, Spell.order_id == Order.id)
            .where(Order.is_test_order == False)
            .group_by(Satisfaction.star_rating)
            .order_by(Satisfaction.star_rating)
        )
        distribution = {str(row[0]): row[1] for row in result.all()}

        # Overall stats
        stats_result = await db.execute(
            select(
                func.avg(Satisfaction.star_rating),
                func.count(Satisfaction.id),
            )
            .join(Spell, Satisfaction.spell_id == Spell.id)
            .join(Order, Spell.order_id == Order.id)
            .where(Order.is_test_order == False)
        )

    stats_row = stats_result.one()

    return SatisfactionMetrics(
        average=round(float(stats_row[0]), 2) if stats_row[0] else 0.0,
        total=stats_row[1] or 0,
        distribution=distribution,
    )
