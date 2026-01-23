#!/usr/bin/env python3
"""Seed script to create default spell types in the database."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.db.session import async_session_maker
from app.models.spell_type import SpellType


DEFAULT_SPELL_TYPES = [
    {
        "name": "Love Spell",
        "slug": "love",
        "description": "A heartfelt enchantment designed to attract romantic love, strengthen existing relationships, or heal emotional wounds. This spell channels positive energy to open the heart chakra and invite genuine connections.",
        "display_order": 1,
    },
    {
        "name": "Prosperity Spell",
        "slug": "prosperity",
        "description": "A powerful manifestation ritual focused on attracting abundance, financial success, and material wealth. This spell aligns your energy with the flow of prosperity and removes blocks to receiving.",
        "display_order": 2,
    },
    {
        "name": "Protection Spell",
        "slug": "protection",
        "description": "A sacred shield of spiritual defense that guards against negative energies, psychic attacks, and harmful intentions. This spell creates a protective barrier around you and your loved ones.",
        "display_order": 3,
    },
    {
        "name": "Healing Spell",
        "slug": "healing",
        "description": "A restorative enchantment that promotes physical, emotional, and spiritual wellness. This spell channels healing light to restore balance, ease pain, and support the body's natural recovery processes.",
        "display_order": 4,
    },
]

DEFAULT_PROMPT_TEMPLATE = """Create a personalized {{ spell_type }} spell for {{ customer_name }}.

**Customer's Intention:**
{{ intention }}

{% if personalization %}
**Additional Details:**
{% for key, value in personalization.items() %}
- {{ key }}: {{ value }}
{% endfor %}
{% endif %}

Create a meaningful, personalized spell that:
1. Opens with a warm greeting using their name
2. Incorporates their specific intention
3. Uses appropriate magical language and imagery
4. Provides clear instructions for the ritual
5. Includes any necessary materials or timing recommendations
6. Closes with words of encouragement

Write the spell in a warm, mystical tone that feels authentic and personal.
Approximately 300-500 words."""


async def seed_spell_types():
    """Create default spell types if they don't exist."""
    async with async_session_maker() as db:
        created_count = 0
        skipped_count = 0

        for spell_data in DEFAULT_SPELL_TYPES:
            # Check if already exists by slug
            result = await db.execute(
                select(SpellType).where(SpellType.slug == spell_data["slug"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"  Skipped: {spell_data['name']} (already exists)")
                skipped_count += 1
                continue

            # Create the spell type
            spell_type = SpellType(
                name=spell_data["name"],
                slug=spell_data["slug"],
                description=spell_data["description"],
                prompt_template=DEFAULT_PROMPT_TEMPLATE,
                is_active=True,
                display_order=spell_data["display_order"],
            )

            db.add(spell_type)
            print(f"  Created: {spell_data['name']}")
            created_count += 1

        await db.commit()

        print(f"\nSummary: {created_count} created, {skipped_count} skipped")


if __name__ == "__main__":
    print("Seeding default spell types...")
    asyncio.run(seed_spell_types())
    print("Done!")
