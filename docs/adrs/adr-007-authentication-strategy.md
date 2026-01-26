# ADR-007: Authentication and Authorization Strategy

## Status
Proposed

## Context
We need a robust authentication and authorization system that supports:
- User registration and login
- Password reset flow
- Session management
- Role-based access control (RBAC)
- Subscription tier enforcement
- Optional OAuth/SSO integration
- API token authentication for future API access

## Decision
We will implement a **custom JWT-based authentication system** with the following components:
- **Access tokens**: Short-lived JWTs (15 minutes)
- **Refresh tokens**: Long-lived, stored in database (7-30 days)
- **Password hashing**: bcrypt with cost factor 12
- **OAuth**: Google and GitHub via OAuth 2.0 (Phase 2)

Technology choices:
- **JWT Library**: python-jose with cryptography backend
- **Password Hashing**: passlib with bcrypt
- **OAuth**: authlib
- **Session Storage**: Redis (for token blacklisting)

## Consequences

### Positive
- **Full control**: No external auth service dependencies or costs
- **Customizable**: Can tailor to exact requirements
- **Stateless API**: JWTs enable horizontal scaling
- **Cost effective**: No per-user fees from auth providers

### Negative
- **Development effort**: More code to write and maintain
- **Security responsibility**: Must implement security best practices correctly
- **No SSO out-of-box**: Need to implement OAuth flows ourselves

### Risk Mitigation
- Follow OWASP authentication best practices
- Regular security audits
- Use well-tested libraries (passlib, python-jose)
- Implement rate limiting on auth endpoints

## Options Considered

| Option | Pros | Cons | Score |
|--------|------|------|-------|
| **Custom JWT** | Full control, no vendor cost | Development effort | ⭐⭐⭐⭐ |
| Auth0 | Feature-rich, secure | Cost at scale, vendor lock-in | ⭐⭐⭐⭐ |
| Firebase Auth | Easy setup, good OAuth | Google dependency | ⭐⭐⭐ |
| Clerk | Modern DX, React components | Newer, cost | ⭐⭐⭐ |
| Keycloak | Open source, full-featured | Complex to operate | ⭐⭐⭐ |

## Technical Details

### JWT Token Structure
```python
# Access Token Payload
{
    "sub": "user-uuid",           # User ID
    "email": "user@example.com",
    "role": "user",               # user, admin, super_admin
    "tier": "pro",                # free, pro, enterprise
    "exp": 1706200000,            # 15 min from issue
    "iat": 1706199100,
    "type": "access"
}

# Refresh Token (stored in DB)
{
    "sub": "user-uuid",
    "exp": 1707404500,            # 7-30 days
    "iat": 1706199100,
    "type": "refresh",
    "jti": "unique-token-id"      # For revocation
}
```

### Authentication Flow
```
┌─────────────────────────────────────────────────────────────┐
│                     REGISTRATION                             │
├─────────────────────────────────────────────────────────────┤
│  1. User submits email, password, display name              │
│  2. Validate input (email format, password strength)        │
│  3. Check email uniqueness                                   │
│  4. Hash password with bcrypt (cost=12)                     │
│  5. Create user with status="pending"                       │
│  6. Generate verification token (expires 24h)               │
│  7. Send verification email                                  │
│  8. User clicks link → status="active"                      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                        LOGIN                                 │
├─────────────────────────────────────────────────────────────┤
│  1. User submits email, password                            │
│  2. Look up user by email                                    │
│  3. Verify password with bcrypt                             │
│  4. Check account status (active, suspended, pending)       │
│  5. Generate access token (15 min)                          │
│  6. Generate refresh token (7/30 days)                      │
│  7. Store refresh token in DB                               │
│  8. Return tokens to client                                  │
│  9. Log successful login                                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    TOKEN REFRESH                             │
├─────────────────────────────────────────────────────────────┤
│  1. Client sends refresh token                              │
│  2. Validate token signature and expiry                     │
│  3. Check token exists in DB (not revoked)                  │
│  4. Check user still active                                  │
│  5. Generate new access token                               │
│  6. Optionally rotate refresh token                         │
│  7. Return new tokens                                        │
└─────────────────────────────────────────────────────────────┘
```

