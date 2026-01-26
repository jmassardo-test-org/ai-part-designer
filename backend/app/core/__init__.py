"""
Core application package.

Contains configuration, database, caching, storage, security, and utilities.
"""

from app.core.config import settings, get_settings
from app.core.database import get_db, init_db, close_db, async_session_maker
from app.core.cache import redis_client, get_redis, RedisClient
from app.core.storage import storage_client, get_storage, StorageClient, StorageBucket
from app.core.events import event_tracker, get_event_tracker, EventTracker, EventCategory
from app.core.validation import DataValidator, Rules, ValidationResult, CADParameterValidator
from app.core.backup import db_backup, data_exporter, DatabaseBackup, DataExporter
from app.core.security import (
    hash_password,
    verify_password,
    check_password_strength,
    create_access_token,
    create_refresh_token,
    create_verification_token,
    decode_token,
    verify_token,
    TokenType,
    EncryptionService,
    generate_secure_token,
    generate_api_key,
    hash_api_key,
    create_hmac_signature,
    verify_hmac_signature,
    sanitize_filename,
    sanitize_html,
)
from app.core.auth import (
    get_current_user,
    get_current_user_optional,
    get_auth_context,
    require_permissions,
    require_role,
    require_admin,
    Role,
    Permission,
    AuthContext,
    CurrentUser,
    OptionalUser,
    Auth,
    blacklist_token,
    blacklist_all_user_tokens,
    ResourceAuthorizer,
)

__all__ = [
    # Config
    "settings",
    "get_settings",
    # Database
    "get_db",
    "init_db",
    "close_db",
    "async_session_maker",
    # Cache
    "redis_client",
    "get_redis",
    "RedisClient",
    # Storage
    "storage_client",
    "get_storage",
    "StorageClient",
    "StorageBucket",
    # Events
    "event_tracker",
    "get_event_tracker",
    "EventTracker",
    "EventCategory",
    # Validation
    "DataValidator",
    "Rules",
    "ValidationResult",
    "CADParameterValidator",
    # Backup
    "db_backup",
    "data_exporter",
    "DatabaseBackup",
    "DataExporter",
    # Security - Password
    "hash_password",
    "verify_password",
    "check_password_strength",
    # Security - Tokens
    "create_access_token",
    "create_refresh_token",
    "create_verification_token",
    "decode_token",
    "verify_token",
    "TokenType",
    # Security - Encryption
    "EncryptionService",
    # Security - Utilities
    "generate_secure_token",
    "generate_api_key",
    "hash_api_key",
    "create_hmac_signature",
    "verify_hmac_signature",
    "sanitize_filename",
    "sanitize_html",
    # Auth - Dependencies
    "get_current_user",
    "get_current_user_optional",
    "get_auth_context",
    "require_permissions",
    "require_role",
    "require_admin",
    # Auth - Types
    "Role",
    "Permission",
    "AuthContext",
    "CurrentUser",
    "OptionalUser",
    "Auth",
    # Auth - Token Management
    "blacklist_token",
    "blacklist_all_user_tokens",
    # Auth - Resource Authorization
    "ResourceAuthorizer",
]
