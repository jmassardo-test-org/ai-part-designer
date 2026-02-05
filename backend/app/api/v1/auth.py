"""
Authentication endpoints.

Provides user registration, login, logout, token refresh, and verification.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.auth import get_current_user
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.security import (
    TokenType,
    check_password_strength,
    create_access_token,
    create_refresh_token,
    create_verification_token,
    hash_password,
    verify_password,
    verify_token,
)
from app.models import User
from app.repositories import UserRepository
from app.services.security_audit import SecurityAuditService, SecurityEventType

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# =============================================================================
# Request/Response Models
# =============================================================================


class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr = Field(description="User's email address")
    password: str = Field(
        min_length=8,
        max_length=128,
        description="Password (min 8 chars, must include upper, lower, digit, special)",
    )
    display_name: str = Field(
        min_length=2,
        max_length=50,
        description="Display name",
    )
    accepted_terms: bool = Field(
        default=True,
        description="User accepted terms of service",
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets strength requirements."""
        result = check_password_strength(v)
        if not result["is_valid"]:
            raise ValueError("; ".join(result["issues"]))
        return v

    @field_validator("accepted_terms")
    @classmethod
    def must_accept_terms(cls, v: bool) -> bool:
        """Ensure terms are accepted."""
        if not v:
            raise ValueError("You must accept the terms of service")
        return v


class LoginRequest(BaseModel):
    """User login request."""

    email: EmailStr
    password: str
    remember_me: bool = False


class TokenResponse(BaseModel):
    """Token response for login/refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token expiry in seconds")
    mfa_required: bool = False
    mfa_token: str | None = None  # Temporary token for MFA verification


class UserResponse(BaseModel):
    """Public user data response."""

    id: str
    email: str
    display_name: str
    role: str
    status: str
    created_at: datetime
    email_verified_at: datetime | None = None

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str
    detail: str | None = None


class RefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str


class VerifyEmailRequest(BaseModel):
    """Email verification request."""

    token: str


class PasswordResetRequest(BaseModel):
    """Password reset request."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation."""

    token: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        result = check_password_strength(v)
        if not result["is_valid"]:
            raise ValueError("; ".join(result["issues"]))
        return v


# =============================================================================
# Registration
# =============================================================================


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Create a new user account. Sends verification email.",
)
async def register(
    request: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UserResponse:
    """
    Register a new user account.

    - Validates email uniqueness
    - Hashes password securely
    - Creates user with pending_verification status
    - Sends verification email (async)
    """
    user_repo = UserRepository(db)

    # Check if email already exists
    existing = await user_repo.get_by_email(request.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Create user
    user = User(
        email=request.email.lower(),
        password_hash=hash_password(request.password),
        display_name=request.display_name,
        role="user",
        status="pending_verification",
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"New user registered: {user.email}")

    # Queue verification email
    if settings.REQUIRE_EMAIL_VERIFICATION:
        background_tasks.add_task(
            _send_verification_email,
            user_id=str(user.id),
            email=user.email,
            display_name=user.display_name,
        )
    else:
        # Auto-verify in dev mode
        user.status = "active"
        user.email_verified_at = datetime.utcnow()
        await db.commit()

    return UserResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        status=user.status,
        created_at=user.created_at,
        email_verified_at=user.email_verified_at,
    )


async def _send_verification_email(user_id: str, email: str, display_name: str):
    """Send verification email (background task)."""
    try:
        from app.services.email import get_email_service

        token = create_verification_token(UUID(user_id))
        settings = get_settings()
        verification_url = f"{settings.CORS_ORIGINS[0]}/verify-email?token={token}"

        email_service = get_email_service()
        await email_service.send_verification_email(
            email=email,
            display_name=display_name,
            verification_url=verification_url,
        )
        logger.info(f"Verification email sent to {email}")

    except Exception as e:
        logger.error(f"Failed to send verification email to {email}: {e}")


# =============================================================================
# Login / Logout
# =============================================================================


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login",
    description="Authenticate and receive access/refresh tokens.",
)
async def login(
    credentials: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """
    Authenticate user and return JWT tokens.

    - Validates credentials
    - Checks account status
    - Returns access and refresh tokens
    - Logs authentication attempt
    """
    user_repo = UserRepository(db)

    # Find user
    user = await user_repo.get_by_email(credentials.email.lower())

    if not user or not verify_password(credentials.password, user.password_hash):
        logger.warning(f"Failed login attempt for: {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check account status
    if user.status == "pending_verification":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in",
        )

    if user.status == "suspended":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been suspended",
        )

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active",
        )

    # Check if MFA is enabled
    if user.mfa_enabled and user.mfa_secret:
        # Generate a temporary MFA token instead of full access
        mfa_token = create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role,
            tier=getattr(user, "tier", "free"),
            additional_claims={"mfa_pending": True},
        )

        logger.info(f"MFA required for user: {user.email}")

        return TokenResponse(
            access_token="",  # No access token until MFA verified
            refresh_token="",
            token_type="bearer",
            expires_in=0,
            mfa_required=True,
            mfa_token=mfa_token,
        )

    # Generate tokens (no MFA)
    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        tier=getattr(user, "tier", "free"),
    )

    refresh_token, _ = create_refresh_token(user.id)

    # Update last login
    user.last_login_at = datetime.utcnow()
    await db.commit()

    logger.info(f"User logged in: {user.email}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        mfa_required=False,
    )


