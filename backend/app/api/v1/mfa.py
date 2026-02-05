"""
Multi-Factor Authentication (MFA) endpoints.

Provides TOTP-based MFA setup, verification, and management.
"""

from __future__ import annotations

import base64
import io
import logging
import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pyotp
import qrcode
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.security import hash_password, verify_password

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mfa", tags=["MFA"])


# =============================================================================
# Request/Response Models
# =============================================================================


class MFASetupResponse(BaseModel):
    """MFA setup response with secret and QR code."""

    secret: str = Field(description="TOTP secret (base32 encoded)")
    qr_code: str = Field(description="QR code as base64 PNG image")
    provisioning_uri: str = Field(description="TOTP provisioning URI")
    backup_codes: list[str] = Field(description="One-time backup codes")


class MFAVerifyRequest(BaseModel):
    """MFA verification request."""

    code: str = Field(
        min_length=6, max_length=8, description="6-digit TOTP code or 8-character backup code"
    )


class MFAVerifyResponse(BaseModel):
    """MFA verification response."""

    verified: bool
    message: str
    backup_code_used: bool = False


class MFAEnableRequest(BaseModel):
    """Request to enable MFA after setup."""

    code: str = Field(min_length=6, max_length=6, description="6-digit TOTP code to verify setup")


class MFADisableRequest(BaseModel):
    """Request to disable MFA."""

    password: str = Field(description="Current password for confirmation")
    code: str = Field(min_length=6, max_length=8, description="Current TOTP code or backup code")


class MFAStatusResponse(BaseModel):
    """MFA status response."""

    enabled: bool
    enabled_at: datetime | None = None
    backup_codes_remaining: int = 0


class BackupCodesResponse(BaseModel):
    """Backup codes response."""

    backup_codes: list[str]
    generated_at: datetime


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


# =============================================================================
# Helper Functions
# =============================================================================


def generate_totp_secret() -> str:
    """Generate a new TOTP secret."""
    return pyotp.random_base32()


def generate_provisioning_uri(secret: str, email: str, issuer: str = "AssemblematicAI") -> str:
    """Generate TOTP provisioning URI for authenticator apps."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)


def generate_qr_code_base64(provisioning_uri: str) -> str:
    """Generate QR code as base64-encoded PNG."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(provisioning_uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return base64.b64encode(buffer.read()).decode("utf-8")


def generate_backup_codes(count: int = 10) -> list[str]:
    """Generate random backup codes."""
    codes = []
    for _ in range(count):
        # Generate 8-character alphanumeric codes
        code = secrets.token_hex(4).upper()
        codes.append(code)
    return codes


def hash_backup_codes(codes: list[str]) -> list[dict]:
    """Hash backup codes for storage."""
    return [
        {
            "hash": hash_password(code),
            "used": False,
            "used_at": None,
        }
        for code in codes
    ]


def verify_totp_code(secret: str, code: str) -> bool:
    """Verify a TOTP code."""
    totp = pyotp.TOTP(secret)
    # Allow 1 window of tolerance (30 seconds before/after)
    return totp.verify(code, valid_window=1)


def verify_backup_code(stored_codes: list[dict], provided_code: str) -> tuple[bool, int | None]:
    """
    Verify a backup code and return (is_valid, code_index).

    Returns the index of the matched code if valid, so it can be marked as used.
    """
    for i, code_entry in enumerate(stored_codes):
        if code_entry.get("used"):
            continue
        if verify_password(provided_code.upper(), code_entry["hash"]):
            return True, i
    return False, None


# =============================================================================
# MFA Setup Endpoints
# =============================================================================


@router.get(
    "/status",
    response_model=MFAStatusResponse,
    summary="Get MFA status",
    description="Check if MFA is enabled for the current user.",
)
async def get_mfa_status(
    current_user: User = Depends(get_current_user),
) -> MFAStatusResponse:
    """Get the current MFA status for the user."""
    return MFAStatusResponse(
        enabled=current_user.mfa_enabled,
        enabled_at=current_user.mfa_enabled_at,
        backup_codes_remaining=current_user.mfa_backup_codes_remaining,
    )


@router.post(
    "/setup",
    response_model=MFASetupResponse,
    summary="Initialize MFA setup",
    description="Generate TOTP secret and QR code for MFA setup.",
)
async def setup_mfa(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MFASetupResponse:
    """
    Initialize MFA setup.

    Generates a new TOTP secret and QR code. The user must verify with
    a code before MFA is actually enabled.
    """
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled. Disable it first to set up again.",
        )

    # Generate new secret
    secret = generate_totp_secret()

    # Generate provisioning URI and QR code
    provisioning_uri = generate_provisioning_uri(
        secret=secret,
        email=current_user.email,
        issuer=settings.APP_NAME,
    )
    qr_code = generate_qr_code_base64(provisioning_uri)

    # Generate backup codes
    backup_codes = generate_backup_codes(10)
    hashed_codes = hash_backup_codes(backup_codes)

    # Store secret and backup codes (not enabled yet)
    current_user.mfa_secret = secret
    current_user.mfa_backup_codes = hashed_codes
    await db.commit()

    logger.info(f"MFA setup initiated for user {current_user.id}")

    return MFASetupResponse(
        secret=secret,
        qr_code=qr_code,
        provisioning_uri=provisioning_uri,
        backup_codes=backup_codes,
    )


