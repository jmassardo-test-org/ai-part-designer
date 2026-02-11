# Organization RBAC Tests

This directory contains comprehensive test coverage for organization Role-Based Access Control (RBAC).

## Test Files

### `test_organizations.py`
Original organization tests covering basic CRUD operations:
- Organization creation, listing, viewing, updating, deletion
- Basic member management
- Basic invitation workflows

### `test_organizations_rbac.py` ⭐ NEW
Comprehensive RBAC enforcement tests (45+ test cases):
- Tests for each role level: Owner, Admin, Member, Viewer, Outsider
- Privilege escalation prevention
- Edge cases and error handling
- Authorization verification for all endpoints

## Test Structure

Each endpoint is tested for proper RBAC enforcement with dedicated test classes:

```
TestGetOrganizationRBAC          - GET /organizations/{org_id} (VIEWER required)
TestUpdateOrganizationRBAC       - PATCH /organizations/{org_id} (ADMIN required)
TestDeleteOrganizationRBAC       - DELETE /organizations/{org_id} (OWNER required)
TestListMembersRBAC              - GET /organizations/{org_id}/members (VIEWER required)
TestChangeRoleRBAC               - PATCH /organizations/{org_id}/members/{id}/role (ADMIN required)
TestRemoveMemberRBAC             - DELETE /organizations/{org_id}/members/{id} (ADMIN required)
TestTransferOwnershipRBAC        - POST /organizations/{org_id}/transfer-ownership (OWNER required)
TestInviteMemberRBAC             - POST /organizations/{org_id}/invites (ADMIN required)
TestListInvitesRBAC              - GET /organizations/{org_id}/invites (ADMIN required)
TestRevokeInviteRBAC             - DELETE /organizations/{org_id}/invites/{id} (ADMIN required)
TestAcceptInviteRBAC             - POST /organizations/invites/accept (Authenticated)
TestPrivilegeEscalation          - Privilege escalation prevention tests
```

## Running Tests

### Run all organization tests:
```bash
pytest tests/api/test_organizations.py tests/api/test_organizations_rbac.py -v
```

### Run only RBAC tests:
```bash
pytest tests/api/test_organizations_rbac.py -v
```

### Run specific test class:
```bash
pytest tests/api/test_organizations_rbac.py::TestGetOrganizationRBAC -v
```

### Run specific test:
```bash
pytest tests/api/test_organizations_rbac.py::TestGetOrganizationRBAC::test_outsider_cannot_view -v
```

### Run with coverage:
```bash
pytest tests/api/test_organizations_rbac.py --cov=app.api.v1.organizations --cov-report=html
```

## Test Fixtures

The RBAC tests use these fixtures:

- `org_owner` - User with OWNER role
- `org_admin` - User with ADMIN role
- `org_member` - User with MEMBER role
- `org_viewer` - User with VIEWER role
- `outsider` - User not in the organization
- `test_org` - Test organization with all role types

## What's Tested

✅ **Authentication** - All endpoints require valid auth  
✅ **Authorization** - Proper role enforcement at backend  
✅ **Role Hierarchy** - VIEWER < MEMBER < ADMIN < OWNER  
✅ **Privilege Escalation** - Cannot escalate to higher roles  
✅ **Business Logic** - Cannot remove/change owner without transfer  
✅ **Edge Cases** - Invalid tokens, expired invites, etc.  

## Security Guarantees

These tests verify that:

1. **No UI-only security** - All checks happen on backend
2. **Role hierarchy enforced** - Lower roles cannot perform higher role actions
3. **Owner protection** - Owner cannot be removed or demoted except via transfer
4. **Member limits** - Invitation system respects organization limits
5. **Audit trail** - All sensitive operations are logged

## Related Documentation

- [RBAC Permission Matrix](../../../docs/rbac-permission-matrix.md) - Complete permission documentation
- [Organization RBAC Audit Report](../../../docs/security/org-rbac-audit.md) - Security audit report
- [Organization E2E Tests](../../../frontend/e2e/organization-rbac.spec.ts)
- [Organization API Source](../../app/api/v1/organizations.py)
- [Organization Models](../../app/models/organization.py)
