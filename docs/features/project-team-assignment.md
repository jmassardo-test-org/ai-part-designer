# Project Team Assignment

## Overview

Projects can now be assigned to teams, allowing for better organization and access control within organizations. This feature enables users to associate a project with a specific team, making it easier to manage collaborative work.

## API Changes

### Updated Endpoints

#### PUT /api/v1/projects/{project_id}

Update a project, including optional team assignment.

**Request Body:**
```json
{
  "name": "string (optional)",
  "description": "string | null (optional)",
  "team_id": "uuid (optional)"
}
```

**Response:**
```json
{
  "id": "uuid",
  "name": "string",
  "description": "string | null",
  "design_count": "integer",
  "thumbnail_url": "string | null",
  "created_at": "string (ISO 8601)",
  "updated_at": "string (ISO 8601)",
  "team_id": "uuid | null",
  "team_name": "string | null"
}
```

**Permissions:**
- User must be the project owner
- User must be a member of the team being assigned, OR
- User must be an admin of the organization that owns the team

#### GET /api/v1/projects

List all projects for the current user. Response now includes team information.

**Response includes team_id and team_name for each project**

#### GET /api/v1/projects/available-teams

Get list of teams available for assignment to projects.

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "string",
    "organization_id": "uuid"
  }
]
```

Returns only teams where:
- The current user is an active member
- The team is active (not deleted)

## Frontend Changes

### Project Settings Modal

The project edit modal now includes a team selector dropdown:
- Shows "No team" option to unassign a team
- Lists all teams where the user is a member
- Displays current team assignment when editing

### Project Display

Projects now show their assigned team:
- **Grid View**: Team name appears in the metadata row with primary color
- **List View**: Team name appears as "Team: {name}" below the description

## Usage Example

### Assigning a Team to a Project

```bash
# 1. Get available teams
curl -X GET http://localhost:8000/api/v1/projects/available-teams \
  -H "Authorization: Bearer {token}"

# 2. Update project with team assignment
curl -X PUT http://localhost:8000/api/v1/projects/{project_id} \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Project",
    "team_id": "team-uuid-here"
  }'
```

### Removing Team Assignment

```bash
curl -X PUT http://localhost:8000/api/v1/projects/{project_id} \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Project",
    "team_id": null
  }'
```

## Business Rules

1. **Single Team Assignment**: A project can only be assigned to one team at a time. Assigning a new team will replace any existing team assignment.

2. **Permission Requirements**: 
   - User must own the project to assign/unassign teams
   - User must be a member of the team OR an admin of the team's organization

3. **Team Visibility**: Only active teams where the user is an active member appear in the available teams list.

4. **Optional Assignment**: Team assignment is optional. Projects without a team assignment work normally.

## Database Schema

### ProjectTeam Table

The `project_team` table manages project-team relationships:

```sql
CREATE TABLE project_team (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    team_id UUID REFERENCES teams(id),
    permission_level VARCHAR(20) DEFAULT 'editor',
    assigned_by_id UUID REFERENCES users(id),
    assigned_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(project_id, team_id)
);
```

**Note**: Currently, only one team per project is supported, enforced at the application level by clearing existing assignments when assigning a new team.

## Testing

Tests are located in:
- Backend: `backend/tests/api/test_projects.py::TestProjectTeamAssignment`
- Coverage includes:
  - Successful team assignment
  - Invalid team handling
  - Permission validation
  - Multiple teams listing
  - Team info in project lists

## Future Enhancements

Potential improvements for future iterations:

1. **Multiple Teams**: Support assigning multiple teams to a project with different permission levels
2. **Inherited Permissions**: Use team permissions to control access to project designs
3. **Team-Level Projects**: Allow creating projects directly under a team
4. **Team Activity Feed**: Show team activity related to assigned projects
5. **Project Templates**: Share project templates across teams

## Related Issues

- Parent Epic: #23 (Epic 5: Organization Admin & RBAC)
- Implements: Team Selector in Project Settings
