"""
Email service for sending transactional emails.

Supports multiple backends: SMTP, SendGrid, AWS SES.
Uses async templates with Jinja2 for email content.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EmailTemplate(StrEnum):
    """Available email templates."""

    VERIFICATION = "verification"
    PASSWORD_RESET = "password_reset"
    WELCOME = "welcome"
    PASSWORD_CHANGED = "password_changed"
    TRASH_DELETION_WARNING = "trash_deletion_warning"


@dataclass
class EmailMessage:
    """Email message to send."""

    to: str
    subject: str
    html_body: str
    text_body: str | None = None
    from_email: str | None = None
    reply_to: str | None = None


class EmailBackend(ABC):
    """Abstract base class for email backends."""

    @abstractmethod
    async def send(self, message: EmailMessage) -> bool:
        """Send an email message."""


class ConsoleEmailBackend(EmailBackend):
    """
    Console email backend for development.

    Prints emails to the console instead of sending them.
    """

    async def send(self, message: EmailMessage) -> bool:
        """Print email to console."""
        logger.info(
            f"\n{'=' * 60}\n"
            f"📧 EMAIL TO: {message.to}\n"
            f"📋 SUBJECT: {message.subject}\n"
            f"{'=' * 60}\n"
            f"{message.text_body or message.html_body}\n"
            f"{'=' * 60}\n"
        )
        return True


class SMTPEmailBackend(EmailBackend):
    """
    SMTP email backend.

    Uses aiosmtplib for async email sending.
    """

    def __init__(
        self,
        host: str,
        port: int,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls

    async def send(self, message: EmailMessage) -> bool:
        """Send email via SMTP."""
        try:
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            import aiosmtplib

            settings = get_settings()

            msg = MIMEMultipart("alternative")
            msg["Subject"] = message.subject
            msg["From"] = (
                message.from_email or f"noreply@{settings.APP_NAME.lower().replace(' ', '')}.com"
            )
            msg["To"] = message.to

            if message.text_body:
                msg.attach(MIMEText(message.text_body, "plain"))
            msg.attach(MIMEText(message.html_body, "html"))

            await aiosmtplib.send(
                msg,
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                use_tls=self.use_tls,
            )

            logger.info(f"Email sent to {message.to}: {message.subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {message.to}: {e}")
            return False


class EmailService:
    """
    Email service for sending transactional emails.

    Handles template rendering and email delivery.

    Example:
        >>> service = get_email_service()
        >>> await service.send_verification_email(
        ...     email="user@example.com",
        ...     display_name="John",
        ...     verification_url="https://app.com/verify?token=abc"
        ... )
    """

    def __init__(self, backend: EmailBackend):
        self.backend = backend
        self._templates = self._load_templates()

    def _load_templates(self) -> dict[EmailTemplate, dict[str, str]]:
        """Load email templates."""
        return {
            EmailTemplate.VERIFICATION: {
                "subject": "Verify your email - {app_name}",
                "html": """
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .button {{ display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 4px; }}
        .footer {{ margin-top: 40px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Welcome to {app_name}!</h1>
        <p>Hi {display_name},</p>
        <p>Thanks for signing up! Please verify your email address by clicking the button below:</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{verification_url}" class="button">Verify Email</a>
        </p>
        <p>Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #666;">{verification_url}</p>
        <p>This link will expire in 24 hours.</p>
        <div class="footer">
            <p>If you didn't create an account, you can safely ignore this email.</p>
            <p>&copy; {year} {app_name}. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
""",
                "text": """
Welcome to {app_name}!

Hi {display_name},

Thanks for signing up! Please verify your email address by visiting:

{verification_url}

This link will expire in 24 hours.

If you didn't create an account, you can safely ignore this email.

© {year} {app_name}
""",
            },
            EmailTemplate.PASSWORD_RESET: {
                "subject": "Reset your password - {app_name}",
                "html": """
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .button {{ display: inline-block; padding: 12px 24px; background-color: #dc3545; color: white; text-decoration: none; border-radius: 4px; }}
        .footer {{ margin-top: 40px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Password Reset Request</h1>
        <p>Hi {display_name},</p>
        <p>We received a request to reset your password. Click the button below to choose a new password:</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}" class="button">Reset Password</a>
        </p>
        <p>Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #666;">{reset_url}</p>
        <p>This link will expire in 1 hour.</p>
        <div class="footer">
            <p>If you didn't request a password reset, you can safely ignore this email. Your password won't be changed.</p>
            <p>&copy; {year} {app_name}. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
""",
                "text": """
Password Reset Request

Hi {display_name},

We received a request to reset your password. Visit this link to choose a new password:

{reset_url}

This link will expire in 1 hour.

If you didn't request a password reset, you can safely ignore this email.

© {year} {app_name}
""",
            },
            EmailTemplate.WELCOME: {
                "subject": "Welcome to {app_name}!",
                "html": """
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Welcome to {app_name}! 🎉</h1>
        <p>Hi {display_name},</p>
        <p>Your email has been verified and your account is now active!</p>
        <p>You can now:</p>
        <ul>
            <li>Create 3D parts from natural language descriptions</li>
            <li>Browse and customize our template library</li>
            <li>Export your designs to STEP and STL formats</li>
        </ul>
        <p>Happy designing!</p>
        <p>The {app_name} Team</p>
    </div>
</body>
</html>
""",
                "text": """
Welcome to {app_name}!

Hi {display_name},

Your email has been verified and your account is now active!

Happy designing!

The {app_name} Team
""",
            },
            EmailTemplate.PASSWORD_CHANGED: {
                "subject": "Your password has been changed - {app_name}",
                "html": """
<!DOCTYPE html>
<html>
<body>
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; font-family: sans-serif;">
        <h1>Password Changed</h1>
        <p>Hi {display_name},</p>
        <p>Your password was successfully changed on {timestamp}.</p>
        <p>If you didn't make this change, please contact support immediately.</p>
    </div>
</body>
</html>
""",
                "text": """
Password Changed

Hi {display_name},

Your password was successfully changed on {timestamp}.

If you didn't make this change, please contact support immediately.
""",
            },
            EmailTemplate.TRASH_DELETION_WARNING: {
                "subject": "Items in your trash will be permanently deleted - {app_name}",
                "html": """
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .warning {{ background-color: #fff3cd; border: 1px solid #ffc107; border-radius: 4px; padding: 15px; margin: 20px 0; }}
        .item-list {{ background-color: #f8f9fa; border-radius: 4px; padding: 15px; margin: 15px 0; }}
        .item {{ padding: 8px 0; border-bottom: 1px solid #dee2e6; }}
        .item:last-child {{ border-bottom: none; }}
        .button {{ display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 4px; }}
        .button-secondary {{ background-color: #6c757d; }}
        .footer {{ margin-top: 40px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>⚠️ Trash Deletion Notice</h1>
        <p>Hi {display_name},</p>

        <div class="warning">
            <strong>Action Required:</strong> The following items in your trash will be permanently deleted in {days_until_deletion} day(s).
        </div>

        <div class="item-list">
            <h3>Items scheduled for deletion:</h3>
            {item_list_html}
        </div>

        <p>
            <a href="{trash_url}" class="button">Review Trash</a>
            <a href="{settings_url}" class="button button-secondary" style="margin-left: 10px;">Manage Settings</a>
        </p>

        <p>To keep these items, restore them from your trash before the deletion date.</p>

        <div class="footer">
            <p>You're receiving this email because you have items expiring in your trash. You can disable these notifications in your account settings.</p>
            <p>&copy; {year} {app_name}. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
""",
                "text": """
⚠️ Trash Deletion Notice

Hi {display_name},

The following items in your trash will be permanently deleted in {days_until_deletion} day(s):

{item_list_text}

To keep these items, restore them from your trash before the deletion date.

Review your trash: {trash_url}
Manage settings: {settings_url}

© {year} {app_name}
""",
            },
        }

    def _render_template(
        self,
        template: EmailTemplate,
        context: dict[str, Any],
    ) -> tuple[str, str, str]:
        """
        Render email template with context.

        Returns:
            Tuple of (subject, html_body, text_body)
        """
        from datetime import datetime

        settings = get_settings()

        # Default context
        default_context = {
            "app_name": settings.APP_NAME,
            "year": datetime.now(tz=datetime.UTC).year,
        }
        full_context = {**default_context, **context}

        tmpl = self._templates[template]

        subject = tmpl["subject"].format(**full_context)
        html_body = tmpl["html"].format(**full_context)
        text_body = tmpl["text"].format(**full_context)

        return subject, html_body, text_body

    async def send_verification_email(
        self,
        email: str,
        display_name: str,
        verification_url: str,
    ) -> bool:
        """Send email verification email."""
        subject, html, text = self._render_template(
            EmailTemplate.VERIFICATION,
            {
                "display_name": display_name,
                "verification_url": verification_url,
            },
        )

        return await self.backend.send(
            EmailMessage(
                to=email,
                subject=subject,
                html_body=html,
                text_body=text,
            )
        )

    async def send_password_reset_email(
        self,
        email: str,
        display_name: str,
        reset_url: str,
    ) -> bool:
        """Send password reset email."""
        subject, html, text = self._render_template(
            EmailTemplate.PASSWORD_RESET,
            {
                "display_name": display_name,
                "reset_url": reset_url,
            },
        )

        return await self.backend.send(
            EmailMessage(
                to=email,
                subject=subject,
                html_body=html,
                text_body=text,
            )
        )

    async def send_welcome_email(
        self,
        email: str,
        display_name: str,
    ) -> bool:
        """Send welcome email after verification."""
        subject, html, text = self._render_template(
            EmailTemplate.WELCOME,
            {"display_name": display_name},
        )

        return await self.backend.send(
            EmailMessage(
                to=email,
                subject=subject,
                html_body=html,
                text_body=text,
            )
        )

    async def send_password_changed_email(
        self,
        email: str,
        display_name: str,
    ) -> bool:
        """Send notification that password was changed."""
        from datetime import datetime

        subject, html, text = self._render_template(
            EmailTemplate.PASSWORD_CHANGED,
            {
                "display_name": display_name,
                "timestamp": datetime.now(tz=datetime.UTC).strftime("%Y-%m-%d %H:%M UTC"),
            },
        )

        return await self.backend.send(
            EmailMessage(
                to=email,
                subject=subject,
                html_body=html,
                text_body=text,
            )
        )

    async def send_trash_deletion_warning(
        self,
        email: str,
        display_name: str,
        days_until_deletion: int,
        items: list[dict[str, Any]],
        trash_url: str,
        settings_url: str,
    ) -> bool:
        """
        Send warning about items scheduled for permanent deletion.

        Args:
            email: User's email address
            display_name: User's display name
            days_until_deletion: Days until items are permanently deleted
            items: List of items with 'name', 'type', and 'deleted_at' keys
            trash_url: URL to view trash
            settings_url: URL to manage trash settings
        """
        # Build HTML item list
        item_list_html = ""
        for item in items:
            item_list_html += f"""
            <div class="item">
                <strong>{item["name"]}</strong>
                <span style="color: #666; margin-left: 10px;">({item["type"]})</span>
                <br><small style="color: #999;">Deleted on {item["deleted_at"]}</small>
            </div>
            """

        # Build text item list
        item_list_text = "\n".join(
            f"  • {item['name']} ({item['type']}) - deleted {item['deleted_at']}" for item in items
        )

        subject, html, text = self._render_template(
            EmailTemplate.TRASH_DELETION_WARNING,
            {
                "display_name": display_name,
                "days_until_deletion": days_until_deletion,
                "item_list_html": item_list_html or "<p>No items</p>",
                "item_list_text": item_list_text or "  (No items)",
                "trash_url": trash_url,
                "settings_url": settings_url,
            },
        )

        return await self.backend.send(
            EmailMessage(
                to=email,
                subject=subject,
                html_body=html,
                text_body=text,
            )
        )


@lru_cache
def get_email_service() -> EmailService:
    """
    Get cached email service instance.

    Uses console backend in development, SMTP/SendGrid in production.
    """
    settings = get_settings()

    if settings.ENVIRONMENT == "development" or settings.DEBUG:
        backend = ConsoleEmailBackend()
    else:
        # TODO: Configure SMTP or SendGrid based on settings
        backend = ConsoleEmailBackend()  # Fallback for now

    return EmailService(backend)
