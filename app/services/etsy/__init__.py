"""Etsy integration services.

This package provides:
- OAuth 2.0 PKCE authentication flow
- Rate-limited API client
- Order synchronization
- Background polling scheduler
"""

from app.services.etsy.oauth import (
    oauth_service,
    EtsyOAuthService,
    EtsyOAuthError,
)
from app.services.etsy.client import (
    EtsyClient,
    EtsyAPIError,
)
from app.services.etsy.rate_limiter import (
    rate_limiter,
    EtsyRateLimiter,
)
from app.services.etsy.orders import (
    OrderSyncService,
    sync_new_orders,
)
from app.services.etsy.scheduler import (
    start_scheduler,
    stop_scheduler,
    get_scheduler,
    is_scheduler_running,
)

__all__ = [
    # OAuth
    "oauth_service",
    "EtsyOAuthService",
    "EtsyOAuthError",
    # Client
    "EtsyClient",
    "EtsyAPIError",
    # Rate limiter
    "rate_limiter",
    "EtsyRateLimiter",
    # Orders
    "OrderSyncService",
    "sync_new_orders",
    # Scheduler
    "start_scheduler",
    "stop_scheduler",
    "get_scheduler",
    "is_scheduler_running",
]
