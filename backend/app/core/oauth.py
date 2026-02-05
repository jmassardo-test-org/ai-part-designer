"""
OAuth integration module.

Provides OAuth 2.0 authentication for Google and GitHub providers
using the authlib library.
"""

import logging
from typing import Any

from authlib.integrations.starlette_client import OAuth, OAuthError
from starlette.requests import Request

from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize OAuth client
oauth = OAuth()

# =============================
# Provider Registration
# =============================

# Google OAuth 2.0
if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
    oauth.register(
        name="google",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={
            "scope": "openid email profile",
        },
    )
    logger.info("Google OAuth provider registered")
else:
    logger.warning("Google OAuth not configured (missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET)")

# GitHub OAuth 2.0
if settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET:
    oauth.register(
        name="github",
        client_id=settings.GITHUB_CLIENT_ID,
        client_secret=settings.GITHUB_CLIENT_SECRET,
        authorize_url="https://github.com/login/oauth/authorize",
        access_token_url="https://github.com/login/oauth/access_token",
        api_base_url="https://api.github.com/",
        client_kwargs={
            "scope": "user:email read:user",
        },
    )
    logger.info("GitHub OAuth provider registered")
else:
    logger.warning("GitHub OAuth not configured (missing GITHUB_CLIENT_ID or GITHUB_CLIENT_SECRET)")


# =============================
# OAuth Helper Functions
# =============================


def get_oauth_client(provider: str):
    """
    Get the OAuth client for a provider.

    Args:
        provider: Provider name ('google' or 'github')

    Returns:
        OAuth client instance

    Raises:
        ValueError: If provider is not configured
    """
    client = oauth.create_client(provider)
    if client is None:
        raise ValueError(f"OAuth provider '{provider}' is not configured")
    return client


async def get_oauth_redirect_uri(request: Request, provider: str) -> str:
    """
    Generate the OAuth callback URI.

    Args:
        request: The incoming request
        provider: Provider name

    Returns:
        Full callback URL
    """
    # Use configured redirect base or construct from request
    base_url = settings.OAUTH_REDIRECT_BASE
    return f"{base_url}/api/v1/auth/oauth/{provider}/callback"


async def fetch_google_user_info(token: dict) -> dict[str, Any]:
    """
    Fetch user information from Google.

    Args:
        token: OAuth access token dict

    Returns:
        User info dict with id, email, name, picture
    """
    client = get_oauth_client("google")

    # Use userinfo endpoint
    resp = await client.get("https://openidconnect.googleapis.com/v1/userinfo", token=token)
    user_info = resp.json()

    return {
        "provider": "google",
        "provider_user_id": user_info.get("sub"),
        "email": user_info.get("email"),
        "email_verified": user_info.get("email_verified", False),
        "name": user_info.get("name"),
        "picture": user_info.get("picture"),
    }


async def fetch_github_user_info(token: dict) -> dict[str, Any]:
    """
    Fetch user information from GitHub.

    Args:
        token: OAuth access token dict

    Returns:
        User info dict with id, email, name, picture
    """
    client = get_oauth_client("github")

    # Fetch user profile
    resp = await client.get("user", token=token)
    user_info = resp.json()

    # GitHub may not return email in profile, need to fetch separately
    email = user_info.get("email")
    if not email:
        # Fetch emails endpoint
        emails_resp = await client.get("user/emails", token=token)
        emails = emails_resp.json()

        # Get primary verified email
        for e in emails:
            if e.get("primary") and e.get("verified"):
                email = e.get("email")
                break

        # Fallback to any verified email
        if not email:
            for e in emails:
                if e.get("verified"):
                    email = e.get("email")
                    break

    return {
        "provider": "github",
        "provider_user_id": str(user_info.get("id")),
        "email": email,
        "email_verified": True,  # GitHub only returns verified emails
        "name": user_info.get("name") or user_info.get("login"),
        "picture": user_info.get("avatar_url"),
        "username": user_info.get("login"),
    }


async def fetch_user_info(provider: str, token: dict) -> dict[str, Any]:
    """
    Fetch user information from an OAuth provider.

    Args:
        provider: Provider name
        token: OAuth access token dict

    Returns:
        Normalized user info dict
    """
    if provider == "google":
        return await fetch_google_user_info(token)
    if provider == "github":
        return await fetch_github_user_info(token)
    raise ValueError(f"Unknown OAuth provider: {provider}")


def is_provider_configured(provider: str) -> bool:
    """Check if an OAuth provider is configured."""
    if provider == "google":
        return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)
    if provider == "github":
        return bool(settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET)
    return False


def get_configured_providers() -> list[str]:
    """Get list of configured OAuth providers."""
    providers = []
    if is_provider_configured("google"):
        providers.append("google")
    if is_provider_configured("github"):
        providers.append("github")
    return providers


# Re-export for convenience
__all__ = [
    "OAuthError",
    "fetch_user_info",
    "get_configured_providers",
    "get_oauth_client",
    "get_oauth_redirect_uri",
    "is_provider_configured",
    "oauth",
]
