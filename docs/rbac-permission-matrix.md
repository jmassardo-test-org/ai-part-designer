# RBAC Permission Matrix

**Last Updated:** 2026-02-11  
**Issue:** US-5.3: Create Permission Matrix Documentation  
**Status:** ✅ Complete

---

## Overview

This document provides a comprehensive overview of the Role-Based Access Control (RBAC) system in AssemblematicAI. The platform implements three levels of access control:

1. **System-Level Roles** - Platform-wide permissions (User, Moderator, Admin, Super Admin)
2. **Organization-Level Roles** - Organization membership and permissions (Viewer, Member, Admin, Owner)
3. **Team-Level Roles** - Team membership within organizations (Member, Lead, Admin)

---

## Table of Contents

- [System-Level Roles](#system-level-roles)
- [Organization-Level Roles](#organization-level-roles)
- [Team-Level Roles](#team-level-roles)
- [Resource-Level Permissions](#resource-level-permissions)
- [Permission Hierarchy](#permission-hierarchy)
- [Implementation Reference](#implementation-reference)

---

## System-Level Roles

System-level roles control access to platform-wide features and administrative functions. Roles are hierarchical: higher roles inherit all permissions from lower roles.

### Role Definitions

| Role | Level | Description |
|------|-------|-------------|
| **User** | 0 | Standard authenticated user with access to core features |
| **Moderator** | 1 | Elevated user with content moderation privileges |
| **Admin** | 2 | Platform administrator with user and template management |
| **Super Admin** | 3 | Full platform access including system administration |

### System Permission Matrix

| Permission | User | Moderator | Admin | Super Admin |
|-----------|:----:|:---------:|:-----:|:-----------:|
| **Designs** |
| Create designs | ✅ | ✅ | ✅ | ✅ |
| Read own designs | ✅ | ✅ | ✅ | ✅ |
| Update own designs | ✅ | ✅ | ✅ | ✅ |
| Delete own designs | ✅ | ✅ | ✅ | ✅ |
| Share designs | ✅ | ✅ | ✅ | ✅ |
| Export designs | ✅ | ✅ | ✅ | ✅ |
| **Projects** |
| Create projects | ✅ | ✅ | ✅ | ✅ |
| Read own projects | ✅ | ✅ | ✅ | ✅ |
| Update own projects | ✅ | ✅ | ✅ | ✅ |
| Delete own projects | ✅ | ✅ | ✅ | ✅ |
| **Templates** |
| Read templates | ✅ | ✅ | ✅ | ✅ |
| Create templates | ❌ | ❌ | ✅ | ✅ |
| Update templates | ❌ | ❌ | ✅ | ✅ |
| Delete templates | ❌ | ❌ | ✅ | ✅ |
| **Jobs** |
| Create jobs | ✅ | ✅ | ✅ | ✅ |
| Read own jobs | ✅ | ✅ | ✅ | ✅ |
| Cancel own jobs | ✅ | ✅ | ✅ | ✅ |
| **Moderation** |
| Read moderation queue | ❌ | ✅ | ✅ | ✅ |
| Take moderation actions | ❌ | ✅ | ✅ | ✅ |
| Review reports | ❌ | ✅ | ✅ | ✅ |
| **User Management** |
| Read user list | ❌ | ✅ | ✅ | ✅ |
| Update users | ❌ | ❌ | ✅ | ✅ |
| Delete users | ❌ | ❌ | ✅ | ✅ |
| **System Administration** |
| Read audit logs | ❌ | ❌ | ✅ | ✅ |
| System administration | ❌ | ❌ | ❌ | ✅ |
| User impersonation | ❌ | ❌ | ❌ | ✅ |

### Permission Enum Reference

System permissions are defined in `backend/app/core/auth.py`:

```python
class Permission(StrEnum):
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
```

---

## Organization-Level Roles

Organizations allow users to collaborate on projects with role-based access control. Organization roles are independent of system-level roles.

### Role Definitions

| Role | Level | Description |
|------|-------|-------------|
| **Viewer** | 0 | Read-only access to organization resources |
| **Member** | 1 | Can create and edit own resources within the organization |
| **Admin** | 2 | Can manage members, settings, and all organization resources |
| **Owner** | 3 | Full control over organization, including deletion and ownership transfer |

### Organization Permission Matrix

| Permission | Viewer | Member | Admin | Owner |
|-----------|:------:|:------:|:-----:|:-----:|
| **Organization Management** |
| View organization details | ✅ | ✅ | ✅ | ✅ |
| View member list | ✅ | ✅ | ✅ | ✅ |
| Update organization settings | ❌ | ❌ | ✅ | ✅ |
| Delete organization | ❌ | ❌ | ❌ | ✅ |
| Transfer ownership | ❌ | ❌ | ❌ | ✅ |
| **Member Management** |
| Invite members | ❌ | ❌ | ✅ | ✅ |
| View invitations | ❌ | ❌ | ✅ | ✅ |
| Revoke invitations | ❌ | ❌ | ✅ | ✅ |
| Change member roles | ❌ | ❌ | ✅ | ✅ |
| Remove members | ❌ | ❌ | ✅ | ✅ |
| Remove self | ✅ | ✅ | ✅ | ❌* |
| **Team Management** |
| View teams | ✅ | ✅ | ✅ | ✅ |
| Create teams | ❌ | ❌ | ✅ | ✅ |
| Manage teams | ❌ | ❌ | ✅ | ✅ |
| **Project Management** |
| View org projects | ✅ | ✅ | ✅ | ✅ |
| Create projects | ❌ | ✅ | ✅ | ✅ |
| Edit own projects | ❌ | ✅ | ✅ | ✅ |
| Edit all projects | ❌ | ❌ | ✅ | ✅ |
| Delete own projects | ❌ | ✅ | ✅ | ✅ |
| Delete all projects | ❌ | ❌ | ✅ | ✅ |
| **Feature Management** |
| View enabled features | ✅ | ✅ | ✅ | ✅ |
| Manage features | ❌ | ❌ | ✅ | ✅ |
| **Audit & Security** |
| View audit logs | ❌ | ❌ | ✅ | ✅ |

*\*Owner cannot remove themselves; must transfer ownership first*

### Organization API Endpoints

| Endpoint | Method | Required Role | Purpose |
|----------|--------|---------------|---------|
| `/organizations` | POST | Authenticated | Create organization (becomes owner) |
| `/organizations` | GET | Authenticated | List user's organizations |
| `/organizations/{org_id}` | GET | Viewer | View organization details |
| `/organizations/{org_id}` | PATCH | Admin | Update organization |
| `/organizations/{org_id}` | DELETE | Owner | Delete organization (soft delete) |
| `/organizations/{org_id}/members` | GET | Viewer | List members |
| `/organizations/{org_id}/members/{member_id}/role` | PATCH | Admin | Change member role |
| `/organizations/{org_id}/members/{member_id}` | DELETE | Admin | Remove member |
| `/organizations/{org_id}/transfer-ownership` | POST | Owner | Transfer ownership |
| `/organizations/{org_id}/invites` | POST | Admin | Create invitation |
| `/organizations/{org_id}/invites` | GET | Admin | List invitations |
| `/organizations/{org_id}/invites/{invite_id}` | DELETE | Admin | Revoke invitation |
| `/organizations/invites/accept` | POST | Authenticated | Accept invitation |
| `/users/me/invites` | GET | Authenticated | View pending invitations |
| `/organizations/{org_id}/features` | GET | Viewer | Get enabled features |
| `/organizations/{org_id}/features` | PUT | Admin | Update features |

### Special Rules

1. **Owner Protection**: Owner role cannot be changed or removed except via ownership transfer
2. **Self-Service**: Members can remove themselves from the organization (except owner)
3. **Invitation Limits**: Member count is enforced based on subscription tier
4. **Role Restrictions**: Cannot invite someone with "owner" role directly
5. **Membership Required**: All operations require active membership (is_active=true)

---

## Team-Level Roles

Teams are sub-groups within organizations that provide granular access control for projects and resources.

### Role Definitions

| Role | Level | Description |
|------|-------|-------------|
| **Member** | 0 | Can view team resources and participate |
| **Lead** | 1 | Can manage team members and settings |
| **Admin** | 2 | Full team administration rights |

### Team Permission Matrix

| Permission | Member | Lead | Admin |
|-----------|:------:|:----:|:-----:|
| **Team Management** |
| View team details | ✅ | ✅ | ✅ |
| View team members | ✅ | ✅ | ✅ |
| Update team settings | ❌ | ✅ | ✅ |
| Delete team | ❌ | ❌ | ✅* |
| **Member Management** |
| Add members | ❌ | ✅ | ✅ |
| Remove members | ❌ | ✅ | ✅ |
| Change member roles | ❌ | ✅ | ✅ |
| **Project Access** |
| View assigned projects | ✅ | ✅ | ✅ |
| Manage project assignments | ❌ | ✅ | ✅ |

*\*Team deletion requires organization admin permission*

### Team API Endpoints

| Endpoint | Method | Required Permission | Purpose |
|----------|--------|-------------------|---------|
| `/organizations/{org_id}/teams` | POST | Org Admin | Create team |
| `/organizations/{org_id}/teams` | GET | Org Member | List teams |
| `/organizations/{org_id}/teams/{team_id}` | GET | Team Member | View team details |
| `/organizations/{org_id}/teams/{team_id}` | PATCH | Team Lead | Update team |
| `/organizations/{org_id}/teams/{team_id}` | DELETE | Org Admin | Delete team |
| `/organizations/{org_id}/teams/{team_id}/members` | POST | Team Lead | Add member |
| `/organizations/{org_id}/teams/{team_id}/members` | GET | Team Member | List members |
| `/organizations/{org_id}/teams/{team_id}/members/{member_id}` | PATCH | Team Lead | Update member role |
| `/organizations/{org_id}/teams/{team_id}/members/{member_id}` | DELETE | Team Lead | Remove member |

### Team-Project Assignments

Teams can be assigned to projects with specific permission levels:

| Permission Level | Description |
|-----------------|-------------|
| **Viewer** | Read-only access to project and designs |
| **Editor** | Can create and edit designs within the project |
| **Admin** | Full project management including settings |

---

## Resource-Level Permissions

Individual resources (designs, projects) have their own access control beyond role-based permissions.

### Design Permissions

Designs can be accessed through:

1. **Ownership** - User owns the design (via project ownership)
2. **Public Access** - Design is marked as public (read-only)
3. **Direct Sharing** - Design is explicitly shared with user

#### Design Share Permissions

| Permission | Description |
|-----------|-------------|
| **Read** | Can view design and download exports |
| **Write** | Can edit design parameters and save changes |
| **Admin** | Can manage sharing settings and delete design |

### Project Permissions

Projects belong to either:
- A user (personal project)
- An organization (shared project)

Access is determined by:
1. **User Projects**: Only the owner has access (unless shared)
2. **Organization Projects**: All org members have access based on their org role
3. **Team Assignments**: Teams assigned to projects grant their members access

---

## Permission Hierarchy

### System Role Hierarchy

```
SUPER_ADMIN (Level 3)
    ├─ All system permissions
    ├─ User impersonation
    └─ System administration
    
ADMIN (Level 2)
    ├─ All MODERATOR permissions
    ├─ User management
    ├─ Template management
    └─ Audit log access
    
MODERATOR (Level 1)
    ├─ All USER permissions
    ├─ Content moderation
    └─ User list access
    
USER (Level 0)
    ├─ Design CRUD (own)
    ├─ Project CRUD (own)
    ├─ Template read
    └─ Job management (own)
```

### Organization Role Hierarchy

```
OWNER (Level 3)
    ├─ All ADMIN permissions
    ├─ Organization deletion
    ├─ Ownership transfer
    └─ Feature management
    
ADMIN (Level 2)
    ├─ All MEMBER permissions
    ├─ Member management
    ├─ Settings management
    └─ Team creation
    
MEMBER (Level 1)
    ├─ All VIEWER permissions
    ├─ Create projects
    ├─ Edit own resources
    └─ Self-removal
    
VIEWER (Level 0)
    ├─ View organization
    ├─ View members
    ├─ View projects
    └─ View teams
```

### Team Role Hierarchy

```
ADMIN (Level 2)
    ├─ All LEAD permissions
    └─ Team deletion (with org admin)
    
LEAD (Level 1)
    ├─ All MEMBER permissions
    ├─ Member management
    ├─ Settings management
    └─ Project assignments
    
MEMBER (Level 0)
    ├─ View team
    ├─ View members
    └─ Access assigned projects
```

---

## Implementation Reference

### Backend Code Locations

| Concept | File Path |
|---------|-----------|
| System Roles & Permissions | `backend/app/core/auth.py` |
| Organization Roles | `backend/app/models/organization.py` |
| Team Roles | `backend/app/models/team.py` |
| Organization API | `backend/app/api/v1/organizations.py` |
| Team API | `backend/app/api/v1/teams.py` |
| Resource Authorization | `backend/app/core/auth.py` (ResourceAuthorizer) |

### Using Permissions in Code

#### System-Level Permission Check

```python
from app.core.auth import require_permissions, Permission, Auth
from fastapi import Depends

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    auth: Auth = Depends(require_permissions(Permission.USER_DELETE)),
):
    """Delete a user (requires user:delete permission)."""
    # User is guaranteed to have permission
    pass
```

#### Organization Role Check

```python
from app.api.v1.organizations import require_org_role
from app.models.organization import OrganizationRole

@router.patch("/organizations/{org_id}")
async def update_organization(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update organization (requires ADMIN role)."""
    await require_org_role(db, org_id, current_user.id, OrganizationRole.ADMIN)
    # User is guaranteed to be admin or owner
    pass
```

#### Resource-Level Check

```python
from app.core.auth import ResourceAuthorizer

async def get_design(design_id: UUID, user_id: UUID, db: AsyncSession):
    """Get a design with permission check."""
    authorized = await ResourceAuthorizer.authorize_design_access(
        design_id=design_id,
        user_id=user_id,
        required_permission="read",
        db=db,
    )
    
    if not authorized:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # User can access design
    pass
```

### Testing

RBAC tests are located in:
- **System Permissions**: `backend/tests/security/test_authorization.py`
- **Organization RBAC**: `backend/tests/api/test_organizations_rbac.py` (45+ tests)
- **Team RBAC**: `backend/tests/api/test_teams.py`
- **E2E Tests**: `frontend/e2e/organization-rbac.spec.ts`

Run tests:
```bash
# System permission tests
pytest backend/tests/security/test_authorization.py -v

# Organization RBAC tests
pytest backend/tests/api/test_organizations_rbac.py -v

# All RBAC tests
pytest backend/tests -k "rbac or authorization" -v
```

---

## Security Considerations

### Best Practices

1. **Backend Enforcement**: All permission checks happen on the backend; UI hiding is cosmetic only
2. **Principle of Least Privilege**: Users/members are assigned the minimum role necessary
3. **Audit Logging**: All sensitive operations are logged via `log_org_action()`
4. **Token Validation**: JWT tokens are validated and checked against blacklist
5. **Rate Limiting**: API endpoints are rate-limited to prevent abuse

### Privilege Escalation Prevention

The system prevents privilege escalation through:

1. **Role Change Restrictions**: Cannot change owner's role without transfer
2. **Invitation Validation**: Cannot invite someone as "owner" directly
3. **Hierarchy Enforcement**: Numeric levels enforce role hierarchy
4. **Member Limits**: Subscription tiers limit organization size
5. **Token Expiration**: Invitation tokens expire after 7 days

### Common Security Patterns

```python
# ✅ Good: Check permission before operation
await require_org_role(db, org_id, user_id, OrganizationRole.ADMIN)
await perform_sensitive_operation()

# ❌ Bad: Check after operation
await perform_sensitive_operation()
if not has_permission:
    await rollback()

# ✅ Good: Use dependency injection
@router.post("/endpoint")
async def endpoint(
    auth: Auth = Depends(require_permissions(Permission.ADMIN))
):
    pass

# ❌ Bad: Manual permission check
@router.post("/endpoint")
async def endpoint(current_user: User):
    if current_user.role != "admin":
        raise HTTPException(403)
```

---

## Related Documentation

- [Organization RBAC Audit Report](./security/org-rbac-audit.md) - Comprehensive security audit
- [Organization Feature Permissions](./org-feature-permissions.md) - Feature flag system
- [API Documentation](http://localhost:8000/docs) - Interactive API documentation
- [Authentication Strategy ADR](./adrs/adr-007-authentication-strategy.md) - Authentication decisions
- [Security Architecture ADR](./adrs/adr-015-security-architecture.md) - Security design

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-11 | 1.0 | Initial permission matrix documentation |

---

**Maintained by:** Development Team  
**Contact:** See [Contributing Guide](../CONTRIBUTING.md)
