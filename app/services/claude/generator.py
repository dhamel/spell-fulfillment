"""Spell generation service using Claude AI."""

from datetime import datetime, timezone
from typing import Optional
import logging

from jinja2 import Template, TemplateError
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.order import CastType, Order, OrderStatus
from app.models.spell import Spell
from app.models.spell_type import SpellType
from app.services.claude.client import get_claude_client, ClaudeAPIError
from app.services.claude.prompts import (
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_CUSTOMER_CAST,
    DEFAULT_PROMPT_TEMPLATE,
    get_template_for_spell_type,
    get_customer_cast_template,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class SpellGenerationError(Exception):
    """Custom exception for spell generation errors."""

    def __init__(self, message: str, order_id: Optional[int] = None):
        self.message = message
        self.order_id = order_id
        super().__init__(message)


class SpellGenerator:
    """Service for generating personalized spells using Claude AI."""

    def __init__(self, db: AsyncSession):
        """Initialize the generator with database session.

        Args:
            db: Async database session
        """
        self.db = db

    def _get_prompt_template(
        self,
        spell_type: Optional[SpellType],
        cast_type: CastType = CastType.CUSTOMER_CAST,
    ) -> str:
        """Get the appropriate prompt template.

        Args:
            spell_type: The SpellType model (may be None)
            cast_type: The cast type (CUSTOMER_CAST or COMBINATION use shorter prompts)

        Returns:
            Prompt template string
        """
        # For CUSTOMER_CAST and COMBINATION, use the shorter templates
        if cast_type in (CastType.CUSTOMER_CAST, CastType.COMBINATION):
            # Use spell_type's custom template if available
            if spell_type and spell_type.prompt_template:
                return spell_type.prompt_template

            # Fall back to customer-cast templates (shorter, more professional)
            if spell_type and spell_type.slug:
                return get_customer_cast_template(spell_type.slug)

            from app.services.claude.prompts import CUSTOMER_CAST_DEFAULT_TEMPLATE
            return CUSTOMER_CAST_DEFAULT_TEMPLATE

        # For original behavior (or future extensions), use original templates
        if spell_type and spell_type.prompt_template:
            return spell_type.prompt_template

        if spell_type and spell_type.slug:
            return get_template_for_spell_type(spell_type.slug)

        return DEFAULT_PROMPT_TEMPLATE

    def _get_system_prompt(self, cast_type: CastType) -> str:
        """Get the appropriate system prompt based on cast type.

        Args:
            cast_type: The cast type

        Returns:
            System prompt string
        """
        # CUSTOMER_CAST and COMBINATION use the shorter, more professional system prompt
        if cast_type in (CastType.CUSTOMER_CAST, CastType.COMBINATION):
            return SYSTEM_PROMPT_CUSTOMER_CAST
        return SYSTEM_PROMPT

    def _render_prompt(
        self,
        template: str,
        order: Order,
        spell_type: Optional[SpellType],
    ) -> str:
        """Render the prompt template with order data.

        Args:
            template: Jinja2 template string
            order: The Order model with customer data
            spell_type: The SpellType model (may be None)

        Returns:
            Rendered prompt string

        Raises:
            SpellGenerationError: If template rendering fails
        """
        # Prepare template variables
        order_date = order.etsy_order_date or order.created_at
        if order_date:
            order_date_str = order_date.strftime("%B %d, %Y")
        else:
            order_date_str = "Unknown"

        variables = {
            "customer_name": order.customer_name or "Valued Customer",
            "intention": order.intention or "their personal journey",
            "spell_type": spell_type.name if spell_type else (order.raw_spell_type or "Custom Spell"),
            "spell_type_slug": spell_type.slug if spell_type else "custom",
            "personalization": order.personalization_data or {},
            "order_date": order_date_str,
            "order_id": order.id,
        }

        try:
            jinja_template = Template(template)
            rendered = jinja_template.render(**variables)
            return rendered.strip()
        except TemplateError as e:
            logger.error(f"Template rendering failed for order {order.id}: {e}")
            raise SpellGenerationError(
                f"Failed to render prompt template: {str(e)}",
                order_id=order.id,
            )

    async def _get_next_version(self, order_id: int) -> int:
        """Get the next version number for an order's spell.

        Args:
            order_id: The order ID

        Returns:
            Next version number (1 if no existing spells)
        """
        result = await self.db.execute(
            select(func.max(Spell.version)).where(Spell.order_id == order_id)
        )
        max_version = result.scalar()
        return (max_version or 0) + 1

    async def generate_spell(
        self,
        order: Order,
        custom_prompt: Optional[str] = None,
    ) -> Spell:
        """Generate a spell for an order.

        For CAST_BY_US orders, creates a placeholder spell record (no AI generation).
        For CUSTOMER_CAST and COMBINATION orders, uses Claude AI with shorter prompts.

        Args:
            order: The Order to generate a spell for
            custom_prompt: Optional custom prompt override

        Returns:
            The created Spell model

        Raises:
            SpellGenerationError: If generation fails
        """
        cast_type = order.cast_type
        logger.info(f"Generating spell for order {order.id} (cast_type={cast_type.value})")

        # Load spell_type if not already loaded
        spell_type = None
        if order.spell_type_id:
            result = await self.db.execute(
                select(SpellType).where(SpellType.id == order.spell_type_id)
            )
            spell_type = result.scalar_one_or_none()

        # Handle CAST_BY_US - no AI generation needed
        if cast_type == CastType.CAST_BY_US:
            return await self._create_cast_by_us_spell(order, spell_type)

        # For CUSTOMER_CAST and COMBINATION, generate AI content
        # Get and render prompt
        if custom_prompt:
            rendered_prompt = custom_prompt
        else:
            template = self._get_prompt_template(spell_type, cast_type)
            rendered_prompt = self._render_prompt(template, order, spell_type)

        # Get the appropriate system prompt
        system_prompt = self._get_system_prompt(cast_type)

        # Update order status to GENERATING
        order.status = OrderStatus.GENERATING
        await self.db.commit()

        try:
            # Call Claude API
            client = get_claude_client()
            content = await client.generate_text(
                prompt=rendered_prompt,
                system_prompt=system_prompt,
            )

            # Get next version number
            version = await self._get_next_version(order.id)

            # Mark any existing spells as not current
            existing_spells = await self.db.execute(
                select(Spell).where(Spell.order_id == order.id, Spell.is_current == True)
            )
            for existing in existing_spells.scalars():
                existing.is_current = False

            # Create new spell record
            spell = Spell(
                order_id=order.id,
                version=version,
                content=content,
                prompt_used=rendered_prompt,
                model_used=settings.CLAUDE_MODEL,
                is_current=True,
                is_approved=False,
            )
            self.db.add(spell)

            # Update order status to REVIEW
            order.status = OrderStatus.REVIEW
            await self.db.commit()
            await self.db.refresh(spell)

            logger.info(
                f"Generated spell v{version} for order {order.id} "
                f"({len(content)} chars)"
            )

            return spell

        except ClaudeAPIError as e:
            # Update order status to FAILED
            order.status = OrderStatus.FAILED
            await self.db.commit()

            logger.error(f"Claude API error for order {order.id}: {e}")
            raise SpellGenerationError(
                f"AI generation failed: {e.message}",
                order_id=order.id,
            )

    async def _create_cast_by_us_spell(
        self,
        order: Order,
        spell_type: Optional[SpellType],
    ) -> Spell:
        """Create a spell record for CAST_BY_US orders.

        No AI generation is needed - the spell content is a marker indicating
        that the cast-by-us email template should be used during delivery.

        Args:
            order: The Order
            spell_type: The SpellType model (may be None)

        Returns:
            The created Spell model
        """
        spell_type_name = spell_type.name if spell_type else (order.raw_spell_type or "Custom Spell")

        # Create placeholder content - actual email uses the template
        content = f"""[CAST BY US]

This {spell_type_name} spell was cast on behalf of {order.customer_name or 'the customer'}.

The customer's intention:
{order.intention or 'Not specified'}

---
Note: This is a "Cast by Us" order. No AI-generated instructions are included.
The delivery email will use the standard cast-by-us template."""

        # Get next version number
        version = await self._get_next_version(order.id)

        # Mark any existing spells as not current
        existing_spells = await self.db.execute(
            select(Spell).where(Spell.order_id == order.id, Spell.is_current == True)
        )
        for existing in existing_spells.scalars():
            existing.is_current = False

        # Create spell record
        spell = Spell(
            order_id=order.id,
            version=version,
            content=content,
            prompt_used="[Cast by us - no AI generation]",
            model_used="none",
            is_current=True,
            is_approved=False,
        )
        self.db.add(spell)

        # Set order status directly to REVIEW (skip GENERATING)
        order.status = OrderStatus.REVIEW
        await self.db.commit()
        await self.db.refresh(spell)

        logger.info(f"Created cast-by-us spell v{version} for order {order.id}")

        return spell

    async def regenerate_spell(
        self,
        spell: Spell,
        custom_prompt: Optional[str] = None,
    ) -> Spell:
        """Regenerate a spell (create new version).

        Args:
            spell: The existing Spell to regenerate
            custom_prompt: Optional custom prompt override

        Returns:
            The new Spell model

        Raises:
            SpellGenerationError: If regeneration fails
        """
        # Load the order
        result = await self.db.execute(
            select(Order)
            .where(Order.id == spell.order_id)
            .options(selectinload(Order.spell_type))
        )
        order = result.scalar_one_or_none()

        if not order:
            raise SpellGenerationError(
                f"Order not found for spell {spell.id}",
                order_id=spell.order_id,
            )

        logger.info(f"Regenerating spell {spell.id} (order {order.id})")

        return await self.generate_spell(order, custom_prompt)


async def generate_spell_for_order(
    db: AsyncSession,
    order_id: int,
    custom_prompt: Optional[str] = None,
) -> Spell:
    """Convenience function to generate a spell for an order.

    Args:
        db: Database session
        order_id: The order ID
        custom_prompt: Optional custom prompt

    Returns:
        The created Spell

    Raises:
        SpellGenerationError: If order not found or generation fails
    """
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.spell_type))
    )
    order = result.scalar_one_or_none()

    if not order:
        raise SpellGenerationError(f"Order {order_id} not found", order_id=order_id)

    generator = SpellGenerator(db)
    return await generator.generate_spell(order, custom_prompt)


async def regenerate_spell(
    db: AsyncSession,
    spell_id: int,
    custom_prompt: Optional[str] = None,
) -> Spell:
    """Convenience function to regenerate a spell.

    Args:
        db: Database session
        spell_id: The spell ID to regenerate
        custom_prompt: Optional custom prompt

    Returns:
        The new Spell version

    Raises:
        SpellGenerationError: If spell not found or regeneration fails
    """
    result = await db.execute(select(Spell).where(Spell.id == spell_id))
    spell = result.scalar_one_or_none()

    if not spell:
        raise SpellGenerationError(f"Spell {spell_id} not found")

    generator = SpellGenerator(db)
    return await generator.regenerate_spell(spell, custom_prompt)
