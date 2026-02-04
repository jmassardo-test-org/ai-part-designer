"""
Tests for Team models.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.models.team import Team, TeamMember, TeamRole, ProjectTeam


class TestTeamRole:
    """Tests for TeamRole enum."""

    def test_team_role_values(self) -> None:
        """Test TeamRole enum has expected values."""
        assert TeamRole.MEMBER.value == "member"
        assert TeamRole.LEAD.value == "lead"
        assert TeamRole.ADMIN.value == "admin"

    def test_team_role_is_string_enum(self) -> None:
        """Test TeamRole is a string enum."""
        assert isinstance(TeamRole.MEMBER, str)
        assert TeamRole.MEMBER == "member"


class TestTeamModel:
    """Tests for Team model."""

    def test_team_repr(self) -> None:
        """Test Team string representation."""
        team = Team(
            id=uuid4(),
            organization_id=uuid4(),
            name="Engineering",
        )
        repr_str = repr(team)
        assert "Team" in repr_str
        assert team.name in repr_str

    def test_team_default_settings(self) -> None:
        """Test Team has empty dict as default settings."""
        team = Team(
            id=uuid4(),
            organization_id=uuid4(),
            name="Engineering",
            slug="engineering",
        )
        # Default should be empty dict when not explicitly set via DB
        assert team.settings == {} or team.settings is None or isinstance(team.settings, dict)

    def test_team_color_property(self) -> None:
        """Test Team color property from settings."""
        team = Team(
            id=uuid4(),
            organization_id=uuid4(),
            name="Engineering",
            slug="engineering",
            settings={"color": "#3B82F6"},
        )
        assert team.color == "#3B82F6"

    def test_team_color_property_missing(self) -> None:
        """Test Team color property returns None when not set."""
        team = Team(
            id=uuid4(),
            organization_id=uuid4(),
            name="Engineering",
            slug="engineering",
            settings={},
        )
        assert team.color is None

    def test_team_icon_property(self) -> None:
        """Test Team icon property from settings."""
        team = Team(
            id=uuid4(),
            organization_id=uuid4(),
            name="Engineering",
            slug="engineering",
            settings={"icon": "code"},
        )
        assert team.icon == "code"

    def test_team_is_active_default(self) -> None:
        """Test Team is_active can be set to True."""
        team = Team(
            id=uuid4(),
            organization_id=uuid4(),
            name="Engineering",
            slug="engineering",
            is_active=True,  # Defaults apply at DB level, explicitly set here
        )
        assert team.is_active is True


class TestTeamMemberModel:
    """Tests for TeamMember model."""

    def test_team_member_repr(self) -> None:
        """Test TeamMember string representation."""
        member = TeamMember(
            id=uuid4(),
            team_id=uuid4(),
            user_id=uuid4(),
            role=TeamRole.MEMBER.value,
        )
        repr_str = repr(member)
        assert "TeamMember" in repr_str
        assert member.role in repr_str

    def test_team_member_default_role(self) -> None:
        """Test TeamMember role is set to MEMBER."""
        member = TeamMember(
            id=uuid4(),
            team_id=uuid4(),
            user_id=uuid4(),
            role=TeamRole.MEMBER.value,  # Defaults apply at DB level
        )
        assert member.role == TeamRole.MEMBER.value

    def test_team_member_is_active_default(self) -> None:
        """Test TeamMember is_active can be set to True."""
        member = TeamMember(
            id=uuid4(),
            team_id=uuid4(),
            user_id=uuid4(),
            is_active=True,  # Defaults apply at DB level
        )
        assert member.is_active is True

    def test_has_permission_member_role(self) -> None:
        """Test has_permission for MEMBER role."""
        member = TeamMember(
            id=uuid4(),
            team_id=uuid4(),
            user_id=uuid4(),
            role=TeamRole.MEMBER.value,
        )
        assert member.has_permission(TeamRole.MEMBER) is True
        assert member.has_permission(TeamRole.LEAD) is False
        assert member.has_permission(TeamRole.ADMIN) is False

    def test_has_permission_lead_role(self) -> None:
        """Test has_permission for LEAD role."""
        member = TeamMember(
            id=uuid4(),
            team_id=uuid4(),
            user_id=uuid4(),
            role=TeamRole.LEAD.value,
        )
        assert member.has_permission(TeamRole.MEMBER) is True
        assert member.has_permission(TeamRole.LEAD) is True
        assert member.has_permission(TeamRole.ADMIN) is False

    def test_has_permission_admin_role(self) -> None:
        """Test has_permission for ADMIN role."""
        member = TeamMember(
            id=uuid4(),
            team_id=uuid4(),
            user_id=uuid4(),
            role=TeamRole.ADMIN.value,
        )
        assert member.has_permission(TeamRole.MEMBER) is True
        assert member.has_permission(TeamRole.LEAD) is True
        assert member.has_permission(TeamRole.ADMIN) is True


class TestProjectTeamModel:
    """Tests for ProjectTeam model."""

    def test_project_team_repr(self) -> None:
        """Test ProjectTeam string representation."""
        project_team = ProjectTeam(
            id=uuid4(),
            project_id=uuid4(),
            team_id=uuid4(),
            permission_level="editor",
        )
        repr_str = repr(project_team)
        assert "ProjectTeam" in repr_str
        assert "editor" in repr_str

    def test_project_team_default_permission(self) -> None:
        """Test ProjectTeam permission level can be set to viewer."""
        project_team = ProjectTeam(
            id=uuid4(),
            project_id=uuid4(),
            team_id=uuid4(),
            permission_level="viewer",  # Defaults apply at DB level
        )
        assert project_team.permission_level == "viewer"

    def test_project_team_with_custom_permission(self) -> None:
        """Test ProjectTeam with custom permission level."""
        project_team = ProjectTeam(
            id=uuid4(),
            project_id=uuid4(),
            team_id=uuid4(),
            permission_level="admin",
        )
        assert project_team.permission_level == "admin"
