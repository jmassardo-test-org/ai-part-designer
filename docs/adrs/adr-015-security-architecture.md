# ADR-015: Security Architecture

## Status
Accepted

## Date
2024-01-15

## Context

The AI Part Designer platform handles sensitive data including:
- User credentials and personal information
- Proprietary CAD designs and intellectual property
- Payment information (for premium tiers)
- AI model outputs and generation parameters

We need a comprehensive security architecture that provides:
- Defense in depth
- Data protection at rest and in transit
- Strong authentication and authorization
- Audit trail for compliance
- Protection against common attack vectors

## Decision

### Authentication Architecture

**JWT-Based Authentication**
- Access tokens: 15-minute expiry, signed with HS256
- Refresh tokens: 7-day expiry (configurable per tier)
- Token blacklisting via Redis for immediate revocation
- Unique JTI (JWT ID) for each token to enable granular revocation

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│  API Layer  │────▶│   Database  │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                    │
       │  JWT Token        │  Validate          │  User Data
       │                   │  + Decode          │
       │                   ▼                    │
       │            ┌─────────────┐             │
       │            │    Redis    │◀────────────┘
       │            │ (blacklist) │  Token State
       │            └─────────────┘
```

**Password Security**
- bcrypt with cost factor 12 (adaptive to hardware)
- Minimum 8 characters with complexity requirements
- Password history tracking (prevent reuse)
- Account lockout after 5 failed attempts

**API Key Authentication**
- For service-to-service and external integrations
- Keys stored as SHA-256 hashes
- Scoped permissions per key
- Key rotation support with grace period

### Authorization Model

**Role-Based Access Control (RBAC)**
```
Role Hierarchy:
├── user          (basic permissions)
├── moderator     (+ moderation capabilities)
├── admin         (+ user management, templates)
└── super_admin   (+ system administration)
```

**Permission-Based Fine-Grained Control**
- Resource-level permissions (design:read, design:write, etc.)
- Inherited permissions through role hierarchy
- Per-resource sharing with granular access (read/write/admin)

### Data Encryption

**In Transit**
- TLS 1.3 required for all connections
- HSTS with preload for browser security
- Certificate pinning for mobile clients

**At Rest**
- Fernet encryption for sensitive fields (derived from master key via PBKDF2)
- Encrypted fields: API credentials, AI provider keys, payment data
- PostgreSQL TDE for database-level encryption (recommended)
- S3 server-side encryption for stored files

**Key Management**
```
Master Key (SECRET_KEY)
    │
    ├──▶ PBKDF2 ──▶ Fernet Key (field encryption)
    │
    ├──▶ JWT Signing Key
    │
    └──▶ HMAC Signing Key
```

### Security Middleware Stack

```
Request Flow:
┌─────────────────────────────────────────────────────────┐
│  1. IP Blocking        - Block banned IPs               │
│  2. Rate Limiting      - Prevent abuse                  │
│  3. Request ID         - Tracing/correlation            │
│  4. Security Logging   - Audit trail                    │
│  5. Security Headers   - Browser protections            │
│  6. CORS               - Cross-origin policy            │
│  7. Authentication     - JWT/API key validation         │
│  8. Authorization      - Permission checking            │
│  9. Application Logic  - Business logic                 │
└─────────────────────────────────────────────────────────┘
```

### Security Headers

| Header | Value | Purpose |
|--------|-------|---------|
| X-Frame-Options | DENY | Prevent clickjacking |
| X-Content-Type-Options | nosniff | Prevent MIME sniffing |
| X-XSS-Protection | 1; mode=block | XSS filter |
| Referrer-Policy | strict-origin-when-cross-origin | Control referrer |
| Content-Security-Policy | default-src 'self' ... | XSS protection |
| Strict-Transport-Security | max-age=31536000 | Force HTTPS |
| Permissions-Policy | camera=(), ... | Disable risky features |

### Rate Limiting

**Tiered Limits**
| Tier | API Requests/min | AI Generations/day | Exports/day |
|------|-----------------|-------------------|-------------|
| Free | 30 | 10 | 5 |
| Pro | 100 | 100 | unlimited |
| Enterprise | 500 | 1000 | unlimited |

**Protection Layers**
1. Global rate limit (middleware)
2. Endpoint-specific limits (decorators)
3. User-based limits (by user ID)
4. IP-based limits (unauthenticated)

### Audit Logging

**Logged Events**
- Authentication events (login, logout, failed attempts)
- Authorization failures
- Data modifications (create, update, delete)
- Administrative actions
- Security events (rate limit hits, suspicious activity)

**Log Format**
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "abc123",
  "user_id": "uuid",
  "action": "design.update",
  "resource_type": "design",
  "resource_id": "uuid",
  "client_ip": "1.2.3.4",
  "user_agent": "...",
  "changes": {"field": {"old": "x", "new": "y"}},
  "result": "success"
}
```

