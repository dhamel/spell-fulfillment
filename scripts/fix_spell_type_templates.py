#!/usr/bin/env python3
"""Fix spell type prompt templates to use Jinja2 syntax.

Run this script to update any spell types that use Python-style {variable}
placeholders to use Jinja2 {{ variable }} syntax instead.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.db.session import async_session_maker
from app.models.spell_type import SpellType

# The correct Jinja2 template
CORRECT_TEMPLATE = """Create a personalized {{ spell_type }} spell for {{ customer_name }}.

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


async def fix_templates():
    """Fix spell type templates that use wrong placeholder syntax."""
    async with async_session_maker() as db:
        result = await db.execute(select(SpellType))
        spell_types = result.scalars().all()

        fixed_count = 0
        for st in spell_types:
            # Check if template uses Python-style placeholders
            if st.prompt_template and '{spell_type}' in st.prompt_template:
                print(f"  Fixing: {st.name} (id={st.id})")
                st.prompt_template = CORRECT_TEMPLATE
                fixed_count += 1
            else:
                print(f"  OK: {st.name} (id={st.id})")

        if fixed_count > 0:
            await db.commit()
            print(f"\nFixed {fixed_count} spell type(s)")
        else:
            print("\nNo spell types needed fixing")


if __name__ == "__main__":
    print("Checking spell type prompt templates...")
    asyncio.run(fix_templates())
    print("Done!")
