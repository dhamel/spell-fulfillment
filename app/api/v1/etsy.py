"""Etsy integration API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.etsy_token import EtsyToken
from app.services.etsy import (
    oauth_service,
    sync_new_orders,
    rate_limiter,
    EtsyAPIError,
    EtsyOAuthError,
)

router = APIRouter()


# Response schemas


class AuthURLResponse(BaseModel):
    """OAuth authorization URL response."""

    authorization_url: str
    state: str


class TokenStatusResponse(BaseModel):
    """Token/connection status response."""

    authenticated: bool
    shop_id: int | None = None
    user_id: int | None = None
    expires_at: str | None = None
    is_expired: bool = False


class SyncResponse(BaseModel):
    """Order sync response."""

    message: str
    new_orders_count: int
    daily_api_calls_remaining: int


class RateLimitStatusResponse(BaseModel):
    """Rate limit status response."""

    daily_remaining: int
    max_per_day: int
    max_per_second: int


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


# Endpoints


@router.get("/auth/url", response_model=AuthURLResponse)
async def get_auth_url(
    _: str = Depends(get_current_user),
) -> AuthURLResponse:
    """Get Etsy OAuth authorization URL.

    Returns a URL that the user should visit to authorize the app.
    The state parameter should be stored to verify the callback.
    """
    url, state = oauth_service.get_authorization_url()
    return AuthURLResponse(authorization_url=url, state=state)


@router.get("/auth/callback")
async def oauth_callback(
    code: str = Query(..., description="Authorization code from Etsy"),
    state: str = Query(..., description="State parameter for CSRF verification"),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Handle Etsy OAuth callback.

    This endpoint is called by Etsy after user authorizes the app.
    It exchanges the authorization code for access tokens.
    """
    try:
        await oauth_service.exchange_code_for_token(code, state, db)
        # Redirect to settings page with success
        return RedirectResponse(
            url="/settings?etsy_connected=true",
            status_code=status.HTTP_302_FOUND,
        )
    except EtsyOAuthError as e:
        # Redirect to settings page with error
        return RedirectResponse(
            url=f"/settings?etsy_error={e.message}",
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/settings?etsy_error=OAuth+failed:+{str(e)}",
            status_code=status.HTTP_302_FOUND,
        )


@router.get("/auth/status", response_model=TokenStatusResponse)
async def get_token_status(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> TokenStatusResponse:
    """Check Etsy authentication/connection status."""
    result = await db.execute(
        select(EtsyToken).order_by(EtsyToken.created_at.desc()).limit(1)
    )
    token = result.scalar_one_or_none()

    if not token:
        return TokenStatusResponse(authenticated=False)

    return TokenStatusResponse(
        authenticated=True,
        shop_id=token.shop_id,
        user_id=token.user_id,
        expires_at=token.expires_at.isoformat() if token.expires_at else None,
        is_expired=token.is_expired,
    )


@router.post("/auth/refresh", response_model=TokenStatusResponse)
async def refresh_token(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> TokenStatusResponse:
    """Manually refresh the Etsy access token."""
    result = await db.execute(
        select(EtsyToken).order_by(EtsyToken.created_at.desc()).limit(1)
    )
    token = result.scalar_one_or_none()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Etsy token found. Please authenticate first.",
        )

    try:
        refreshed = await oauth_service.refresh_token(token, db)
        return TokenStatusResponse(
            authenticated=True,
            shop_id=refreshed.shop_id,
            user_id=refreshed.user_id,
            expires_at=refreshed.expires_at.isoformat() if refreshed.expires_at else None,
            is_expired=refreshed.is_expired,
        )
    except EtsyOAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {e.message}",
        )


@router.post("/auth/disconnect", response_model=MessageResponse)
async def disconnect_etsy(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> MessageResponse:
    """Disconnect Etsy by revoking the stored token."""
    deleted = await oauth_service.revoke_token(db)

    if deleted:
        return MessageResponse(message="Etsy account disconnected successfully")
    else:
        return MessageResponse(message="No Etsy account was connected")


@router.post("/orders/sync", response_model=SyncResponse)
async def manual_sync_orders(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> SyncResponse:
    """Manually trigger Etsy order sync.

    Fetches new paid orders from Etsy and stores them in the database.
    """
    try:
        new_orders = await sync_new_orders(db)
        return SyncResponse(
            message="Order sync completed successfully",
            new_orders_count=len(new_orders),
            daily_api_calls_remaining=rate_limiter.daily_remaining,
        )
    except EtsyAPIError as e:
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=e.message,
        )


@router.get("/rate-limit", response_model=RateLimitStatusResponse)
async def get_rate_limit_status(
    _: str = Depends(get_current_user),
) -> RateLimitStatusResponse:
    """Get current Etsy API rate limit status."""
    return RateLimitStatusResponse(
        daily_remaining=rate_limiter.daily_remaining,
        max_per_day=rate_limiter.MAX_PER_DAY,
        max_per_second=rate_limiter.MAX_PER_SECOND,
    )
