# Organization-Level Feature Permissions

This document describes how to implement and use organization-level feature permissions in the AI Part Designer platform.

> **Note:** For comprehensive role-based access control (RBAC) documentation including organization roles and permissions, see the [RBAC Permission Matrix](./rbac-permission-matrix.md).

## Overview

Organization-level feature permissions allow organization admins to control which features are enabled for their organization. This provides fine-grained control over functionality based on subscription tiers and organizational needs.

## Feature Definitions

Features are defined in `backend/app/core/features.py`. Each feature is represented by an enum value:

```python
class OrgFeature(StrEnum):
    """Features that can be toggled at the organization level."""
    
    AI_GENERATION = "ai_generation"
    AI_CHAT = "ai_chat"
    TEMPLATES = "templates"
    # ... more features
```

### Default Features by Tier

Features are automatically enabled based on subscription tier:

- **Free**: Basic AI generation, templates, STL export
- **Pro**: All free features + direct generation, custom templates, assemblies, more exports
- **Enterprise**: All pro features + advanced CAD, external storage, cost estimation

## Backend Implementation

### Checking Feature Permissions

#### In Models

Organizations have a `has_feature()` method:

```python
from app.models.organization import Organization

# Check if org has a feature
if org.has_feature("ai_generation"):
    # Feature is enabled
    pass
```

#### In API Endpoints

Use the `require_org_feature()` dependency to enforce feature permissions:

```python
from app.api.deps import require_org_feature
from app.core.features import OrgFeature

@router.post("/designs/{design_id}/generate")
async def generate_design(
    design_id: UUID,
    org_id: UUID,
    _feature: None = Depends(require_org_feature(OrgFeature.AI_GENERATION.value)),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a design (requires AI generation feature)."""
    # Feature is guaranteed to be enabled
    pass
```

The dependency will:
1. Look up the organization by `org_id` (must be in path/query params)
2. Check if the feature is enabled
3. Return 403 if disabled
4. Continue to endpoint if enabled

### Managing Features

Organization admins can manage features via the API:

```bash
# Get features
GET /api/v1/organizations/{org_id}/features

# Update features
PUT /api/v1/organizations/{org_id}/features
{
  "enabled_features": ["ai_generation", "templates", "export_stl"]
}
```

Response:
```json
{
  "enabled_features": ["ai_generation", "templates", "export_stl"],
  "available_features": ["ai_generation", "ai_chat", "templates", ...],
  "subscription_tier": "free"
}
```

## Frontend Implementation

### Organization Settings UI

The feature permissions UI is in the Settings tab of the Organization Settings page (`/organizations/{orgId}/settings`).

Only organization owners can see and modify feature permissions.

### Using the API

```typescript
import { organizationsApi } from '@/lib/api/organizations';

// Get features
const features = await organizationsApi.getFeatures(orgId);

// Update features
const updated = await organizationsApi.updateFeatures(orgId, {
  enabled_features: ['ai_generation', 'templates'],
});
```

### Checking Features in UI

```typescript
// In components, check if a feature is enabled
if (org.settings.enabled_features?.includes('ai_generation')) {
  // Show AI generation UI
}
```

## Adding New Features

To add a new feature:

1. Add to `OrgFeature` enum in `backend/app/core/features.py`
2. Add to appropriate tier in `DEFAULT_FEATURES`
3. Add display name and description in `frontend/src/pages/OrganizationSettingsPage.tsx` `featureLabels`
4. Use `require_org_feature()` dependency in relevant endpoints
5. Check feature in frontend components as needed

## Testing

Tests are located in:
- Backend: `backend/tests/api/test_organizations.py` - `TestOrganizationFeatures` class
- Tests cover:
  - Getting features
  - Updating features
  - Validating feature names
  - Checking tier restrictions
  - Default feature behavior

## Security Considerations

- Only organization owners can view and modify feature permissions
- Features can only be enabled if they're available on the org's subscription tier
- Feature checks are enforced at the API level via dependencies
- Invalid feature names are rejected with 422 status
- Attempts to enable unavailable features return 400 with clear error messages

## Migration Notes

Existing organizations will automatically get features based on their subscription tier when the `enabled_features` setting is not present or empty. This ensures backward compatibility.

The Organization model's `enabled_features` property returns tier defaults when no explicit features are set:

```python
@property
def enabled_features(self) -> list[str]:
    """Get list of enabled features."""
    features = self.settings.get("enabled_features")
    # If not set, use tier defaults
    if features is None or features == []:
        tier = self.subscription_tier
        return get_default_features(tier)
    return features
```
