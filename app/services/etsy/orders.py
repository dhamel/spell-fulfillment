"""Order sync service for Etsy orders."""

from datetime import datetime, timezone
from typing import Optional
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderStatus
from app.models.etsy_token import EtsyToken
from app.services.etsy.client import EtsyClient, EtsyAPIError

logger = logging.getLogger(__name__)


class OrderSyncService:
    """Sync Etsy orders to local database."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session.

        Args:
            db: Async database session
        """
        self.db = db
        self.client = EtsyClient(db)

    async def _get_shop_id(self) -> Optional[int]:
        """Get shop ID from stored token or fetch from API.

        Returns:
            Shop ID or None if unavailable
        """
        result = await self.db.execute(
            select(EtsyToken).order_by(EtsyToken.created_at.desc()).limit(1)
        )
        token = result.scalar_one_or_none()

        if not token:
            logger.warning("No Etsy token found")
            return None

        # If shop_id not stored, fetch and store it
        if not token.shop_id:
            try:
                user_info = await self.client.get_me()
                user_id = user_info.get("user_id")

                # Get shop ID from user info
                # The /users/me endpoint returns shop_id in the response
                shop_id = user_info.get("shop_id")

                if shop_id:
                    token.shop_id = shop_id
                    token.user_id = user_id
                    await self.db.commit()
                    logger.info(f"Stored shop_id: {shop_id}")
                else:
                    logger.warning("User does not have a shop")
                    return None

            except EtsyAPIError as e:
                logger.error(f"Failed to fetch user info: {e}")
                return None

        return token.shop_id

    def _parse_receipt_to_order(self, receipt: dict) -> dict:
        """Parse Etsy receipt data to Order model fields.

        Args:
            receipt: Raw receipt data from Etsy API

        Returns:
            Dict of Order model fields
        """
        # Extract buyer info
        buyer_email = receipt.get("buyer_email")
        buyer_name = receipt.get("name", "")

        # Extract first transaction (listing) info
        transactions = receipt.get("transactions", [])
        listing_id = None
        transaction_id = None
        raw_spell_type = None
        intention = None
        personalization_data: dict = {}

        if transactions:
            first_txn = transactions[0]
            listing_id = first_txn.get("listing_id")
            transaction_id = first_txn.get("transaction_id")
            raw_spell_type = first_txn.get("title", "")

            # Extract personalizations (variations)
            variations = first_txn.get("variations", [])
            for var in variations:
                prop_name = var.get("formatted_name", "")
                prop_value = var.get("formatted_value", "")
                if prop_name and prop_value:
                    personalization_data[prop_name] = prop_value

                    # Try to extract intention from common field names
                    if "intention" in prop_name.lower() or "wish" in prop_name.lower():
                        intention = prop_value

            # Buyer message might contain intention
            buyer_message = receipt.get("message_from_buyer", "")
            if buyer_message:
                personalization_data["buyer_message"] = buyer_message
                if not intention:
                    intention = buyer_message

        # Parse dates
        created_timestamp = receipt.get("create_timestamp")
        order_date = None
        if created_timestamp:
            order_date = datetime.fromtimestamp(created_timestamp, tz=timezone.utc)

        # Parse amounts
        total_price = receipt.get("grandtotal", {})
        order_total_cents = None
        currency = "USD"
        if total_price:
            order_total_cents = total_price.get("amount")
            currency = total_price.get("currency_code", "USD")

        return {
            "etsy_receipt_id": receipt["receipt_id"],
            "etsy_listing_id": listing_id,
            "etsy_transaction_id": transaction_id,
            "customer_name": buyer_name,
            "customer_email": buyer_email,
            "raw_spell_type": raw_spell_type,
            "intention": intention,
            "personalization_data": personalization_data if personalization_data else None,
            "etsy_order_date": order_date,
            "order_total_cents": order_total_cents,
            "currency_code": currency,
            "status": OrderStatus.PENDING,
        }

    async def sync_new_orders(
        self,
        min_created: Optional[int] = None,
    ) -> list[Order]:
        """Fetch and sync new orders from Etsy.

        Args:
            min_created: Unix timestamp - only fetch orders after this time

        Returns:
            List of newly created Order objects
        """
        shop_id = await self._get_shop_id()
        if not shop_id:
            logger.warning("No shop ID available for order sync")
            return []

        new_orders: list[Order] = []
        offset = 0
        limit = 25

        logger.info(f"Starting order sync for shop {shop_id}")

        while True:
            try:
                response = await self.client.get_shop_receipts(
                    shop_id=shop_id,
                    min_created=min_created,
                    limit=limit,
                    offset=offset,
                    was_paid=True,  # Only sync paid orders
                )
            except EtsyAPIError as e:
                logger.error(f"Failed to fetch receipts: {e}")
                break

            receipts = response.get("results", [])
            if not receipts:
                break

            for receipt in receipts:
                receipt_id = receipt["receipt_id"]

                # Check if order already exists
                existing = await self.db.execute(
                    select(Order).where(Order.etsy_receipt_id == receipt_id)
                )
                if existing.scalar_one_or_none():
                    logger.debug(f"Order {receipt_id} already exists, skipping")
                    continue

                # Create new order
                order_data = self._parse_receipt_to_order(receipt)
                order = Order(**order_data)
                self.db.add(order)
                new_orders.append(order)
                logger.info(f"Created new order for receipt {receipt_id}")

            # Check if more pages exist
            total_count = response.get("count", 0)
            offset += limit
            if offset >= total_count:
                break

        if new_orders:
            await self.db.commit()
            logger.info(f"Synced {len(new_orders)} new orders from Etsy")

        return new_orders

    async def sync_order_by_receipt_id(
        self,
        receipt_id: int,
    ) -> Optional[Order]:
        """Sync a specific order by Etsy receipt ID.

        Args:
            receipt_id: Etsy receipt ID to sync

        Returns:
            Order object (new or updated) or None if fetch failed
        """
        shop_id = await self._get_shop_id()
        if not shop_id:
            return None

        try:
            response = await self.client.get_receipt(shop_id, receipt_id)
        except EtsyAPIError as e:
            logger.error(f"Failed to fetch receipt {receipt_id}: {e}")
            return None

        # Check if order exists
        existing = await self.db.execute(
            select(Order).where(Order.etsy_receipt_id == receipt_id)
        )
        order = existing.scalar_one_or_none()

        order_data = self._parse_receipt_to_order(response)

        if order:
            # Update existing order
            for key, value in order_data.items():
                if key not in ("etsy_receipt_id", "status"):
                    setattr(order, key, value)
            logger.info(f"Updated order for receipt {receipt_id}")
        else:
            # Create new order
            order = Order(**order_data)
            self.db.add(order)
            logger.info(f"Created order for receipt {receipt_id}")

        await self.db.commit()
        await self.db.refresh(order)

        return order


async def sync_new_orders(db: AsyncSession) -> list[Order]:
    """Convenience function to sync new orders.

    Args:
        db: Async database session

    Returns:
        List of newly created Order objects
    """
    service = OrderSyncService(db)
    return await service.sync_new_orders()