### Security Implementation
```python
# app/core/security.py
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt, JWTError
from pydantic import BaseModel

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class TokenPayload(BaseModel):
    sub: str
    email: str
    role: str
    tier: str
    exp: datetime
    type: str

def hash_password(password: str) -> str:
    """Hash password with bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain, hashed)

def create_access_token(user: User) -> str:
    """Create short-lived access token."""
    expire = datetime.utcnow() + timedelta(minutes=15)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "tier": user.subscription_tier,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

def create_refresh_token(user: User, remember_me: bool = False) -> tuple[str, datetime]:
    """Create long-lived refresh token."""
    days = 30 if remember_me else 7
    expire = datetime.utcnow() + timedelta(days=days)
    jti = str(uuid.uuid4())
    
    payload = {
        "sub": str(user.id),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
        "jti": jti
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token, expire, jti

def decode_token(token: str) -> TokenPayload:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return TokenPayload(**payload)
    except JWTError:
        raise InvalidTokenError()
```

### RBAC Implementation
```python
# app/core/permissions.py
from enum import Enum
from functools import wraps

class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class Permission(str, Enum):
    # Designs
    CREATE_DESIGN = "create:design"
    READ_DESIGN = "read:design"
    UPDATE_DESIGN = "update:design"
    DELETE_DESIGN = "delete:design"
    
    # Admin
    VIEW_ALL_USERS = "view:all_users"
    MODERATE_CONTENT = "moderate:content"
    MANAGE_USERS = "manage:users"
    
    # System
    VIEW_METRICS = "view:metrics"
    MANAGE_SYSTEM = "manage:system"

ROLE_PERMISSIONS = {
    Role.USER: [
        Permission.CREATE_DESIGN,
        Permission.READ_DESIGN,
        Permission.UPDATE_DESIGN,
        Permission.DELETE_DESIGN,
    ],
    Role.ADMIN: [
        *ROLE_PERMISSIONS[Role.USER],
        Permission.VIEW_ALL_USERS,
        Permission.MODERATE_CONTENT,
        Permission.VIEW_METRICS,
    ],
    Role.SUPER_ADMIN: [
        *ROLE_PERMISSIONS[Role.ADMIN],
        Permission.MANAGE_USERS,
        Permission.MANAGE_SYSTEM,
    ],
}

def require_permission(permission: Permission):
    """Decorator to require specific permission."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User, **kwargs):
            if permission not in ROLE_PERMISSIONS.get(current_user.role, []):
                raise PermissionDeniedError()
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator
```

### FastAPI Dependencies
```python
# app/api/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Extract and validate current user from JWT."""
    token = credentials.credentials
    
    try:
        payload = decode_token(token)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    if payload.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    user = await user_repo.get_by_id(db, payload.sub)
    if not user or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    return user

async def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Require admin role."""
    if current_user.role not in [Role.ADMIN, Role.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user
```

### Password Requirements
```python
# app/core/validators.py
import re

def validate_password(password: str) -> tuple[bool, list[str]]:
    """Validate password meets security requirements."""
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters")
    if len(password) > 128:
        errors.append("Password must be at most 128 characters")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one number")
    
    return len(errors) == 0, errors
```

### Rate Limiting
```python
# app/middleware/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Apply to auth endpoints
@router.post("/login")
@limiter.limit("5/minute")  # 5 attempts per minute
async def login(request: Request, credentials: LoginRequest):
    ...

@router.post("/register")
@limiter.limit("3/hour")  # 3 registrations per hour per IP
async def register(request: Request, data: RegisterRequest):
    ...
```

## Security Checklist
- [ ] Passwords hashed with bcrypt (cost 12+)
- [ ] JWT tokens signed with strong secret
- [ ] Access tokens short-lived (15 min)
- [ ] Refresh tokens stored in DB for revocation
- [ ] Rate limiting on auth endpoints
- [ ] Account lockout after failed attempts
- [ ] Secure password reset with expiring tokens
- [ ] HTTPS enforced in production
- [ ] Secure cookie settings (HttpOnly, Secure, SameSite)

## References
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [JWT Best Practices](https://auth0.com/blog/jwt-security-best-practices/)
- [python-jose](https://python-jose.readthedocs.io/)
- [passlib](https://passlib.readthedocs.io/)
