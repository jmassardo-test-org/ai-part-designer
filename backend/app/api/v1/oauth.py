"""
OAuth authentication endpoints.

Provides OAuth login and callback handlers for Google and GitHub.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.core.auth import get_current_user
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.oauth import fetch_github_user_info, fetch_google_user_info, oauth
from app.core.security import create_access_token, create_refresh_token, hash_password
from app.models import OAuthConnection, User
from app.repositories import UserRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/oauth", tags=["OAuth"])


# =============================================================================
# Request/Response Models
# =============================================================================


class OAuthLoginResponse(BaseModel):
    """OAuth login initiation response."""

    authorization_url: str
    state: str


class OAuthTokenResponse(BaseModel):
    """OAuth callback success response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    is_new_user: bool = False
    user: OAuthUserResponse


class OAuthUserResponse(BaseModel):
    """User info from OAuth response."""

    id: str
    email: str
    display_name: str
    provider: str

    class Config:
        from_attributes = True


class OAuthConnectionResponse(BaseModel):
    """OAuth connection info."""

    id: str
    provider: str
    provider_email: str | None
    provider_username: str | None
    connected_at: datetime


class OAuthConnectionsResponse(BaseModel):
    """List of OAuth connections."""

    connections: list[OAuthConnectionResponse]


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


# =============================================================================
# OAuth Login Initiation
# =============================================================================


@router.get(
    "/{provider}/login",
    response_model=OAuthLoginResponse,
    summary="Initiate OAuth login",
    description="Get authorization URL for OAuth provider login.",
)
async def oauth_login(
    request: Request,
    provider: Literal["google", "github"],
    redirect_uri: str | None = Query(None, description="Custom redirect URI after callback"),
    settings: Settings = Depends(get_settings),
) -> OAuthLoginResponse:
    """
    Initiate OAuth login flow.

    Returns the authorization URL to redirect the user to the OAuth provider.
    """
    # Validate provider is configured
    if provider == "google" and not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured",
        )
    if provider == "github" and not settings.GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth is not configured",
        )

    # Get the OAuth client
    client = oauth.create_client(provider)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown OAuth provider: {provider}",
        )

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)

    # Build callback URL
    callback_url = f"{settings.OAUTH_REDIRECT_BASE}/api/v1/auth/oauth/{provider}/callback"

    # Store state and optional redirect_uri in session
    request.session["oauth_state"] = state
    if redirect_uri:
        request.session["oauth_redirect"] = redirect_uri

    # Get authorization URL
    authorization_url = await client.create_authorization_url(
        callback_url,
        state=state,
    )

    return OAuthLoginResponse(
        authorization_url=authorization_url["url"],
        state=state,
    )


@router.get(
    "/{provider}/authorize",
    summary="Redirect to OAuth provider",
    description="Redirect user to OAuth provider for authentication.",
)
async def oauth_authorize(
    request: Request,
    provider: Literal["google", "github"],
    redirect_uri: str | None = Query(None, description="Custom redirect URI after callback"),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    """
    Redirect to OAuth provider for authentication.

    This is an alternative to the /login endpoint that directly redirects.
    """
    # Validate provider is configured
    if provider == "google" and not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured",
        )
    if provider == "github" and not settings.GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth is not configured",
        )

    # Get the OAuth client
    client = oauth.create_client(provider)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown OAuth provider: {provider}",
        )

    # Build callback URL
    callback_url = f"{settings.OAUTH_REDIRECT_BASE}/api/v1/auth/oauth/{provider}/callback"

    # Store optional redirect_uri in session
    if redirect_uri:
        request.session["oauth_redirect"] = redirect_uri

    # Redirect to OAuth provider
    return await client.authorize_redirect(request, callback_url)


# =============================================================================
# OAuth Callback
# =============================================================================


