"""
Pydantic schemas for Team domain.

Defines request/response models for team management API endpoints.
"""

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TeamBase(BaseModel):
    """Base schema with common team fields."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Team name",
        examples=["Engineering", "Design Team"],
    )
    description: str | None = Field(
        None,
        max_length=500,
        description="Team description",
        examples=["Backend engineering team"],
    )


class TeamCreate(TeamBase):
    """Schema for creating a new team."""

    slug: str | None = Field(
        None,
        max_length=100,
        pattern=r"^[a-z0-9-]+$",
        description="URL-friendly team identifier (auto-generated if not provided)",
        examples=["engineering", "design-team"],
    )
    settings: dict | None = Field(
        default_factory=dict,
        description="Team settings (color, icon, etc.)",
        examples=[{"color": "#3B82F6", "icon": "code"}],
    )

    @field_validator("slug", mode="before")
    @classmethod
    def generate_slug(cls, v: str | None, info) -> str:
        """Generate slug from name if not provided."""
        if v:
            return v.lower().strip()
        # Get name from the values being validated
        name = info.data.get("name", "")
        if name:
            # Convert name to slug format
            slug = re.sub(r"[^a-z0-9]+", "-", name.lower())
            return slug.strip("-")
        return ""


class TeamUpdate(BaseModel):
    """Schema for updating an existing team."""

    name: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        description="Team name",
    )
    description: str | None = Field(
        None,
        max_length=500,
        description="Team description",
    )
    settings: dict | None = Field(
        None,
        description="Team settings (merged with existing)",
    )
    is_active: bool | None = Field(
        None,
        description="Whether the team is active",
    )


class TeamMemberInfo(BaseModel):
    """Brief info about a team member."""

    id: UUID
    user_id: UUID
    email: str
    full_name: str | None
    role: str
    joined_at: datetime

    class Config:
        from_attributes = True


class TeamResponse(TeamBase):
    """Schema for team response."""

    id: UUID
    organization_id: UUID
    slug: str
    settings: dict
    is_active: bool
    created_by_id: UUID | None
    created_at: datetime
    updated_at: datetime
    member_count: int | None = None

    class Config:
        from_attributes = True


class TeamListResponse(BaseModel):
    """Schema for paginated team list response."""

    items: list[TeamResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class TeamDetailResponse(TeamResponse):
    """Schema for detailed team response with members."""

    members: list[TeamMemberInfo] = []


# Team Member schemas
class TeamMemberBase(BaseModel):
    """Base schema for team member."""

    role: str = Field(
        default="member",
        description="Member role in the team",
        examples=["member", "lead", "admin"],
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate role is valid."""
        valid_roles = {"member", "lead", "admin"}
        if v.lower() not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}")
        return v.lower()


class TeamMemberAdd(TeamMemberBase):
    """Schema for adding a member to a team."""

    user_id: UUID = Field(
        ...,
        description="User ID to add to the team",
    )


class TeamMemberBulkAdd(BaseModel):
    """Schema for bulk adding members to a team."""

    members: list[TeamMemberAdd] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of members to add",
    )


class TeamMemberUpdate(BaseModel):
    """Schema for updating a team member."""

    role: str | None = Field(
        None,
        description="New role for the member",
    )
    is_active: bool | None = Field(
        None,
        description="Whether the member is active",
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str | None) -> str | None:
        """Validate role is valid if provided."""
        if v is None:
            return v
        valid_roles = {"member", "lead", "admin"}
        if v.lower() not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}")
        return v.lower()


class TeamMemberResponse(BaseModel):
    """Schema for team member response."""

    id: UUID
    team_id: UUID
    user_id: UUID
    role: str
    joined_at: datetime
    is_active: bool
    added_by_id: UUID | None
    created_at: datetime
    updated_at: datetime

    # User info (populated via join)
    user_email: str | None = None
    user_full_name: str | None = None

    class Config:
        from_attributes = True


class TeamMemberListResponse(BaseModel):
    """Schema for paginated team member list response."""

    items: list[TeamMemberResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# Project-Team assignment schemas
class ProjectTeamAssign(BaseModel):
    """Schema for assigning a team to a project."""

    team_id: UUID = Field(
        ...,
        description="Team ID to assign",
    )
    permission_level: str = Field(
        default="viewer",
        description="Permission level for the team",
        examples=["viewer", "editor", "admin"],
    )

    @field_validator("permission_level")
    @classmethod
    def validate_permission(cls, v: str) -> str:
        """Validate permission level is valid."""
        valid_permissions = {"viewer", "editor", "admin"}
        if v.lower() not in valid_permissions:
            raise ValueError(f"Permission level must be one of: {', '.join(valid_permissions)}")
        return v.lower()


class ProjectTeamUpdate(BaseModel):
    """Schema for updating a project-team assignment."""

    permission_level: str = Field(
        ...,
        description="New permission level for the team",
    )

    @field_validator("permission_level")
    @classmethod
    def validate_permission(cls, v: str) -> str:
        """Validate permission level is valid."""
        valid_permissions = {"viewer", "editor", "admin"}
        if v.lower() not in valid_permissions:
            raise ValueError(f"Permission level must be one of: {', '.join(valid_permissions)}")
        return v.lower()


class ProjectTeamResponse(BaseModel):
    """Schema for project-team assignment response."""

    id: UUID
    project_id: UUID
    team_id: UUID
    permission_level: str
    assigned_by_id: UUID | None
    assigned_at: datetime
    created_at: datetime
    updated_at: datetime

    # Related info
    team_name: str | None = None
    project_name: str | None = None

    class Config:
        from_attributes = True


class UserTeamResponse(BaseModel):
    """Schema for user's team membership response."""

    id: UUID
    team_id: UUID
    team_name: str
    team_slug: str
    organization_id: UUID
    organization_name: str
    role: str
    joined_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class UserTeamListResponse(BaseModel):
    """Schema for user's teams list response."""

    items: list[UserTeamResponse]
    total: int
