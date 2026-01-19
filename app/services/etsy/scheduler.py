"""APScheduler integration for Etsy order polling."""

from typing import Optional
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings
from app.db.session import async_session_maker
from app.services.etsy.orders import sync_new_orders

logger = logging.getLogger(__name__)
settings = get_settings()

# Global scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None


async def poll_etsy_orders() -> None:
    """Background job to poll Etsy for new orders.

    This function is called periodically by the scheduler to check
    for new orders and sync them to the local database.
    """
    logger.info("Running Etsy order poll job")

    async with async_session_maker() as db:
        try:
            new_orders = await sync_new_orders(db)
            if new_orders:
                logger.info(f"Poll job synced {len(new_orders)} new orders")
            else:
                logger.debug("Poll job found no new orders")
        except Exception as e:
            logger.error(f"Etsy poll job failed: {e}", exc_info=True)


def get_scheduler() -> AsyncIOScheduler:
    """Get or create the scheduler instance.

    Returns:
        AsyncIOScheduler instance
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


def start_scheduler() -> None:
    """Start the background scheduler with Etsy polling job.

    The scheduler will poll Etsy for new orders at the interval
    configured in ETSY_POLL_INTERVAL_MINUTES (default: 5 minutes).
    """
    scheduler = get_scheduler()

    if scheduler.running:
        logger.warning("Scheduler already running")
        return

    # Add Etsy polling job
    scheduler.add_job(
        poll_etsy_orders,
        trigger=IntervalTrigger(minutes=settings.ETSY_POLL_INTERVAL_MINUTES),
        id="etsy_order_poll",
        name="Poll Etsy for new orders",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        f"Started Etsy polling scheduler (interval: {settings.ETSY_POLL_INTERVAL_MINUTES} min)"
    )


def stop_scheduler() -> None:
    """Stop the background scheduler gracefully."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Stopped Etsy polling scheduler")
    _scheduler = None


def is_scheduler_running() -> bool:
    """Check if the scheduler is currently running.

    Returns:
        True if scheduler is running, False otherwise
    """
    return _scheduler is not None and _scheduler.running