@router.get(
    "/{provider}/callback",
    summary="OAuth callback handler",
    description="Handle OAuth provider callback and authenticate user.",
)
async def oauth_callback(
    request: Request,
    provider: Literal["google", "github"],
    code: str = Query(..., description="Authorization code from OAuth provider"),
    state: str | None = Query(None, description="CSRF state parameter"),
    error: str | None = Query(None, description="Error from OAuth provider"),
    error_description: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    """
    Handle OAuth callback from provider.

    - Exchanges authorization code for tokens
    - Fetches user info from provider
    - Creates or updates user account
    - Links OAuth connection
    - Generates JWT tokens
    - Redirects to frontend with tokens
    """
    # Handle OAuth errors
    if error:
        logger.warning(f"OAuth error from {provider}: {error} - {error_description}")
        redirect_url = request.session.pop("oauth_redirect", settings.FRONTEND_URL)
        return RedirectResponse(
            url=f"{redirect_url}?error=oauth_error&message={error_description or error}"
        )

    # Validate state (CSRF protection)
    stored_state = request.session.pop("oauth_state", None)
    if stored_state and state != stored_state:
        logger.warning(f"OAuth state mismatch for {provider}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state - possible CSRF attack",
        )

    try:
        # Get the OAuth client
        client = oauth.create_client(provider)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown OAuth provider: {provider}",
            )

        # Build callback URL for token exchange

        # Exchange code for tokens
        token = await client.authorize_access_token(request)

        # Fetch user info from provider
        if provider == "google":
            user_info = await fetch_google_user_info(token)
        elif provider == "github":
            user_info = await fetch_github_user_info(token)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported provider: {provider}",
            )

        if not user_info or not user_info.get("email"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not get email from OAuth provider",
            )

        # Find or create user
        user_repo = UserRepository(db)
        email = user_info["email"].lower()
        provider_user_id = str(user_info["id"])
        is_new_user = False
        user: User | None = None

        # First, check if OAuth connection exists
        oauth_conn = await db.execute(
            select(OAuthConnection).where(
                OAuthConnection.provider == provider,
                OAuthConnection.provider_user_id == provider_user_id,
            )
        )
        existing_connection = oauth_conn.scalar_one_or_none()

        if existing_connection:
            # User already linked this OAuth - get the user
            user = await user_repo.get_by_id(existing_connection.user_id)
            if not user:
                # Orphaned connection - remove it
                await db.delete(existing_connection)
                await db.commit()
                existing_connection = None

        if not existing_connection or not user:
            # Check if user exists by email
            user = await user_repo.get_by_email(email)

            if not user:
                # Create new user
                is_new_user = True
                user = User(
                    email=email,
                    password_hash=hash_password(secrets.token_urlsafe(32)),
                    display_name=user_info.get("name", email.split("@")[0]),
                    role="user",
                    status="active",  # OAuth users are pre-verified
                    email_verified_at=datetime.utcnow(),
                )
                db.add(user)
                await db.flush()

            # Create OAuth connection
            oauth_connection = OAuthConnection(
                user_id=user.id,
                provider=provider,
                provider_user_id=provider_user_id,
                provider_email=email,
                provider_username=user_info.get("username"),
                access_token=token.get("access_token"),
                refresh_token=token.get("refresh_token"),
                token_expires_at=(
                    datetime.utcnow() + timedelta(seconds=token["expires_in"])
                    if token.get("expires_in")
                    else None
                ),
                profile_data=user_info,
                last_used_at=datetime.utcnow(),
            )
            db.add(oauth_connection)
        else:
            # Update existing connection
            existing_connection.access_token = token.get("access_token")
            existing_connection.refresh_token = token.get(
                "refresh_token", existing_connection.refresh_token
            )
            if token.get("expires_in"):
                existing_connection.token_expires_at = datetime.utcnow() + timedelta(
                    seconds=token["expires_in"]
                )
            existing_connection.profile_data = user_info
            existing_connection.last_used_at = datetime.utcnow()

        # Update user last login
        user.last_login_at = datetime.utcnow()
        await db.commit()

        # Generate JWT tokens
        access_token = create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role,
        )
        refresh_token_str, _ = create_refresh_token(user_id=user.id)

        # Get redirect URL
        redirect_url = request.session.pop("oauth_redirect", settings.FRONTEND_URL)

        # Redirect to frontend with tokens
        return RedirectResponse(
            url=(
                f"{redirect_url}?access_token={access_token}"
                f"&refresh_token={refresh_token_str}"
                f"&is_new_user={str(is_new_user).lower()}"
            )
        )

    except Exception:
        logger.exception(f"OAuth callback error for {provider}")
        redirect_url = request.session.pop("oauth_redirect", settings.FRONTEND_URL)
        return RedirectResponse(
            url=f"{redirect_url}?error=server_error&message=Authentication failed"
        )


# =============================================================================
# OAuth Connection Management
# =============================================================================


