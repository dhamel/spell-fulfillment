"""Service for creating test orders (development only)."""

import random
import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderStatus
from app.models.spell_type import SpellType


# Test data pools for realistic order generation
SAMPLE_NAMES = [
    "Emma Thompson",
    "James Wilson",
    "Sofia Martinez",
    "Michael Chen",
    "Olivia Johnson",
    "William Brown",
    "Ava Garcia",
    "Benjamin Lee",
    "Isabella Davis",
    "Ethan Miller",
    "Mia Anderson",
    "Alexander Taylor",
]

SAMPLE_INTENTIONS = {
    "love": [
        "I want to attract my soulmate into my life",
        "Help me strengthen the bond with my partner",
        "I wish to find true love that lasts forever",
        "Bring romantic harmony into my relationship",
        "Open my heart to receive love",
    ],
    "prosperity": [
        "I want to attract financial abundance",
        "Help my business grow and thrive",
        "I wish to manifest new income opportunities",
        "Bring prosperity and success to my career",
        "Remove blocks to my financial success",
    ],
    "protection": [
        "Protect my family from negative energy",
        "Shield me from toxic people at work",
        "I need protection during a difficult time",
        "Guard my home and create a safe space",
        "Protect me during my spiritual journey",
    ],
    "healing": [
        "Help me heal from past emotional wounds",
        "I want to recover my energy and vitality",
        "Bring healing light to my body and mind",
        "Help me find peace after a loss",
        "Support my journey to wellness",
    ],
}


def generate_fake_etsy_receipt_id() -> int:
    """Generate a unique fake Etsy receipt ID.

    Uses timestamp + random suffix, prefixed with 99 to identify test orders.
    """
    timestamp_part = int(time.time() * 1000) % 1000000000
    random_part = random.randint(1000, 9999)
    return int(f"99{timestamp_part}{random_part}")


async def get_spell_type_by_slug(db: AsyncSession, slug: str) -> Optional[SpellType]:
    """Get spell type by slug."""
    result = await db.execute(
        select(SpellType).where(SpellType.slug == slug, SpellType.is_active == True)
    )
    return result.scalar_one_or_none()


async def create_test_order(
    db: AsyncSession,
    customer_name: str,
    customer_email: str,
    spell_type: str,
    intention: str,
    personalization_data: Optional[dict] = None,
    order_total_cents: int = 2999,
    currency_code: str = "USD",
) -> Order:
    """Create a single test order.

    Args:
        db: Database session
        customer_name: Customer's name
        customer_email: Customer's email
        spell_type: Type of spell (love, prosperity, protection, healing)
        intention: Customer's intention/wish
        personalization_data: Additional personalization fields
        order_total_cents: Order total in cents
        currency_code: Currency code

    Returns:
        Created Order object
    """
    # Get spell_type_id if exists
    spell_type_obj = await get_spell_type_by_slug(db, spell_type)
    spell_type_id = spell_type_obj.id if spell_type_obj else None

    # Build raw_spell_type name like Etsy would
    raw_spell_type = f"{spell_type.title()} Spell - Personalized"

    # Build personalization data
    final_personalization = {"source": "test_order"}
    if personalization_data:
        final_personalization.update(personalization_data)

    order = Order(
        etsy_receipt_id=generate_fake_etsy_receipt_id(),
        etsy_listing_id=random.randint(1000000000, 9999999999),
        etsy_transaction_id=random.randint(1000000000, 9999999999),
        customer_name=customer_name,
        customer_email=customer_email,
        spell_type_id=spell_type_id,
        raw_spell_type=raw_spell_type,
        intention=intention,
        personalization_data=final_personalization,
        etsy_order_date=datetime.now(timezone.utc),
        order_total_cents=order_total_cents,
        currency_code=currency_code,
        status=OrderStatus.PENDING,
    )

    db.add(order)
    await db.commit()
    await db.refresh(order)

    return order


async def create_random_test_order(
    db: AsyncSession,
    spell_type: Optional[str] = None,
) -> Order:
    """Create a test order with randomized realistic data.

    Args:
        db: Database session
        spell_type: Optional spell type override; if None, picks randomly

    Returns:
        Created Order object
    """
    if spell_type is None:
        spell_type = random.choice(list(SAMPLE_INTENTIONS.keys()))

    customer_name = random.choice(SAMPLE_NAMES)
    email_name = customer_name.lower().replace(" ", ".")
    customer_email = f"{email_name}@example.com"
    intention = random.choice(SAMPLE_INTENTIONS[spell_type])

    return await create_test_order(
        db=db,
        customer_name=customer_name,
        customer_email=customer_email,
        spell_type=spell_type,
        intention=intention,
        order_total_cents=random.choice([1999, 2499, 2999, 3499, 3999]),
    )


async def create_bulk_test_orders(
    db: AsyncSession,
    count: int = 5,
    spell_types: Optional[list[str]] = None,
) -> list[Order]:
    """Create multiple test orders.

    Args:
        db: Database session
        count: Number of orders to create
        spell_types: Optional list to cycle through; if None, picks randomly

    Returns:
        List of created Order objects
    """
    orders = []
    for i in range(count):
        if spell_types:
            spell_type = spell_types[i % len(spell_types)]
        else:
            spell_type = None

        order = await create_random_test_order(db, spell_type)
        orders.append(order)

    return orders
