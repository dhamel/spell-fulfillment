"""Rate limiter for Etsy API (10/sec, 10k/day)."""

import asyncio
from datetime import datetime, timezone
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class EtsyRateLimiter:
    """Rate limiter for Etsy API requests.

    Enforces:
    - 10 requests per second (via semaphore)
    - 10,000 requests per day (via counter with UTC midnight reset)
    """

    MAX_PER_SECOND = 10
    MAX_PER_DAY = 10_000

    def __init__(self) -> None:
        self._semaphore = asyncio.Semaphore(self.MAX_PER_SECOND)
        self._daily_count = 0
        self._daily_reset: Optional[datetime] = None
        self._lock = asyncio.Lock()

    def _check_daily_reset(self) -> None:
        """Reset daily counter if it's a new day (UTC)."""
        now = datetime.now(timezone.utc)
        if self._daily_reset is None or now.date() > self._daily_reset.date():
            self._daily_count = 0
            self._daily_reset = now

    async def acquire(self) -> bool:
        """Acquire rate limit slot.

        Returns:
            True if slot acquired, False if daily limit exceeded.
        """
        async with self._lock:
            self._check_daily_reset()

            if self._daily_count >= self.MAX_PER_DAY:
                logger.warning("Etsy daily rate limit reached")
                return False

            self._daily_count += 1

        # Per-second limiting via semaphore
        await self._semaphore.acquire()

        # Release semaphore after 1 second to maintain rate
        asyncio.create_task(self._release_after_delay())

        return True

    async def _release_after_delay(self) -> None:
        """Release semaphore slot after 1 second."""
        await asyncio.sleep(1.0)
        self._semaphore.release()

    @property
    def daily_remaining(self) -> int:
        """Get remaining daily API calls."""
        self._check_daily_reset()
        return max(0, self.MAX_PER_DAY - self._daily_count)


# Singleton instance
rate_limiter = EtsyRateLimiter()
