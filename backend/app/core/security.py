"""
Security utilities and cryptographic functions.

Provides:
- Password hashing and verification
- Token generation and validation
- Encryption/decryption for sensitive data
- Secure random generation
"""

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from uuid import UUID

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# =============================================================================
# Password Hashing
# =============================================================================

# bcrypt with automatic salt, cost factor 12
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Stored hash to compare against

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def check_password_strength(password: str) -> dict:
    """
    Check password strength and return validation result.

    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character

    Returns:
        Dict with is_valid and list of issues
    """
    issues = []

    if len(password) < 8:
        issues.append("Password must be at least 8 characters long")
    if len(password) > 128:
        issues.append("Password must not exceed 128 characters")
    if not any(c.isupper() for c in password):
        issues.append("Password must contain at least one uppercase letter")
    if not any(c.islower() for c in password):
        issues.append("Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in password):
        issues.append("Password must contain at least one digit")
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        issues.append("Password must contain at least one special character")

    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
        "strength": _calculate_password_strength(password),
    }


def _calculate_password_strength(password: str) -> str:
    """Calculate password strength score."""
    score = 0

    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    if len(password) >= 16:
        score += 1
    if any(c.isupper() for c in password):
        score += 1
    if any(c.islower() for c in password):
        score += 1
    if any(c.isdigit() for c in password):
        score += 1
    if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        score += 1

    if score <= 3:
        return "weak"
    if score <= 5:
        return "medium"
    return "strong"


# =============================================================================
# JWT Token Management
# =============================================================================


class TokenType:
    ACCESS = "access"
    REFRESH = "refresh"
    VERIFICATION = "verification"
    PASSWORD_RESET = "password_reset"


