"""
Core application package.

Contains configuration, database, caching, storage, security, and utilities.
"""

from app.core.auth import (
    Auth,
    AuthContext,
    CurrentUser,
    OptionalUser,
    Permission,
    ResourceAuthorizer,
    Role,
    blacklist_all_user_tokens,
    blacklist_token,
    get_auth_context,
    get_current_user,
    get_current_user_optional,
    require_admin,
    require_permissions,
    require_role,
)
from app.core.backup import DatabaseBackup, DataExporter, data_exporter, db_backup
from app.core.cache import RedisClient, get_redis, redis_client
from app.core.config import get_settings, settings
from app.core.database import async_session_maker, close_db, get_db, init_db
from app.core.events import EventCategory, EventTracker, event_tracker, get_event_tracker
from app.core.security import (
    EncryptionService,
    TokenType,
    check_password_strength,
    create_access_token,
    create_hmac_signature,
    create_refresh_token,
    create_verification_token,
    decode_token,
    generate_api_key,
    generate_secure_token,
    hash_api_key,
    hash_password,
    sanitize_filename,
    sanitize_html,
    verify_hmac_signature,
    verify_password,
    verify_token,
)
from app.core.storage import StorageBucket, StorageClient, get_storage, storage_client
from app.core.validation import CADParameterValidator, DataValidator, Rules, ValidationResult

__all__ = [
    "Auth",
    "AuthContext",
    "CADParameterValidator",
    "CurrentUser",
    "DataExporter",
    # Validation
    "DataValidator",
    "DatabaseBackup",
    # Security - Encryption
    "EncryptionService",
    "EventCategory",
    "EventTracker",
    "OptionalUser",
    "Permission",
    "RedisClient",
    # Auth - Resource Authorization
    "ResourceAuthorizer",
    # Auth - Types
    "Role",
    "Rules",
    "StorageBucket",
    "StorageClient",
    "TokenType",
    "ValidationResult",
    "async_session_maker",
    "blacklist_all_user_tokens",
    # Auth - Token Management
    "blacklist_token",
    "check_password_strength",
    "close_db",
    # Security - Tokens
    "create_access_token",
    "create_hmac_signature",
    "create_refresh_token",
    "create_verification_token",
    "data_exporter",
    # Backup
    "db_backup",
    "decode_token",
    # Events
    "event_tracker",
    "generate_api_key",
    # Security - Utilities
    "generate_secure_token",
    "get_auth_context",
    # Auth - Dependencies
    "get_current_user",
    "get_current_user_optional",
    # Database
    "get_db",
    "get_event_tracker",
    "get_redis",
    "get_settings",
    "get_storage",
    "hash_api_key",
    # Security - Password
    "hash_password",
    "init_db",
    # Cache
    "redis_client",
    "require_admin",
    "require_permissions",
    "require_role",
    "sanitize_filename",
    "sanitize_html",
    # Config
    "settings",
    # Storage
    "storage_client",
    "verify_hmac_signature",
    "verify_password",
    "verify_token",
]
