"""Etsy OAuth 2.0 PKCE flow implementation."""

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode
import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.etsy_token import EtsyToken

logger = logging.getLogger(__name__)
settings = get_settings()

# Etsy OAuth endpoints
ETSY_AUTH_URL = "https://www.etsy.com/oauth/connect"
ETSY_TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"


class EtsyOAuthError(Exception):
    """Custom exception for Etsy OAuth errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class EtsyOAuthService:
    """Handle Etsy OAuth 2.0 PKCE flow."""

    def __init__(self) -> None:
        # Store pending OAuth states (in production, use Redis)
        self._pending_states: dict[str, dict] = {}

    def generate_pkce_pair(self) -> tuple[str, str]:
        """Generate PKCE code_verifier and code_challenge.

        Returns:
            Tuple of (code_verifier, code_challenge)
        """
        # code_verifier: 43-128 chars, URL-safe
        code_verifier = secrets.token_urlsafe(64)

        # code_challenge: SHA256 hash of verifier, base64url encoded (no padding)
        digest = hashlib.sha256(code_verifier.encode()).digest()
        code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

        return code_verifier, code_challenge

    def get_authorization_url(self) -> tuple[str, str]:
        """Generate Etsy OAuth authorization URL.

        Returns:
            Tuple of (authorization_url, state)
        """
        state = secrets.token_urlsafe(32)
        code_verifier, code_challenge = self.generate_pkce_pair()

        # Store for callback verification (expires after 10 minutes)
        self._pending_states[state] = {
            "code_verifier": code_verifier,
            "created_at": datetime.now(timezone.utc),
        }

        # Clean up old pending states
        self._cleanup_expired_states()

        params = {
            "response_type": "code",
            "client_id": settings.ETSY_API_KEY,
            "redirect_uri": settings.ETSY_REDIRECT_URI,
            "scope": settings.ETSY_SCOPES,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        url = f"{ETSY_AUTH_URL}?{urlencode(params)}"
        logger.info(f"Generated OAuth authorization URL with state: {state[:8]}...")
        return url, state

    def _cleanup_expired_states(self) -> None:
        """Remove pending states older than 10 minutes."""
        now = datetime.now(timezone.utc)
        expired = [
            state
            for state, data in self._pending_states.items()
            if now - data["created_at"] > timedelta(minutes=10)
        ]
        for state in expired:
            del self._pending_states[state]

    async def exchange_code_for_token(
        self,
        code: str,
        state: str,
        db: AsyncSession,
    ) -> EtsyToken:
        """Exchange authorization code for access token.

        Args:
            code: Authorization code from Etsy callback
            state: State parameter for CSRF verification
            db: Database session

        Returns:
            EtsyToken model with stored tokens

        Raises:
            EtsyOAuthError: If state is invalid or token exchange fails
        """
        if state not in self._pending_states:
            raise EtsyOAuthError("Invalid or expired state parameter")

        state_data = self._pending_states.pop(state)
        code_verifier = state_data["code_verifier"]

        logger.info("Exchanging authorization code for access token")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                ETSY_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "client_id": settings.ETSY_API_KEY,
                    "redirect_uri": settings.ETSY_REDIRECT_URI,
                    "code": code,
                    "code_verifier": code_verifier,
                },
            )

            if not response.is_success:
                error_msg = f"Token exchange failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise EtsyOAuthError(error_msg, response.status_code)

            token_data = response.json()

        # Calculate expiration
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=token_data["expires_in"]
        )

        # Delete any existing tokens (single user system)
        existing = await db.execute(select(EtsyToken))
        for token in existing.scalars():
            await db.delete(token)

        # Store new token in database
        etsy_token = EtsyToken(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_type=token_data.get("token_type", "Bearer"),
            expires_at=expires_at,
            scope=settings.ETSY_SCOPES,
        )

        db.add(etsy_token)
        await db.commit()
        await db.refresh(etsy_token)

        logger.info("Successfully stored Etsy access token")
        return etsy_token

    async def refresh_token(
        self,
        etsy_token: EtsyToken,
        db: AsyncSession,
    ) -> EtsyToken:
        """Refresh an expired access token.

        Args:
            etsy_token: Existing EtsyToken to refresh
            db: Database session

        Returns:
            Updated EtsyToken with new access token

        Raises:
            EtsyOAuthError: If token refresh fails
        """
        logger.info("Refreshing Etsy access token")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                ETSY_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "client_id": settings.ETSY_API_KEY,
                    "refresh_token": etsy_token.refresh_token,
                },
            )

            if not response.is_success:
                error_msg = f"Token refresh failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise EtsyOAuthError(error_msg, response.status_code)

            token_data = response.json()

        # Update token
        etsy_token.access_token = token_data["access_token"]
        etsy_token.refresh_token = token_data["refresh_token"]
        etsy_token.expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=token_data["expires_in"]
        )

        await db.commit()
        await db.refresh(etsy_token)

        logger.info("Successfully refreshed Etsy access token")
        return etsy_token

    async def get_valid_token(self, db: AsyncSession) -> Optional[EtsyToken]:
        """Get a valid (non-expired) token, refreshing if needed.

        Args:
            db: Database session

        Returns:
            Valid EtsyToken or None if no token exists
        """
        result = await db.execute(
            select(EtsyToken).order_by(EtsyToken.created_at.desc()).limit(1)
        )
        token = result.scalar_one_or_none()

        if not token:
            return None

        # Refresh if expired or about to expire (5 min buffer)
        buffer_time = timedelta(minutes=5)
        if token.is_expired or (
            token.expires_at - datetime.now(timezone.utc) < buffer_time
        ):
            try:
                token = await self.refresh_token(token, db)
            except EtsyOAuthError as e:
                logger.error(f"Failed to refresh token: {e}")
                return None

        return token

    async def revoke_token(self, db: AsyncSession) -> bool:
        """Revoke/delete the stored Etsy token.

        Args:
            db: Database session

        Returns:
            True if token was deleted, False if no token existed
        """
        result = await db.execute(select(EtsyToken))
        tokens = result.scalars().all()

        if not tokens:
            return False

        for token in tokens:
            await db.delete(token)

        await db.commit()
        logger.info("Revoked Etsy token")
        return True


# Singleton instance
oauth_service = EtsyOAuthService()
