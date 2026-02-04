"""
Authentication and authorization middleware and dependencies.

Provides:
- JWT token validation
- User authentication
- Role-based access control (RBAC)
- Permission checking
- Rate limiting integration
"""

from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Annotated, Callable
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_token, TokenType
from app.core.cache import redis_client
from app.models import User
from app.repositories import UserRepository

# =============================================================================
# Security Scheme
# =============================================================================

bearer_scheme = HTTPBearer(
    scheme_name="JWT",
    description="Enter your JWT access token",
    auto_error=False,
)


# =============================================================================
# User Roles and Permissions
# =============================================================================

class Role(str, Enum):
    """User roles with hierarchical permissions."""
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class Permission(str, Enum):
    """Granular permissions for RBAC."""
    # Design permissions
    DESIGN_CREATE = "design:create"
    DESIGN_READ = "design:read"
    DESIGN_UPDATE = "design:update"
    DESIGN_DELETE = "design:delete"
    DESIGN_SHARE = "design:share"
    DESIGN_EXPORT = "design:export"
    
    # Project permissions
    PROJECT_CREATE = "project:create"
    PROJECT_READ = "project:read"
    PROJECT_UPDATE = "project:update"
    PROJECT_DELETE = "project:delete"
    
    # Template permissions
    TEMPLATE_READ = "template:read"
    TEMPLATE_CREATE = "template:create"
    TEMPLATE_UPDATE = "template:update"
    TEMPLATE_DELETE = "template:delete"
    
    # Job permissions
    JOB_CREATE = "job:create"
    JOB_READ = "job:read"
    JOB_CANCEL = "job:cancel"
    
    # Admin permissions
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_IMPERSONATE = "user:impersonate"
    
    MODERATION_READ = "moderation:read"
    MODERATION_ACTION = "moderation:action"
    
    SYSTEM_ADMIN = "system:admin"
    AUDIT_READ = "audit:read"


# Role-Permission mapping
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.USER: {
        Permission.DESIGN_CREATE,
        Permission.DESIGN_READ,
        Permission.DESIGN_UPDATE,
        Permission.DESIGN_DELETE,
        Permission.DESIGN_SHARE,
        Permission.DESIGN_EXPORT,
        Permission.PROJECT_CREATE,
        Permission.PROJECT_READ,
        Permission.PROJECT_UPDATE,
        Permission.PROJECT_DELETE,
        Permission.TEMPLATE_READ,
        Permission.JOB_CREATE,
        Permission.JOB_READ,
        Permission.JOB_CANCEL,
    },
    Role.MODERATOR: {
        # Inherits all user permissions plus:
        Permission.MODERATION_READ,
        Permission.MODERATION_ACTION,
        Permission.USER_READ,
    },
    Role.ADMIN: {
        # Inherits all moderator permissions plus:
        Permission.TEMPLATE_CREATE,
        Permission.TEMPLATE_UPDATE,
        Permission.TEMPLATE_DELETE,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
        Permission.AUDIT_READ,
    },
    Role.SUPER_ADMIN: {
        # All permissions
        Permission.SYSTEM_ADMIN,
        Permission.USER_IMPERSONATE,
    },
}


def get_role_permissions(role: Role) -> set[Permission]:
    """Get all permissions for a role, including inherited ones."""
    permissions = set()
    
    role_hierarchy = [Role.USER, Role.MODERATOR, Role.ADMIN, Role.SUPER_ADMIN]
    role_index = role_hierarchy.index(role)
    
    for r in role_hierarchy[:role_index + 1]:
        permissions.update(ROLE_PERMISSIONS.get(r, set()))
    
    return permissions


# =============================================================================
# Authentication Context
# =============================================================================

class AuthContext:
    """
    Authentication context for the current request.
    
    Contains the authenticated user and their permissions.
    """
    
    def __init__(
        self,
        user: User,
        token_payload: dict,
        permissions: set[Permission],
    ):
        self.user = user
        self.user_id = user.id
        self.email = user.email
        self.role = Role(user.role)
        self.tier = token_payload.get("tier", "free")
        self.permissions = permissions
        self.token_payload = token_payload
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions
    
    def has_any_permission(self, *permissions: Permission) -> bool:
        """Check if user has any of the specified permissions."""
        return any(p in self.permissions for p in permissions)
    
    def has_all_permissions(self, *permissions: Permission) -> bool:
        """Check if user has all of the specified permissions."""
        return all(p in self.permissions for p in permissions)
    
    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.role in (Role.ADMIN, Role.SUPER_ADMIN)
    
    def is_owner_or_admin(self, owner_id: UUID) -> bool:
        """Check if user is the owner or an admin."""
        return self.user_id == owner_id or self.is_admin()


