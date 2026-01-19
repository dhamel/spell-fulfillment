"""Email delivery service using SendGrid."""

from dataclasses import dataclass
from typing import Optional
import httpx

from app.config import get_settings

settings = get_settings()


class EmailDeliveryError(Exception):
    """Exception raised when email delivery fails."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


@dataclass
class EmailResult:
    """Result of an email send operation."""

    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


async def send_spell_email(
    to_email: str,
    customer_name: str,
    spell_content: str,
    spell_type: str,
    subject: Optional[str] = None,
) -> EmailResult:
    """Send a personalized spell email to a customer.

    Args:
        to_email: Customer's email address
        customer_name: Customer's name for personalization
        spell_content: The AI-generated spell content (plain text)
        spell_type: Type of spell for the subject line
        subject: Optional custom subject line

    Returns:
        EmailResult with success status and message ID or error
    """
    if not settings.SENDGRID_API_KEY:
        raise EmailDeliveryError("SendGrid API key not configured")

    # Generate subject line if not provided
    if not subject:
        subject = f"Your Personalized {spell_type.title()} Spell is Ready"

    # Build the email HTML content
    html_content = _build_spell_email_html(customer_name, spell_content, spell_type)
    plain_content = _build_spell_email_plain(customer_name, spell_content)

    # SendGrid API payload
    payload = {
        "personalizations": [
            {
                "to": [{"email": to_email, "name": customer_name}],
                "subject": subject,
            }
        ],
        "from": {
            "email": settings.FROM_EMAIL,
            "name": settings.FROM_NAME,
        },
        "content": [
            {"type": "text/plain", "value": plain_content},
            {"type": "text/html", "value": html_content},
        ],
        "tracking_settings": {
            "click_tracking": {"enable": False},
            "open_tracking": {"enable": True},
        },
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )

            if response.status_code in (200, 201, 202):
                # SendGrid returns message ID in X-Message-Id header
                message_id = response.headers.get("X-Message-Id", "")
                return EmailResult(success=True, message_id=message_id)
            else:
                error_detail = response.text
                return EmailResult(
                    success=False,
                    error=f"SendGrid error ({response.status_code}): {error_detail}",
                )
        except httpx.RequestError as e:
            return EmailResult(success=False, error=f"Network error: {str(e)}")


def _build_spell_email_html(
    customer_name: str, spell_content: str, spell_type: str
) -> str:
    """Build the HTML email content for spell delivery."""
    # Convert newlines to <br> tags for HTML
    spell_html = spell_content.replace("\n", "<br>")

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your Personalized Spell</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f4f4f4; font-family: Georgia, 'Times New Roman', serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f4f4f4;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 40px 40px 30px; text-align: center; border-radius: 8px 8px 0 0;">
                            <h1 style="color: #f0e6d2; margin: 0; font-size: 28px; font-weight: normal; letter-spacing: 2px;">
                                ✨ Your {spell_type.title()} Spell ✨
                            </h1>
                        </td>
                    </tr>

                    <!-- Greeting -->
                    <tr>
                        <td style="padding: 30px 40px 20px;">
                            <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0;">
                                Dear {customer_name},
                            </p>
                            <p style="color: #666; font-size: 16px; line-height: 1.6; margin: 15px 0 0;">
                                Thank you for trusting us with your magical intentions. We have crafted this personalized spell just for you, infused with care and positive energy.
                            </p>
                        </td>
                    </tr>

                    <!-- Spell Content -->
                    <tr>
                        <td style="padding: 20px 40px;">
                            <div style="background: linear-gradient(to bottom, #faf8f5, #f5f0e8); border: 1px solid #e0d5c5; border-radius: 8px; padding: 30px; margin: 0;">
                                <p style="color: #2c2c2c; font-size: 15px; line-height: 1.8; margin: 0; white-space: pre-line;">
                                    {spell_html}
                                </p>
                            </div>
                        </td>
                    </tr>

                    <!-- Closing -->
                    <tr>
                        <td style="padding: 20px 40px 30px;">
                            <p style="color: #666; font-size: 14px; line-height: 1.6; margin: 0;">
                                May this spell bring you the blessings you seek. Remember, the true magic lies within you.
                            </p>
                            <p style="color: #666; font-size: 14px; line-height: 1.6; margin: 15px 0 0;">
                                With mystical blessings,<br>
                                <strong style="color: #333;">{settings.FROM_NAME}</strong>
                            </p>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8f8f8; padding: 20px 40px; text-align: center; border-radius: 0 0 8px 8px; border-top: 1px solid #e0e0e0;">
                            <p style="color: #999; font-size: 12px; margin: 0;">
                                This spell was created especially for you based on your intention.
                            </p>
                            <p style="color: #999; font-size: 12px; margin: 10px 0 0;">
                                © {settings.FROM_NAME}
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""


def _build_spell_email_plain(customer_name: str, spell_content: str) -> str:
    """Build the plain text email content for spell delivery."""
    return f"""Dear {customer_name},

Thank you for trusting us with your magical intentions. We have crafted this personalized spell just for you, infused with care and positive energy.

---

{spell_content}

---

May this spell bring you the blessings you seek. Remember, the true magic lies within you.

With mystical blessings,
{settings.FROM_NAME}

---
This spell was created especially for you based on your intention.
"""
