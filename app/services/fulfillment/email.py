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
        "reply_to": {
            "email": settings.FROM_EMAIL,
            "name": settings.FROM_NAME,
        },
        "headers": {
            "List-Unsubscribe": f"<mailto:{settings.FROM_EMAIL}?subject=Unsubscribe>",
            "Precedence": "bulk",
        },
        "content": [
            {"type": "text/plain", "value": plain_content},
            {"type": "text/html", "value": html_content},
        ],
        "tracking_settings": {
            "click_tracking": {"enable": False},
            "open_tracking": {"enable": False},
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
                                Your {spell_type.title()}
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


async def send_cast_by_us_email(
    to_email: str,
    customer_name: str,
    spell_type: str,
    intention: str,
    subject: Optional[str] = None,
) -> EmailResult:
    """Send a cast-by-us confirmation email (no AI-generated content).

    This email confirms the spell was cast on the customer's behalf
    and includes their intention with a slight rephrase.

    Args:
        to_email: Customer's email address
        customer_name: Customer's name for personalization
        spell_type: Type of spell that was cast
        intention: Customer's original intention
        subject: Optional custom subject line

    Returns:
        EmailResult with success status and message ID or error
    """
    if not settings.SENDGRID_API_KEY:
        raise EmailDeliveryError("SendGrid API key not configured")

    if not subject:
        subject = f"Your {spell_type.title()} Has Been Cast"

    # Build the email content
    html_content = _build_cast_by_us_html(customer_name, spell_type, intention)
    plain_content = _build_cast_by_us_plain(customer_name, spell_type, intention)

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
        "reply_to": {
            "email": settings.FROM_EMAIL,
            "name": settings.FROM_NAME,
        },
        "headers": {
            "List-Unsubscribe": f"<mailto:{settings.FROM_EMAIL}?subject=Unsubscribe>",
            "Precedence": "bulk",
        },
        "content": [
            {"type": "text/plain", "value": plain_content},
            {"type": "text/html", "value": html_content},
        ],
        "tracking_settings": {
            "click_tracking": {"enable": False},
            "open_tracking": {"enable": False},
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


def _build_cast_by_us_html(customer_name: str, spell_type: str, intention: str) -> str:
    """Build the HTML email content for cast-by-us confirmation."""
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your Spell Has Been Cast</title>
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
                                Your {spell_type.title()} Has Been Cast
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
                                Your spell has been cast. The forces it has unleashed are now active, and we have taken your expressed desire and formed it into a magical request to the Universal Spirit, seeking what you have asked to be manifested.
                            </p>
                        </td>
                    </tr>

                    <!-- Intention Box -->
                    <tr>
                        <td style="padding: 10px 40px 20px;">
                            <div style="background: linear-gradient(to bottom, #faf8f5, #f5f0e8); border: 1px solid #e0d5c5; border-radius: 8px; padding: 20px; margin: 0;">
                                <p style="color: #666; font-size: 14px; margin: 0 0 10px; font-style: italic;">You told us:</p>
                                <p style="color: #2c2c2c; font-size: 15px; line-height: 1.6; margin: 0;">
                                    "{intention}"
                                </p>
                            </div>
                        </td>
                    </tr>

                    <!-- Main Content -->
                    <tr>
                        <td style="padding: 10px 40px 20px;">
                            <h2 style="color: #333; font-size: 18px; margin: 0 0 15px;">About Your Magic</h2>
                            <p style="color: #666; font-size: 15px; line-height: 1.7; margin: 0 0 15px;">
                                The magic we practice is white magic—powerful, ethical magic that works through positive energy and intention. While we are confident in its power, it's important to understand that magic works through the Universe in its own way and time.
                            </p>
                            <p style="color: #666; font-size: 15px; line-height: 1.7; margin: 0 0 15px;">
                                Magic helps clear obstacles on the path to your desire and aligns the Universal intent with your wishes. Think of your spell like a seed planted in fertile soil—it needs time, patience, and care to grow and manifest results.
                            </p>
                            <p style="color: #666; font-size: 15px; line-height: 1.7; margin: 0;">
                                The best thing you can do now is act as if the magic is working and trust in the process. Doubt and worry can scatter the magic's energy. Walk confidently on the path that the spell has opened to your desires.
                            </p>
                        </td>
                    </tr>

                    <!-- What If Section -->
                    <tr>
                        <td style="padding: 10px 40px 20px;">
                            <h2 style="color: #333; font-size: 18px; margin: 0 0 15px;">What If Results Differ?</h2>
                            <p style="color: #666; font-size: 15px; line-height: 1.7; margin: 0;">
                                If the results don't manifest exactly as you envisioned, know that the Universal Spirit often works in mysterious ways and may be guiding you toward an even better outcome. Remain open-minded and trust that you will receive what is truly best for your life and spirit.
                            </p>
                        </td>
                    </tr>

                    <!-- Closing -->
                    <tr>
                        <td style="padding: 20px 40px 30px;">
                            <p style="color: #666; font-size: 14px; line-height: 1.6; margin: 0;">
                                We wish you peace, health, and happiness on your journey.
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
                                If you have a moment, we'd love to hear about your experience.
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


def _build_cast_by_us_plain(customer_name: str, spell_type: str, intention: str) -> str:
    """Build the plain text email content for cast-by-us confirmation."""
    return f"""Dear {customer_name},

Your {spell_type.title()} has been cast on your behalf. The forces it has unleashed are now active, and we have taken your expressed desire and formed it into a magical request to the Universal Spirit, seeking what you have asked to be manifested.

---

YOU TOLD US:
"{intention}"

---

ABOUT YOUR MAGIC

The magic we practice is white magic—powerful, ethical magic that works through positive energy and intention. While we are confident in its power, it's important to understand that magic works through the Universe in its own way and time.

Magic helps clear obstacles on the path to your desire and aligns the Universal intent with your wishes. Think of your spell like a seed planted in fertile soil—it needs time, patience, and care to grow and manifest results.

The best thing you can do now is act as if the magic is working and trust in the process. Doubt and worry can scatter the magic's energy. Walk confidently on the path that the spell has opened to your desires.

---

WHAT IF RESULTS DIFFER?

If the results don't manifest exactly as you envisioned, know that the Universal Spirit often works in mysterious ways and may be guiding you toward an even better outcome. Remain open-minded and trust that you will receive what is truly best for your life and spirit.

---

We wish you peace, health, and happiness on your journey.

With mystical blessings,
{settings.FROM_NAME}

---
If you have a moment, we'd love to hear about your experience.
"""


async def send_combination_email(
    to_email: str,
    customer_name: str,
    spell_type: str,
    intention: str,
    spell_instructions: str,
    subject: Optional[str] = None,
) -> EmailResult:
    """Send a combination email: cast-by-us confirmation + customer cast instructions.

    Args:
        to_email: Customer's email address
        customer_name: Customer's name for personalization
        spell_type: Type of spell
        intention: Customer's original intention
        spell_instructions: AI-generated spell instructions
        subject: Optional custom subject line

    Returns:
        EmailResult with success status and message ID or error
    """
    if not settings.SENDGRID_API_KEY:
        raise EmailDeliveryError("SendGrid API key not configured")

    if not subject:
        subject = f"Your {spell_type.title()} - Cast & Enhancement Instructions"

    # Build the email content
    html_content = _build_combination_html(customer_name, spell_type, intention, spell_instructions)
    plain_content = _build_combination_plain(customer_name, spell_type, intention, spell_instructions)

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
        "reply_to": {
            "email": settings.FROM_EMAIL,
            "name": settings.FROM_NAME,
        },
        "headers": {
            "List-Unsubscribe": f"<mailto:{settings.FROM_EMAIL}?subject=Unsubscribe>",
            "Precedence": "bulk",
        },
        "content": [
            {"type": "text/plain", "value": plain_content},
            {"type": "text/html", "value": html_content},
        ],
        "tracking_settings": {
            "click_tracking": {"enable": False},
            "open_tracking": {"enable": False},
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


def _build_combination_html(
    customer_name: str, spell_type: str, intention: str, spell_instructions: str
) -> str:
    """Build the HTML email content for combination (cast-by-us + customer cast)."""
    spell_html = spell_instructions.replace("\n", "<br>")

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your Spell - Cast & Instructions</title>
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
                                Your {spell_type.title()}
                            </h1>
                            <p style="color: #c9b896; font-size: 14px; margin: 10px 0 0;">Cast by Us + Your Personal Instructions</p>
                        </td>
                    </tr>

                    <!-- PART 1: Cast By Us Section -->
                    <tr>
                        <td style="padding: 30px 40px 10px;">
                            <h2 style="color: #1a1a2e; font-size: 20px; margin: 0 0 15px; padding-bottom: 10px; border-bottom: 2px solid #e0d5c5;">
                                Part 1: Your Spell Has Been Cast
                            </h2>
                            <p style="color: #666; font-size: 15px; line-height: 1.7; margin: 0 0 15px;">
                                Dear {customer_name}, your spell has been cast on your behalf. The forces it has unleashed are now active, and we have taken your expressed desire and formed it into a magical request to the Universal Spirit.
                            </p>
                        </td>
                    </tr>

                    <!-- Intention Box -->
                    <tr>
                        <td style="padding: 0 40px 20px;">
                            <div style="background: linear-gradient(to bottom, #faf8f5, #f5f0e8); border: 1px solid #e0d5c5; border-radius: 8px; padding: 20px; margin: 0;">
                                <p style="color: #666; font-size: 14px; margin: 0 0 10px; font-style: italic;">You told us:</p>
                                <p style="color: #2c2c2c; font-size: 15px; line-height: 1.6; margin: 0;">
                                    "{intention}"
                                </p>
                            </div>
                        </td>
                    </tr>

                    <!-- Magic Explanation -->
                    <tr>
                        <td style="padding: 0 40px 20px;">
                            <p style="color: #666; font-size: 15px; line-height: 1.7; margin: 0;">
                                The magic we practice is white magic—powerful, ethical magic that works through positive energy. Magic helps clear obstacles on the path to your desire. Think of your spell like a seed planted in fertile soil—it needs time and care to manifest results. Trust in the process and walk confidently on the path the spell has opened.
                            </p>
                        </td>
                    </tr>

                    <!-- PART 2: Customer Cast Instructions -->
                    <tr>
                        <td style="padding: 20px 40px 10px;">
                            <h2 style="color: #1a1a2e; font-size: 20px; margin: 0 0 15px; padding-bottom: 10px; border-bottom: 2px solid #e0d5c5;">
                                Part 2: Amplify Your Magic
                            </h2>
                            <p style="color: #666; font-size: 15px; line-height: 1.7; margin: 0 0 15px;">
                                While we have cast the spell on your behalf, you can multiply its effects by performing your own ritual. Here are personalized instructions for you:
                            </p>
                        </td>
                    </tr>

                    <!-- Spell Instructions -->
                    <tr>
                        <td style="padding: 0 40px 20px;">
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
                                We wish you peace, health, and happiness on your journey.
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


def _build_combination_plain(
    customer_name: str, spell_type: str, intention: str, spell_instructions: str
) -> str:
    """Build the plain text email content for combination (cast-by-us + customer cast)."""
    return f"""Dear {customer_name},

Your {spell_type.title()} - Cast by Us + Your Personal Instructions

=====================================
PART 1: YOUR SPELL HAS BEEN CAST
=====================================

Your spell has been cast on your behalf. The forces it has unleashed are now active, and we have taken your expressed desire and formed it into a magical request to the Universal Spirit.

YOU TOLD US:
"{intention}"

The magic we practice is white magic—powerful, ethical magic that works through positive energy. Magic helps clear obstacles on the path to your desire. Think of your spell like a seed planted in fertile soil—it needs time and care to manifest results. Trust in the process and walk confidently on the path the spell has opened.

=====================================
PART 2: AMPLIFY YOUR MAGIC
=====================================

While we have cast the spell on your behalf, you can multiply its effects by performing your own ritual. Here are personalized instructions for you:

---

{spell_instructions}

---

We wish you peace, health, and happiness on your journey.

With mystical blessings,
{settings.FROM_NAME}

---
This spell was created especially for you based on your intention.
"""


@dataclass
class EmailPreviewResult:
    """Result of email preview generation."""

    subject: str
    html_content: str
    plain_content: str


def get_email_preview(
    cast_type: str,
    customer_name: str,
    spell_type: str,
    intention: str,
    spell_content: Optional[str] = None,
) -> EmailPreviewResult:
    """Generate email preview content without sending.

    Args:
        cast_type: The cast type (cast_by_us, customer_cast, combination)
        customer_name: Customer's name for personalization
        spell_type: Type of spell
        intention: Customer's original intention
        spell_content: AI-generated spell content (required for customer_cast and combination)

    Returns:
        EmailPreviewResult with subject, HTML, and plain text content
    """
    if cast_type == "cast_by_us":
        subject = f"Your {spell_type.title()} Has Been Cast"
        html_content = _build_cast_by_us_html(customer_name, spell_type, intention)
        plain_content = _build_cast_by_us_plain(customer_name, spell_type, intention)
    elif cast_type == "combination":
        subject = f"Your {spell_type.title()} - Cast & Instructions"
        html_content = _build_combination_html(
            customer_name, spell_type, intention, spell_content or ""
        )
        plain_content = _build_combination_plain(
            customer_name, spell_type, intention, spell_content or ""
        )
    else:  # customer_cast (default)
        subject = f"Your Personalized {spell_type.title()} is Ready"
        html_content = _build_spell_email_html(
            customer_name, spell_content or "", spell_type
        )
        plain_content = _build_spell_email_plain(customer_name, spell_content or "")

    return EmailPreviewResult(
        subject=subject,
        html_content=html_content,
        plain_content=plain_content,
    )
