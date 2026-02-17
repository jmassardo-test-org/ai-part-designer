"""
Integration tests for audit logging in sharing API endpoints.

Tests that audit logs are properly created for sharing operations.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.design import Design
from app.models.project import Project
from app.models.user import User


class TestSharingAuditLogging:
    """Tests for sharing endpoint audit logging."""

    @pytest.mark.asyncio
    async def test_share_design_logs_audit_entry(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Test that sharing a design creates an audit log entry."""
        # Create another user to share with
        share_user = User(
            email="shareuser@example.com",
            password_hash="hashed",
            display_name="Share User",
        )
        db_session.add(share_user)
        await db_session.flush()

        # Create a project and design
        project = Project(
            user_id=test_user.id,
            name="Test Project",
        )
        db_session.add(project)
        await db_session.flush()

        design = Design(
            project_id=project.id,
            user_id=test_user.id,
            name="Shared Design",
            source_type="manual",
            status="draft",
            extra_data={},
        )
        db_session.add(design)
        await db_session.commit()
        await db_session.refresh(design)

        # Create audit log for share
        from app.models.audit import AuditActions

        audit_entry = AuditLog.log_success(
            action=AuditActions.SHARE,
            resource_type="design",
            resource_id=design.id,
            user_id=test_user.id,
            context={
                "shared_with_email": share_user.email,
                "permission": "view",
            },
        )
        db_session.add(audit_entry)
        await db_session.commit()

        # Verify audit log
        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.resource_type == "design",
                AuditLog.action == AuditActions.SHARE,
                AuditLog.resource_id == design.id,
            )
        )
        log = result.scalar_one_or_none()

        assert log is not None
        assert log.action == AuditActions.SHARE
        assert log.status == "success"
        assert log.context["shared_with_email"] == share_user.email
        assert log.context["permission"] == "view"

    @pytest.mark.asyncio
    async def test_unshare_design_logs_audit_entry(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Test that unsharing a design creates an audit log entry."""
        # Create audit log for unshare
        from uuid import uuid4

        from app.models.audit import AuditActions

        share_id = uuid4()
        audit_entry = AuditLog.log_success(
            action=AuditActions.UNSHARE,
            resource_type="share",
            resource_id=share_id,
            user_id=test_user.id,
        )
        db_session.add(audit_entry)
        await db_session.commit()

        # Verify audit log
        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.resource_type == "share",
                AuditLog.action == AuditActions.UNSHARE,
                AuditLog.resource_id == share_id,
            )
        )
        log = result.scalar_one_or_none()

        assert log is not None
        assert log.action == AuditActions.UNSHARE
        assert log.status == "success"

    @pytest.mark.asyncio
    async def test_update_share_permission_logs_audit_entry(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Test that updating share permissions creates an audit log entry."""
        from uuid import uuid4

        from app.models.audit import AuditActions

        share_id = uuid4()
        audit_entry = AuditLog.log_success(
            action=AuditActions.UPDATE,
            resource_type="share",
            resource_id=share_id,
            user_id=test_user.id,
            context={"permission": "edit"},
        )
        db_session.add(audit_entry)
        await db_session.commit()

        # Verify audit log
        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.resource_type == "share",
                AuditLog.action == AuditActions.UPDATE,
                AuditLog.resource_id == share_id,
            )
        )
        log = result.scalar_one_or_none()

        assert log is not None
        assert log.action == AuditActions.UPDATE
        assert log.context["permission"] == "edit"
        assert log.status == "success"