class MFALoginRequest(BaseModel):
    """MFA verification for login."""

    mfa_token: str = Field(description="Temporary MFA token from login")
    code: str = Field(min_length=6, max_length=8, description="TOTP code or backup code")


@router.post(
    "/login/mfa",
    response_model=TokenResponse,
    summary="Complete MFA login",
    description="Complete login by verifying MFA code.",
)
async def login_mfa(
    request: MFALoginRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """
    Complete login with MFA verification.

    After initial login returns mfa_required=True, use this endpoint
    with the mfa_token and a valid TOTP code to complete authentication.
    """
    import pyotp

    # Decode the MFA token
    try:
        payload = verify_token(request.mfa_token, TokenType.ACCESS)
        if not payload.get("mfa_pending"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid MFA token",
            )
        user_id = UUID(payload["sub"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired MFA token",
        )

    # Get user
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user or not user.mfa_enabled or not user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled for this account",
        )

    code = request.code.strip()
    code_valid = False
    backup_code_used = False

    # Try TOTP verification (6 digits)
    if len(code) == 6 and code.isdigit():
        totp = pyotp.TOTP(user.mfa_secret)
        code_valid = totp.verify(code, valid_window=1)

    # Try backup code (8 characters)
    if not code_valid and user.mfa_backup_codes:
        for i, code_entry in enumerate(user.mfa_backup_codes):
            if code_entry.get("used"):
                continue
            if verify_password(code.upper(), code_entry["hash"]):
                code_valid = True
                backup_code_used = True
                # Mark backup code as used
                user.mfa_backup_codes[i]["used"] = True
                user.mfa_backup_codes[i]["used_at"] = datetime.utcnow().isoformat()
                break

    if not code_valid:
        logger.warning(f"Failed MFA verification for user: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid verification code",
        )

    # Generate full access tokens
    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        tier=getattr(user, "tier", "free"),
    )

    refresh_token, _ = create_refresh_token(user.id)

    # Update last login
    user.last_login_at = datetime.utcnow()
    await db.commit()

    if backup_code_used:
        remaining = sum(1 for c in user.mfa_backup_codes if not c.get("used", False))
        logger.info(f"User {user.email} used backup code. {remaining} remaining.")

    logger.info(f"User logged in with MFA: {user.email}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        mfa_required=False,
    )


@router.post(
    "/login/form",
    response_model=TokenResponse,
    summary="OAuth2 form login",
    description="Login using OAuth2 password flow (for Swagger UI).",
    include_in_schema=False,
)
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """OAuth2-compatible login endpoint for Swagger UI."""
    credentials = LoginRequest(
        email=form_data.username,
        password=form_data.password,
    )

    # Reuse login logic
    from fastapi import Request

    return await login(
        credentials=credentials,
        request=Request(scope={"type": "http"}),
        db=db,
        settings=settings,
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="User logout",
    description="Invalidate the current access token.",
)
async def logout(
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """
    Logout user by blacklisting their token.
    """
    # Token blacklisting is handled by the auth dependency
    # The actual blacklist happens when the token is validated

    logger.info(f"User logged out: {current_user.email}")

    return MessageResponse(
        message="Successfully logged out",
    )


# =============================================================================
# Token Refresh
# =============================================================================


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Get new access token using refresh token.",
)
async def refresh_token(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """
    Refresh access token using refresh token.
    """
    payload = verify_token(request.refresh_token, expected_type=TokenType.REFRESH)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = UUID(payload["sub"])
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Generate new tokens
    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        tier=getattr(user, "tier", "free"),
    )

    new_refresh_token, _ = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# =============================================================================