@router.post(
    "/enable",
    response_model=MessageResponse,
    summary="Enable MFA",
    description="Enable MFA after verifying setup with a TOTP code.",
)
async def enable_mfa(
    request: MFAEnableRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Enable MFA after setup.

    Requires verification with a valid TOTP code to confirm the user
    has successfully configured their authenticator app.
    """
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled.",
        )

    if not current_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA setup not initiated. Call /mfa/setup first.",
        )

    # Verify the code
    if not verify_totp_code(current_user.mfa_secret, request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code. Please try again.",
        )

    # Enable MFA
    current_user.mfa_enabled = True
    current_user.mfa_enabled_at = datetime.now(UTC)
    await db.commit()

    logger.info(f"MFA enabled for user {current_user.id}")

    return MessageResponse(message="MFA has been successfully enabled.")


@router.post(
    "/disable",
    response_model=MessageResponse,
    summary="Disable MFA",
    description="Disable MFA with password and code verification.",
)
async def disable_mfa(
    request: MFADisableRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Disable MFA.

    Requires both password and a valid TOTP code or backup code
    for security verification.
    """
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled.",
        )

    # Verify password
    if not verify_password(request.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password.",
        )

    # Verify TOTP code or backup code
    code_valid = False

    # Try TOTP first
    if len(request.code) == 6 and request.code.isdigit():
        code_valid = verify_totp_code(current_user.mfa_secret, request.code)

    # Try backup code
    if not code_valid and current_user.mfa_backup_codes:
        code_valid, _ = verify_backup_code(current_user.mfa_backup_codes, request.code)

    if not code_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code.",
        )

    # Disable MFA
    current_user.mfa_enabled = False
    current_user.mfa_secret = None
    current_user.mfa_backup_codes = None
    current_user.mfa_enabled_at = None
    await db.commit()

    logger.info(f"MFA disabled for user {current_user.id}")

    return MessageResponse(message="MFA has been successfully disabled.")


# =============================================================================
# MFA Verification Endpoints
# =============================================================================


@router.post(
    "/verify",
    response_model=MFAVerifyResponse,
    summary="Verify MFA code",
    description="Verify a TOTP code or backup code.",
)
async def verify_mfa(
    request: MFAVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MFAVerifyResponse:
    """
    Verify an MFA code.

    Can be used to verify either a 6-digit TOTP code or an 8-character
    backup code. Backup codes are single-use.
    """
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled for this account.",
        )

    code = request.code.strip()

    # Try TOTP verification first (6 digits)
    if len(code) == 6 and code.isdigit() and verify_totp_code(current_user.mfa_secret, code):
        return MFAVerifyResponse(
            verified=True,
            message="Code verified successfully.",
            backup_code_used=False,
        )

    # Try backup code verification
    if current_user.mfa_backup_codes:
        is_valid, code_index = verify_backup_code(current_user.mfa_backup_codes, code)

        if is_valid and code_index is not None:
            # Mark backup code as used
            current_user.mfa_backup_codes[code_index]["used"] = True
            current_user.mfa_backup_codes[code_index]["used_at"] = datetime.now(UTC).isoformat()
            await db.commit()

            remaining = current_user.mfa_backup_codes_remaining
            logger.info(
                f"Backup code used for user {current_user.id}. {remaining} codes remaining."
            )

            return MFAVerifyResponse(
                verified=True,
                message=f"Backup code verified. {remaining} backup codes remaining.",
                backup_code_used=True,
            )

    # Invalid code
    logger.warning(f"Failed MFA verification attempt for user {current_user.id}")

    return MFAVerifyResponse(
        verified=False,
        message="Invalid verification code.",
        backup_code_used=False,
    )


# =============================================================================
# Backup Code Management
# =============================================================================


@router.post(
    "/backup-codes/regenerate",
    response_model=BackupCodesResponse,
    summary="Regenerate backup codes",
    description="Generate new backup codes (invalidates old ones).",
)
async def regenerate_backup_codes(
    request: MFAVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BackupCodesResponse:
    """
    Regenerate backup codes.

    Requires verification with a TOTP code. Old backup codes are
    invalidated when new ones are generated.
    """
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled.",
        )

    # Verify TOTP code
    if not verify_totp_code(current_user.mfa_secret, request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code.",
        )

    # Generate new backup codes
    backup_codes = generate_backup_codes(10)
    hashed_codes = hash_backup_codes(backup_codes)

    current_user.mfa_backup_codes = hashed_codes
    await db.commit()

    logger.info(f"Backup codes regenerated for user {current_user.id}")

    return BackupCodesResponse(
        backup_codes=backup_codes,
        generated_at=datetime.now(UTC),
    )


@router.get(
    "/backup-codes/count",
    response_model=dict,
    summary="Get backup codes count",
    description="Get the number of remaining unused backup codes.",
)
async def get_backup_codes_count(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get count of remaining backup codes."""
    if not current_user.mfa_enabled:
        return {"remaining": 0, "total": 0}

    total = len(current_user.mfa_backup_codes) if current_user.mfa_backup_codes else 0
    remaining = current_user.mfa_backup_codes_remaining

    return {
        "remaining": remaining,
        "total": total,
    }