@router.get(
    "/connections",
    response_model=OAuthConnectionsResponse,
    summary="List OAuth connections",
    description="Get list of linked OAuth provider accounts.",
)
async def list_oauth_connections(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OAuthConnectionsResponse:
    """List all OAuth connections for the current user."""
    result = await db.execute(
        select(OAuthConnection).where(OAuthConnection.user_id == current_user.id)
    )
    connections = result.scalars().all()

    return OAuthConnectionsResponse(
        connections=[
            OAuthConnectionResponse(
                id=str(conn.id),
                provider=conn.provider,
                provider_email=conn.provider_email,
                provider_username=conn.provider_username,
                connected_at=conn.created_at,
            )
            for conn in connections
        ]
    )


@router.post(
    "/link/{provider}",
    response_model=OAuthLoginResponse,
    summary="Link OAuth provider",
    description="Initiate OAuth flow to link a new provider to existing account.",
)
async def link_oauth_provider(
    request: Request,
    provider: Literal["google", "github"],
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> OAuthLoginResponse:
    """
    Initiate OAuth flow to link a provider to the current user's account.
    """
    # Validate provider is configured
    if provider == "google" and not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured",
        )
    if provider == "github" and not settings.GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth is not configured",
        )

    # Get the OAuth client
    client = oauth.create_client(provider)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown OAuth provider: {provider}",
        )

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)

    # Build callback URL for linking
    callback_url = f"{settings.OAUTH_REDIRECT_BASE}/api/v1/auth/oauth/link/{provider}/callback"

    # Store state and user ID in session for linking
    request.session["oauth_state"] = state
    request.session["oauth_link_user_id"] = str(current_user.id)

    # Get authorization URL
    authorization_url = await client.create_authorization_url(
        callback_url,
        state=state,
    )

    return OAuthLoginResponse(
        authorization_url=authorization_url["url"],
        state=state,
    )


@router.get(
    "/link/{provider}/callback",
    summary="OAuth link callback",
    description="Handle OAuth callback for account linking.",
)
async def link_oauth_callback(
    request: Request,
    provider: Literal["google", "github"],
    code: str = Query(...),
    state: str | None = Query(None),
    error: str | None = Query(None),
    error_description: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    """Handle OAuth callback for linking provider to existing account."""
    # Get user ID from session
    user_id = request.session.pop("oauth_link_user_id", None)
    if not user_id:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/settings?error=session_expired")

    # Handle OAuth errors
    if error:
        logger.warning(f"OAuth link error from {provider}: {error}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings?error=oauth_error&message={error_description or error}"
        )

    # Validate state
    stored_state = request.session.pop("oauth_state", None)
    if stored_state and state != stored_state:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/settings?error=invalid_state")

    try:
        # Get the OAuth client
        client = oauth.create_client(provider)

        # Exchange code for tokens
        token = await client.authorize_access_token(request)

        # Fetch user info
        if provider == "google":
            user_info = await fetch_google_user_info(token)
        else:
            user_info = await fetch_github_user_info(token)

        if not user_info:
            return RedirectResponse(url=f"{settings.FRONTEND_URL}/settings?error=no_user_info")

        provider_user_id = str(user_info["id"])

        # Check if this OAuth account is already linked to another user
        existing = await db.execute(
            select(OAuthConnection).where(
                OAuthConnection.provider == provider,
                OAuthConnection.provider_user_id == provider_user_id,
            )
        )
        existing_conn = existing.scalar_one_or_none()

        if existing_conn and str(existing_conn.user_id) != user_id:
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/settings?error=already_linked&message=This {provider} account is linked to another user"
            )

        if existing_conn:
            # Already linked to this user - update tokens
            existing_conn.access_token = token.get("access_token")
            existing_conn.refresh_token = token.get("refresh_token", existing_conn.refresh_token)
            existing_conn.last_used_at = datetime.utcnow()
        else:
            # Create new connection
            oauth_connection = OAuthConnection(
                user_id=user_id,
                provider=provider,
                provider_user_id=provider_user_id,
                provider_email=user_info.get("email"),
                provider_username=user_info.get("username"),
                access_token=token.get("access_token"),
                refresh_token=token.get("refresh_token"),
                token_expires_at=(
                    datetime.utcnow() + timedelta(seconds=token["expires_in"])
                    if token.get("expires_in")
                    else None
                ),
                profile_data=user_info,
                last_used_at=datetime.utcnow(),
            )
            db.add(oauth_connection)

        await db.commit()

        return RedirectResponse(url=f"{settings.FRONTEND_URL}/settings?oauth_linked={provider}")

    except Exception:
        logger.exception(f"OAuth link callback error for {provider}")
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/settings?error=link_failed")


@router.delete(
    "/connections/{provider}",
    response_model=MessageResponse,
    summary="Unlink OAuth provider",
    description="Remove linked OAuth provider from account.",
)
async def unlink_oauth_provider(
    provider: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Remove OAuth provider connection from user account."""
    # Find the connection
    result = await db.execute(
        select(OAuthConnection).where(
            OAuthConnection.user_id == current_user.id,
            OAuthConnection.provider == provider,
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {provider} connection found",
        )

    # Check if user has a password or other OAuth connections
    other_connections = await db.execute(
        select(OAuthConnection).where(
            OAuthConnection.user_id == current_user.id,
            OAuthConnection.provider != provider,
        )
    )
    has_other_oauth = other_connections.scalar_one_or_none() is not None

    # If no password and no other OAuth, don't allow unlinking
    if not current_user.password_hash and not has_other_oauth:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot unlink last authentication method. Set a password first.",
        )

    await db.delete(connection)
    await db.commit()

    return MessageResponse(message=f"Successfully unlinked {provider} account")
