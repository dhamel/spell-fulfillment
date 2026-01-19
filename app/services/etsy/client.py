"""Async HTTP client for Etsy API v3."""

from typing import Any, Optional
import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.services.etsy.oauth import oauth_service
from app.services.etsy.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)
settings = get_settings()

ETSY_API_BASE = "https://openapi.etsy.com/v3"


class EtsyAPIError(Exception):
    """Custom exception for Etsy API errors."""

    def __init__(
        self,
        status_code: int,
        message: str,
        response_body: Any = None,
    ):
        self.status_code = status_code
        self.message = message
        self.response_body = response_body
        super().__init__(f"Etsy API Error {status_code}: {message}")


class EtsyClient:
    """Async HTTP client for Etsy API v3.

    Features:
    - Automatic token management (refresh when expired)
    - Rate limiting (10/sec, 10k/day)
    - Error handling with custom exceptions
    """

    def __init__(self, db: AsyncSession):
        """Initialize client with database session.

        Args:
            db: Async database session for token management
        """
        self.db = db

    async def _ensure_token(self) -> str:
        """Get valid access token, refresh if needed.

        Returns:
            Valid access token string

        Raises:
            EtsyAPIError: If no valid token exists
        """
        token = await oauth_service.get_valid_token(self.db)
        if not token:
            raise EtsyAPIError(401, "No valid Etsy token. Please authenticate first.")
        return token.access_token

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json_body: Optional[dict] = None,
    ) -> dict:
        """Make authenticated request to Etsy API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path (e.g., "/application/shops/123")
            params: Query parameters
            json_body: JSON body for POST/PUT requests

        Returns:
            Parsed JSON response

        Raises:
            EtsyAPIError: If rate limit exceeded or API returns error
        """
        # Rate limiting
        if not await rate_limiter.acquire():
            raise EtsyAPIError(429, "Daily rate limit exceeded. Try again tomorrow.")

        access_token = await self._ensure_token()

        headers = {
            "Authorization": f"Bearer {access_token}",
            "x-api-key": settings.ETSY_API_KEY,
            "Content-Type": "application/json",
        }

        url = f"{ETSY_API_BASE}{endpoint}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_body,
            )

            # Handle 401 - token might be invalid, try refresh
            if response.status_code == 401:
                logger.warning("Got 401, attempting token refresh")
                token = await oauth_service.get_valid_token(self.db)
                if token:
                    headers["Authorization"] = f"Bearer {token.access_token}"
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        params=params,
                        json=json_body,
                    )

            if not response.is_success:
                response_body = None
                try:
                    response_body = response.json()
                except Exception:
                    pass

                logger.error(
                    f"Etsy API error: {response.status_code} - {response.text}"
                )
                raise EtsyAPIError(
                    status_code=response.status_code,
                    message=response.text,
                    response_body=response_body,
                )

            return response.json()

    async def get(
        self,
        endpoint: str,
        params: Optional[dict] = None,
    ) -> dict:
        """Make GET request to Etsy API.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            Parsed JSON response
        """
        return await self._make_request("GET", endpoint, params=params)

    async def post(
        self,
        endpoint: str,
        json_body: Optional[dict] = None,
    ) -> dict:
        """Make POST request to Etsy API.

        Args:
            endpoint: API endpoint path
            json_body: JSON body

        Returns:
            Parsed JSON response
        """
        return await self._make_request("POST", endpoint, json_body=json_body)

    # Convenience methods for common operations

    async def get_me(self) -> dict:
        """Get authenticated user info.

        Returns:
            User data including user_id and shops
        """
        return await self.get("/application/users/me")

    async def get_shop(self, shop_id: int) -> dict:
        """Get shop details.

        Args:
            shop_id: Etsy shop ID

        Returns:
            Shop data
        """
        return await self.get(f"/application/shops/{shop_id}")

    async def get_shop_receipts(
        self,
        shop_id: int,
        min_created: Optional[int] = None,
        max_created: Optional[int] = None,
        limit: int = 25,
        offset: int = 0,
        was_paid: Optional[bool] = None,
        was_shipped: Optional[bool] = None,
    ) -> dict:
        """Get shop receipts (orders).

        Args:
            shop_id: Etsy shop ID
            min_created: Unix timestamp - minimum created time
            max_created: Unix timestamp - maximum created time
            limit: Number of results per page (max 100)
            offset: Pagination offset
            was_paid: Filter by payment status
            was_shipped: Filter by shipment status

        Returns:
            Response with "count" and "results" list
        """
        params: dict[str, Any] = {
            "limit": min(limit, 100),
            "offset": offset,
        }

        if min_created is not None:
            params["min_created"] = min_created
        if max_created is not None:
            params["max_created"] = max_created
        if was_paid is not None:
            params["was_paid"] = str(was_paid).lower()
        if was_shipped is not None:
            params["was_shipped"] = str(was_shipped).lower()

        return await self.get(
            f"/application/shops/{shop_id}/receipts",
            params=params,
        )

    async def get_receipt(self, shop_id: int, receipt_id: int) -> dict:
        """Get a specific receipt.

        Args:
            shop_id: Etsy shop ID
            receipt_id: Receipt ID

        Returns:
            Receipt data
        """
        return await self.get(
            f"/application/shops/{shop_id}/receipts/{receipt_id}"
        )

    async def get_listing(self, listing_id: int) -> dict:
        """Get listing details.

        Args:
            listing_id: Etsy listing ID

        Returns:
            Listing data
        """
        return await self.get(f"/application/listings/{listing_id}")