# =============================================================================
# Authentication Dependencies
# =============================================================================

async def get_token_payload(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict | None:
    """Extract and validate JWT token from request."""
    if credentials is None:
        return None
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None:
        return None
    
    # Check token type
    if payload.get("type") != TokenType.ACCESS:
        return None
    
    # Check expiration
    exp = payload.get("exp")
    if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
        return None
    
    # Check if token is blacklisted
    jti = payload.get("jti")
    if jti:
        is_blacklisted = await redis_client.exists(f"blacklist:token:{jti}")
        if is_blacklisted:
            return None
    
    return payload


async def get_current_user(
    token_payload: dict | None = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get the current authenticated user.
    
    Raises HTTPException if not authenticated.
    """
    if token_payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = token_payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    user_repo = UserRepository(db)
    # Eagerly load subscription to access tier property without N+1 queries
    user = await user_repo.get_by_id(UUID(user_id), load_relations=["subscription"])
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user.status}",
        )
    
    return user


async def get_current_user_optional(
    token_payload: dict | None = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Get current user if authenticated, None otherwise."""
    if token_payload is None:
        return None
    
    try:
        return await get_current_user(token_payload, db)
    except HTTPException:
        return None


async def get_auth_context(
    user: User = Depends(get_current_user),
    token_payload: dict = Depends(get_token_payload),
) -> AuthContext:
    """Get full authentication context for the current user."""
    role = Role(user.role)
    permissions = get_role_permissions(role)
    
    return AuthContext(
        user=user,
        token_payload=token_payload,
        permissions=permissions,
    )


# =============================================================================
# Permission Decorators and Dependencies
# =============================================================================

def require_permissions(*required_permissions: Permission):
    """
    Dependency factory that requires specific permissions.
    
    Usage:
        @router.get("/admin/users")
        async def list_users(
            auth: AuthContext = Depends(require_permissions(Permission.USER_READ))
        ):
            ...
    """
    async def permission_checker(
        auth: AuthContext = Depends(get_auth_context),
    ) -> AuthContext:
        if not auth.has_all_permissions(*required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return auth
    
    return permission_checker


def require_any_permission(*required_permissions: Permission):
    """Require at least one of the specified permissions."""
    async def permission_checker(
        auth: AuthContext = Depends(get_auth_context),
    ) -> AuthContext:
        if not auth.has_any_permission(*required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return auth
    
    return permission_checker


def require_role(*allowed_roles: Role):
    """
    Dependency factory that requires specific roles.
    
    Usage:
        @router.delete("/users/{user_id}")
        async def delete_user(
            auth: AuthContext = Depends(require_role(Role.ADMIN, Role.SUPER_ADMIN))
        ):
            ...
    """
    async def role_checker(
        auth: AuthContext = Depends(get_auth_context),
    ) -> AuthContext:
        if auth.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {', '.join(r.value for r in allowed_roles)}",
            )
        return auth
    
    return role_checker


def require_admin():
    """Shortcut for requiring admin role."""
    return require_role(Role.ADMIN, Role.SUPER_ADMIN)


# =============================================================================
# Resource Authorization
# =============================================================================

class ResourceAuthorizer:
    """
    Authorize access to specific resources.
    
    Checks ownership and sharing permissions for designs, projects, etc.
    """
    
    @staticmethod
    async def authorize_design_access(
        design_id: UUID,
        user_id: UUID,
        required_permission: str = "read",
        db: AsyncSession = None,
    ) -> bool:
        """
        Check if user can access a design.
        
        Args:
            design_id: Design to check
            user_id: User requesting access
            required_permission: read, write, or admin
            db: Database session
            
        Returns:
            True if authorized
        """
        from app.models import Design, DesignShare
        from sqlalchemy import select, or_
        
        # Check if user owns the design
        result = await db.execute(
            select(Design)
            .where(Design.id == design_id)
            .where(Design.deleted_at.is_(None))
        )
        design = result.scalar_one_or_none()
        
        if design is None:
            return False
        
        # Owner has full access
        if design.project.user_id == user_id:
            return True
        
        # Check if design is public (read only)
        if design.is_public and required_permission == "read":
            return True
        
        # Check sharing permissions
        permission_hierarchy = {"read": 0, "write": 1, "admin": 2}
        required_level = permission_hierarchy.get(required_permission, 0)
        
        result = await db.execute(
            select(DesignShare)
            .where(DesignShare.design_id == design_id)
            .where(DesignShare.shared_with_user_id == user_id)
        )
        share = result.scalar_one_or_none()
        
        if share:
            share_level = permission_hierarchy.get(share.permission, 0)
            if share_level >= required_level:
                return True
        
        return False

    @staticmethod
    async def authorize_project_access(
        project_id: UUID,
        user_id: UUID,
        db: AsyncSession = None,
    ) -> bool:
        """Check if user owns a project."""
        from app.models import Project
        from sqlalchemy import select
        
        result = await db.execute(
            select(Project)
            .where(Project.id == project_id)
            .where(Project.user_id == user_id)
            .where(Project.deleted_at.is_(None))
        )
        return result.scalar_one_or_none() is not None


# =============================================================================
# Token Blacklisting
# =============================================================================

async def blacklist_token(jti: str, expires_in: int = 86400) -> None:
    """
    Add a token to the blacklist.
    
    Args:
        jti: Token's unique identifier
        expires_in: Seconds until blacklist entry expires
    """
    await redis_client.set(
        f"blacklist:token:{jti}",
        "1",
        ttl=expires_in,
    )


async def blacklist_all_user_tokens(user_id: UUID) -> None:
    """
    Invalidate all tokens for a user.
    
    Used when password is changed or account is compromised.
    """
    # Store a timestamp; tokens issued before this are invalid
    await redis_client.set(
        f"user:token_invalidation:{user_id}",
        str(datetime.utcnow().timestamp()),
        ttl=86400 * 30,  # 30 days
    )


async def is_token_valid_for_user(user_id: UUID, issued_at: float) -> bool:
    """Check if a token is still valid based on invalidation timestamp."""
    invalidation_time = await redis_client.get(f"user:token_invalidation:{user_id}")
    
    if invalidation_time is None:
        return True
    
    return issued_at > float(invalidation_time)


# =============================================================================
# Rate Limiting
# =============================================================================

async def check_rate_limit(
    request: Request,
    key_prefix: str = "api",
    max_requests: int | None = None,
    window_seconds: int = 60,
) -> tuple[bool, dict]:
    """
    Check rate limit for a request.
    
    Args:
        request: FastAPI request
        key_prefix: Prefix for rate limit key
        max_requests: Max requests per window (default from settings)
        window_seconds: Time window in seconds
        
    Returns:
        Tuple of (is_allowed, rate_limit_info)
    """
    if not settings.RATE_LIMIT_ENABLED:
        return True, {}
    
    max_requests = max_requests or settings.RATE_LIMIT_PER_MINUTE
    
    # Build rate limit key
    client_ip = request.client.host if request.client else "unknown"
    key = f"ratelimit:{key_prefix}:{client_ip}:{window_seconds}"
    
    is_allowed, remaining = await redis_client.check_rate_limit(
        key,
        max_requests,
        window_seconds,
    )
    
    return is_allowed, {
        "limit": max_requests,
        "remaining": remaining,
        "reset_in": window_seconds,
    }


async def rate_limit_dependency(
    request: Request,
    max_requests: int = 60,
    window_seconds: int = 60,
) -> None:
    """
    Rate limiting dependency.
    
    Raises HTTPException if rate limit exceeded.
    """
    is_allowed, info = await check_rate_limit(
        request,
        max_requests=max_requests,
        window_seconds=window_seconds,
    )
    
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(info["limit"]),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(info["reset_in"]),
            },
        )


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]
Auth = Annotated[AuthContext, Depends(get_auth_context)]
