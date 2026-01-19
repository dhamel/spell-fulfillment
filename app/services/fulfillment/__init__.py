"""Fulfillment services."""

from app.services.fulfillment.email import (
    send_spell_email,
    EmailDeliveryError,
    EmailResult,
)

__all__ = ["send_spell_email", "EmailDeliveryError", "EmailResult"]