### Input Validation & Sanitization

**Validation Rules**
- All inputs validated at API boundary
- Type checking via Pydantic models
- Size limits on all string fields
- Enum validation for categorical fields

**Sanitization**
- Filename sanitization (remove path traversal attempts)
- HTML sanitization for user content
- SQL parameterization (via SQLAlchemy ORM)
- No string interpolation in queries

### Threat Model

**STRIDE Analysis**

| Threat | Mitigation |
|--------|------------|
| Spoofing | JWT authentication, API key validation |
| Tampering | HMAC signatures, database constraints |
| Repudiation | Comprehensive audit logging |
| Information Disclosure | Encryption, access control |
| Denial of Service | Rate limiting, resource quotas |
| Elevation of Privilege | RBAC, permission checking |

**OWASP Top 10 Coverage**

| Risk | Mitigation |
|------|------------|
| Injection | ORM, parameterized queries |
| Broken Authentication | JWT best practices, bcrypt |
| Sensitive Data Exposure | Encryption, minimal exposure |
| XXE | JSON-only APIs |
| Broken Access Control | RBAC, resource authorization |
| Security Misconfiguration | Security headers, hardened defaults |
| XSS | CSP, input sanitization |
| Insecure Deserialization | Pydantic validation |
| Using Vulnerable Components | Dependency scanning |
| Insufficient Logging | Comprehensive audit trail |

### Secrets Management

**Environment-Based Configuration**
- Secrets via environment variables
- No secrets in code or version control
- Different secrets per environment

**Production Recommendations**
- Use HashiCorp Vault or AWS Secrets Manager
- Rotate secrets regularly
- Encrypt secrets at rest in CI/CD

### Tenant Isolation

**Data Isolation**
- User ID foreign keys on all user data
- Row-level security in queries
- No cross-tenant data access in API

**Resource Isolation**
- Per-user file storage paths
- Separate Redis namespaces per user
- Job isolation in Celery workers

## Consequences

### Positive
- Defense in depth protects against various attack vectors
- Comprehensive audit trail for compliance
- Granular access control for enterprise needs
- Industry-standard cryptographic practices

### Negative
- Additional latency from security checks
- Complexity in middleware stack
- Key management requires operational care
- Token blacklisting adds Redis dependency

### Risks
- SECRET_KEY compromise affects all encryption
- Redis unavailability impacts token blacklisting
- Over-aggressive rate limiting may block legitimate users

## Implementation Files

- `backend/app/core/security.py` - Cryptographic utilities
- `backend/app/core/auth.py` - Authentication/authorization
- `backend/app/middleware/security.py` - Security middleware
- `backend/app/models/audit.py` - Audit logging model

## Compliance Notes

This architecture supports:
- GDPR (data protection, audit logs, encryption)
- SOC 2 (access control, logging, encryption)
- OWASP guidelines (security best practices)