# Email Verification
# =============================================================================


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    summary="Verify email address",
    description="Verify email using token from verification email.",
)
async def verify_email(
    request: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Verify user's email address using verification token.
    """
    payload = verify_token(request.token, expected_type=TokenType.VERIFICATION)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    user_id = UUID(payload["sub"])
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.email_verified_at:
        return MessageResponse(
            message="Email already verified",
        )

    # Verify user
    user.email_verified_at = datetime.utcnow()
    user.status = "active"
    await db.commit()

    logger.info(f"Email verified for: {user.email}")

    return MessageResponse(
        message="Email successfully verified",
        detail="You can now log in to your account",
    )


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    summary="Resend verification email",
    description="Request a new verification email.",
)
async def resend_verification(
    email: EmailStr,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Resend verification email.

    Rate limited to 1 per 60 seconds (handled by rate limiter middleware).
    """
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(email.lower())

    # Don't reveal if user exists
    if user and not user.email_verified_at:
        background_tasks.add_task(
            _send_verification_email,
            user_id=str(user.id),
            email=user.email,
            display_name=user.display_name,
        )

    return MessageResponse(
        message="If an unverified account exists, a verification email has been sent",
    )


# =============================================================================
# Password Reset
# =============================================================================


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request password reset",
    description="Request a password reset email.",
)
async def forgot_password(
    request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Request password reset email.

    Always returns success to prevent email enumeration.
    """
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(request.email.lower())

    if user and user.status == "active":
        background_tasks.add_task(
            _send_password_reset_email,
            user_id=str(user.id),
            email=user.email,
            display_name=user.display_name,
        )

    return MessageResponse(
        message="If an account exists, a password reset email has been sent",
    )


async def _send_password_reset_email(user_id: str, email: str, display_name: str):
    """Send password reset email (background task)."""
    try:
        from app.core.security import create_verification_token
        from app.services.email import get_email_service

        # Use verification token with password_reset type
        token = create_verification_token(UUID(user_id), token_type=TokenType.PASSWORD_RESET)
        settings = get_settings()
        reset_url = f"{settings.CORS_ORIGINS[0]}/reset-password?token={token}"

        email_service = get_email_service()
        await email_service.send_password_reset_email(
            email=email,
            display_name=display_name,
            reset_url=reset_url,
        )
        logger.info(f"Password reset email sent to {email}")

    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {e}")


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password",
    description="Reset password using token from email.",
)
async def reset_password(
    request: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Reset password using reset token.
    """
    payload = verify_token(request.token, expected_type=TokenType.PASSWORD_RESET)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user_id = UUID(payload["sub"])
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Update password
    user.password_hash = hash_password(request.new_password)
    await db.commit()

    # Log password reset completion to audit log
    security_audit = SecurityAuditService(db)
    await security_audit.log_event(
        event_type=SecurityEventType.PASSWORD_RESET_COMPLETED,
        user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        details={
            "user_email": user.email,
            "method": "token",
        },
    )
    await db.commit()

    # Blacklist all existing tokens for this user
    await blacklist_all_user_tokens(user.id)

    logger.info(f"Password reset for: {user.email}")

    return MessageResponse(
        message="Password successfully reset",
        detail="Please log in with your new password",
    )


async def blacklist_all_user_tokens(user_id: UUID):
    """Invalidate all tokens for a user (security measure after password reset)."""
    try:
        from app.core.cache import get_redis

        redis = await get_redis()

        # Store a "tokens invalidated at" timestamp
        key = f"user:{user_id}:tokens_invalidated_at"
        await redis.set(key, datetime.utcnow().isoformat(), ex=86400 * 30)  # 30 days

    except Exception as e:
        logger.warning(f"Failed to blacklist tokens for user {user_id}: {e}")


# =============================================================================
# Current User
# =============================================================================


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get authenticated user's profile.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Get current authenticated user's profile.
    """
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        display_name=current_user.display_name,
        role=current_user.role,
        status=current_user.status,
        created_at=current_user.created_at,
        email_verified_at=current_user.email_verified_at,
    )


# =============================================================================
# Development Endpoints (Non-Production Only)
# =============================================================================


class DevVerifyRequest(BaseModel):
    """Request to force-verify a user in development."""

    email: EmailStr


@router.post(
    "/dev/verify-user",
    status_code=status.HTTP_200_OK,
    summary="[DEV ONLY] Force verify a user",
    description="Development endpoint to force-verify a user. Disabled in production.",
    include_in_schema=False,  # Hide from OpenAPI docs
)
async def dev_verify_user(
    request: DevVerifyRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Force-verify a user for testing purposes.
    Only available when ENVIRONMENT is 'development' or 'test'.
    """
    if settings.ENVIRONMENT not in ("development", "test", "local"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )

    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(request.email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.status = "active"
    user.email_verified_at = datetime.utcnow()
    await db.commit()

    logger.info(f"[DEV] User force-verified: {user.email}")

    return {"message": f"User {user.email} verified successfully"}
