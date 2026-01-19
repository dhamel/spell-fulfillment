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
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> DashboardMetrics:
    """Get overview dashboard metrics."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    # Order counts by status
    pending_count = (
        await db.execute(
            select(func.count()).where(Order.status == OrderStatus.PENDING)
        )
    ).scalar() or 0

    review_count = (
        await db.execute(
            select(func.count()).where(Order.status == OrderStatus.REVIEW)
        )
    ).scalar() or 0

    delivered_today = (
        await db.execute(
            select(func.count()).where(
                Order.status == OrderStatus.DELIVERED,
                Order.updated_at >= today_start,
            )
        )
    ).scalar() or 0

    delivered_week = (
        await db.execute(
            select(func.count()).where(
                Order.status == OrderStatus.DELIVERED,
                Order.updated_at >= week_start,
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
            "etsy_connected": False,  # TODO: Check actual connection status
            "etsy_requests_today": 0,
            "etsy_rate_limit_remaining": 10000,
        },
    )


@router.get("/orders", response_model=OrderMetrics)
async def get_order_metrics(
    period: str = Query("week", regex="^(day|week|month|year)$"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> OrderMetrics:
    """Get order metrics by period."""
    now = datetime.now(timezone.utc)

    if period == "day":
        start_date = now - timedelta(days=1)
    elif period == "week":
        start_date = now - timedelta(weeks=1)
    elif period == "month":
        start_date = now - timedelta(days=30)
    else:  # year
        start_date = now - timedelta(days=365)

    # Orders by status in period
    result = await db.execute(
        select(Order.status, func.count())
        .where(Order.created_at >= start_date)
        .group_by(Order.status)
    )
    by_status = {str(row[0].value): row[1] for row in result.all()}

    # Orders by spell type in period
    result = await db.execute(
        select(Order.spell_type_id, func.count())
        .where(Order.created_at >= start_date)
        .group_by(Order.spell_type_id)
    )
    by_spell_type = {str(row[0]): row[1] for row in result.all() if row[0]}

    # Total in period
    total = (
        await db.execute(
            select(func.count()).where(Order.created_at >= start_date)
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
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> SatisfactionMetrics:
    """Get satisfaction rating breakdown."""
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
    stats_row = stats_result.one()

    return SatisfactionMetrics(
        average=round(float(stats_row[0]), 2) if stats_row[0] else 0.0,
        total=stats_row[1] or 0,
        distribution=distribution,
    )