def create_access_token(
    user_id: UUID,
    email: str,
    role: str = "user",
    tier: str = "free",
    expires_delta: timedelta | None = None,
    additional_claims: dict | None = None,
) -> str:
    """
    Create a short-lived access token.

    Args:
        user_id: User's UUID
        email: User's email address
        role: User's role (user, admin, etc.)
        tier: User's subscription tier
        expires_delta: Custom expiration time
        additional_claims: Extra claims to include

    Returns:
        Encoded JWT string
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(tz=datetime.UTC)
    expire = now + expires_delta

    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "tier": tier,
        "type": TokenType.ACCESS,
        "iat": now,
        "exp": expire,
        "jti": secrets.token_urlsafe(16),  # Unique token ID
    }

    if additional_claims:
        payload.update(additional_claims)

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    user_id: UUID,
    expires_delta: timedelta | None = None,
) -> tuple[str, str]:
    """
    Create a long-lived refresh token.

    Args:
        user_id: User's UUID
        expires_delta: Custom expiration time

    Returns:
        Tuple of (encoded_token, token_jti)
    """
    if expires_delta is None:
        expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    now = datetime.now(tz=datetime.UTC)
    expire = now + expires_delta
    jti = secrets.token_urlsafe(32)

    payload = {
        "sub": str(user_id),
        "type": TokenType.REFRESH,
        "iat": now,
        "exp": expire,
        "jti": jti,
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, jti


def create_verification_token(
    user_id: UUID,
    purpose: str = "email_verification",
    expires_hours: int = 24,
) -> str:
    """
    Create a verification token for email verification or password reset.

    Args:
        user_id: User's UUID
        purpose: Token purpose (email_verification, password_reset)
        expires_hours: Hours until expiration

    Returns:
        Encoded JWT string
    """
    now = datetime.now(tz=datetime.UTC)
    expire = now + timedelta(hours=expires_hours)

    payload = {
        "sub": str(user_id),
        "type": purpose,
        "iat": now,
        "exp": expire,
        "jti": secrets.token_urlsafe(16),
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict | None:
    """
    Decode and validate a JWT token.

    Args:
        token: Encoded JWT string

    Returns:
        Token payload dict or None if invalid
    """
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        return None


def verify_token(token: str, expected_type: str | None = None) -> dict | None:
    """
    Verify a token and optionally check its type.

    Args:
        token: Encoded JWT string
        expected_type: Expected token type (access, refresh, etc.)

    Returns:
        Token payload if valid, None otherwise
    """
    payload = decode_token(token)

    if payload is None:
        return None

    # Check expiration
    exp = payload.get("exp")
    if exp and datetime.fromtimestamp(exp, tz=datetime.UTC) < datetime.now(tz=datetime.UTC):
        return None

    # Check type if specified
    if expected_type and payload.get("type") != expected_type:
        return None

    return payload


# =============================================================================
# Data Encryption
# =============================================================================


class EncryptionService:
    """
    Fernet-based encryption for sensitive data at rest.

    Uses a key derived from SECRET_KEY for encryption.
    Suitable for encrypting PII, API keys, and other sensitive data.
    """

    def __init__(self, key: str | None = None):
        key = key or settings.SECRET_KEY
        # Derive a Fernet-compatible key from the secret
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"ai-part-designer-salt",  # Static salt for key derivation
            iterations=100000,
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
        self._fernet = Fernet(derived_key)

    def encrypt(self, data: str) -> str:
        """
        Encrypt a string.

        Args:
            data: Plain text string to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        encrypted = self._fernet.encrypt(data.encode())
        return encrypted.decode()

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt an encrypted string.

        Args:
            encrypted_data: Base64-encoded encrypted string

        Returns:
            Decrypted plain text string
        """
        decrypted = self._fernet.decrypt(encrypted_data.encode())
        return decrypted.decode()

    def encrypt_dict(self, data: dict) -> str:
        """Encrypt a dictionary as JSON."""
        import json

        return self.encrypt(json.dumps(data))

    def decrypt_dict(self, encrypted_data: str) -> dict:
        """Decrypt to a dictionary."""
        import json

        return json.loads(self.decrypt(encrypted_data))


# Global encryption service instance
encryption_service = EncryptionService()


# =============================================================================
# Secure Random Generation
# =============================================================================


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)


def generate_verification_code(length: int = 6) -> str:
    """Generate a numeric verification code."""
    return "".join(secrets.choice("0123456789") for _ in range(length))


def generate_api_key() -> tuple[str, str]:
    """
    Generate an API key and its hash.

    Returns:
        Tuple of (raw_key, key_hash)
    """
    raw_key = f"apd_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, key_hash


def hash_api_key(raw_key: str) -> str:
    """
    Hash an API key for storage/comparison.

    Args:
        raw_key: The raw API key string

    Returns:
        SHA-256 hash of the key
    """
    return hashlib.sha256(raw_key.encode()).hexdigest()


# =============================================================================
# HMAC Signatures
# =============================================================================


def create_hmac_signature(data: str, key: str | None = None) -> str:
    """
    Create an HMAC-SHA256 signature.

    Args:
        data: Data to sign
        key: Secret key (defaults to settings.SECRET_KEY)

    Returns:
        Hex-encoded signature
    """
    key = key or settings.SECRET_KEY
    return hmac.new(
        key.encode(),
        data.encode(),
        hashlib.sha256,
    ).hexdigest()


def verify_hmac_signature(data: str, signature: str, key: str | None = None) -> bool:
    """
    Verify an HMAC-SHA256 signature.

    Args:
        data: Original data
        signature: Signature to verify
        key: Secret key (defaults to settings.SECRET_KEY)

    Returns:
        True if signature is valid
    """
    expected = create_hmac_signature(data, key)
    return hmac.compare_digest(signature, expected)


# =============================================================================
# Input Sanitization
# =============================================================================


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal attacks.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    import re
    from pathlib import Path

    # Get just the filename, no path
    filename = Path(filename).name

    # Remove null bytes and control characters
    filename = re.sub(r"[\x00-\x1f\x7f]", "", filename)

    # Replace dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)

    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        filename = f"{name[:250]}.{ext}" if ext else name[:255]

    return filename or "unnamed"


def sanitize_html(html: str) -> str:
    """
    Sanitize HTML content to prevent XSS attacks.

    Args:
        html: HTML string to sanitize

    Returns:
        Sanitized HTML string
    """
    import html as html_module

    return html_module.escape(html)
