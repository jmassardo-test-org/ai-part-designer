"""
Contact Form API Endpoints.

Handles contact form submissions from the public website.
"""

from typing import Any

import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field, field_validator

router = APIRouter(prefix="/contact", tags=["contact"])
logger = logging.getLogger(__name__)


# =============================
# Schemas
# =============================


class ContactFormRequest(BaseModel):
    """Contact form submission request."""

    name: str = Field(..., min_length=2, max_length=100, description="Sender's name")
    email: EmailStr = Field(..., description="Sender's email address")
    subject: str = Field(..., min_length=5, max_length=200, description="Message subject")
    message: str = Field(..., min_length=20, max_length=5000, description="Message content")

    @field_validator("name", "subject", "message")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading/trailing whitespace from string fields."""
        return v.strip()


class ContactFormResponse(BaseModel):
    """Contact form submission response."""

    success: bool = True
    message: str = "Your message has been sent successfully. We'll get back to you soon."


# =============================
# Rate Limiting (Simple In-Memory)
# =============================

# Simple in-memory rate limiting - in production, use Redis
_submission_times: dict[str, list[datetime]] = {}
RATE_LIMIT_WINDOW = 3600  # 1 hour
RATE_LIMIT_MAX = 5  # Max 5 submissions per hour per IP


def check_rate_limit(ip_address: str) -> bool:
    """
    Check if the IP address has exceeded the rate limit.

    Args:
        ip_address: The client's IP address.

    Returns:
        True if within limit, False if exceeded.
    """
    now = datetime.now(tz=datetime.UTC)
    cutoff = now.timestamp() - RATE_LIMIT_WINDOW

    if ip_address not in _submission_times:
        _submission_times[ip_address] = []

    # Filter to only recent submissions
    _submission_times[ip_address] = [
        t for t in _submission_times[ip_address] if t.timestamp() > cutoff
    ]

    if len(_submission_times[ip_address]) >= RATE_LIMIT_MAX:
        return False

    _submission_times[ip_address].append(now)
    return True


# =============================
# Background Task: Send Email
# =============================


async def send_contact_email(
    name: str,
    email: str,
    subject: str,
    message: str,
    ip_address: str,
) -> None:
    """
    Send contact form notification email.

    In production, this would integrate with an email service like:
    - SendGrid
    - AWS SES
    - Mailgun
    - Resend

    For now, we just log the submission.
    """
    logger.info(
        "Contact form submission received",
        extra={
            "name": name,
            "email": email,
            "subject": subject,
            "message_length": len(message),
            "ip_address": ip_address,
        },
    )

    # TODO: Integrate with email service (e.g., SendGrid or similar)
    # When implemented, send notification to support@assemblematicai.com
    # For development, print to console
    print(f"""
    ========================================
    NEW CONTACT FORM SUBMISSION
    ========================================
    From: {name} <{email}>
    Subject: {subject}
    IP: {ip_address}
    ----------------------------------------
    {message}
    ========================================
    """)


# =============================
# Endpoints
# =============================


@router.post(
    "",
    response_model=ContactFormResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit contact form",
    description="Submit a contact form message. Rate limited to prevent spam.",
)
async def submit_contact_form(
    request: Request,
    form: ContactFormRequest,
    background_tasks: BackgroundTasks,
) -> ContactFormResponse:
    """
    Handle contact form submission.

    Args:
        request: FastAPI request object for IP extraction.
        form: The contact form data.
        background_tasks: FastAPI background tasks for async email sending.

    Returns:
        ContactFormResponse with success message.

    Raises:
        HTTPException: If rate limit exceeded or validation fails.
    """
    # Get client IP (handle proxy headers)
    ip_address = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    if not ip_address:
        ip_address = request.client.host if request.client else "unknown"

    # Check rate limit
    if not check_rate_limit(ip_address):
        logger.warning(f"Rate limit exceeded for contact form submission from {ip_address}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many submissions. Please try again later.",
        )

    # Basic spam detection
    # Check for common spam patterns
    spam_keywords = ["viagra", "casino", "lottery", "winner", "inheritance"]
    message_lower = form.message.lower()
    if any(keyword in message_lower for keyword in spam_keywords):
        logger.warning(f"Spam detected in contact form from {ip_address}")
        # Return success to not reveal detection
        return ContactFormResponse()

    # Schedule email notification as background task
    background_tasks.add_task(
        send_contact_email,
        name=form.name,
        email=form.email,
        subject=form.subject,
        message=form.message,
        ip_address=ip_address,
    )

    logger.info(f"Contact form submitted successfully from {ip_address}")

    return ContactFormResponse()


@router.get(
    "/info",
    summary="Get contact information",
    description="Get public contact information for the company.",
)
async def get_contact_info() -> dict[str, Any]:
    """
    Get public contact information.

    Returns:
        Dictionary with contact details.
    """
    return {
        "email": "support@assemblematicai.com",
        "sales_email": "sales@assemblematicai.com",
        "address": {
            "street": "123 Innovation Way",
            "city": "San Francisco",
            "state": "CA",
            "zip": "94107",
            "country": "United States",
        },
        "response_time": "24-48 hours",
        "social": {
            "twitter": "@assemblematicai",
            "github": "github.com/assemblematicai",
            "linkedin": "linkedin.com/company/assemblematicai",
        },
    }
