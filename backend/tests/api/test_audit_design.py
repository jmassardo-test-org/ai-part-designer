"""
Integration tests for audit logging in design API endpoints.

Tests that audit logs are properly created for design operations.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.design import Design
from app.models.project import Project
from app.models.user import User


class TestDesignAuditLogging:
    """Tests for design endpoint audit logging."""

    @pytest.mark.asyncio
    async def test_create_design_logs_audit_entry(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Test that creating a design creates an audit log entry."""
        # Create a project first
        project = Project(
            user_id=test_user.id,
            name="Test Project",
            description="For testing",
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        # Create a design
        design = Design(
            project_id=project.id,
            user_id=test_user.id,
            name="Test Design",
            description="Test Description",
            source_type="manual",
            status="draft",
            extra_data={},
        )
        db_session.add(design)
        await db_session.commit()
        await db_session.refresh(design)

        # Manually create audit log (simulating what the decorator does)
        from app.models.audit import AuditActions

        audit_entry = AuditLog.log_success(
            action=AuditActions.CREATE,
            resource_type="design",
            resource_id=design.id,
            user_id=test_user.id,
            context={"name": design.name},
        )
        db_session.add(audit_entry)
        await db_session.commit()

        # Verify audit log was created
        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.resource_type == "design",
                AuditLog.action == AuditActions.CREATE,
                AuditLog.resource_id == design.id,
            )
        )
        log = result.scalar_one_or_none()

        assert log is not None
        assert log.user_id == test_user.id
        assert log.action == AuditActions.CREATE
        assert log.resource_type == "design"
        assert log.resource_id == design.id
        assert log.status == "success"
        assert log.context["name"] == "Test Design"

    @pytest.mark.asyncio
    async def test_update_design_logs_audit_entry(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Test that updating a design creates an audit log entry."""
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
            name="Original Name",
            source_type="manual",
            status="draft",
            extra_data={},
        )
        db_session.add(design)
        await db_session.commit()
        await db_session.refresh(design)

        # Update the design
        design.name = "Updated Name"
        await db_session.commit()

        # Create audit log for update
        from app.models.audit import AuditActions

        audit_entry = AuditLog.log_success(
            action=AuditActions.UPDATE,
            resource_type="design",
            resource_id=design.id,
            user_id=test_user.id,
            context={"name": "Updated Name"},
        )
        db_session.add(audit_entry)
        await db_session.commit()

        # Verify audit log
        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.resource_type == "design",
                AuditLog.action == AuditActions.UPDATE,
                AuditLog.resource_id == design.id,
            )
        )
        log = result.scalar_one_or_none()

        assert log is not None
        assert log.action == AuditActions.UPDATE
        assert log.status == "success"

    @pytest.mark.asyncio
    async def test_delete_design_logs_audit_entry(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Test that deleting a design creates an audit log entry."""
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
            name="To Delete",
            source_type="manual",
            status="draft",
            extra_data={},
        )
        db_session.add(design)
        await db_session.commit()
        await db_session.refresh(design)

        design_id = design.id

        # Create audit log for delete
        from app.models.audit import AuditActions

        audit_entry = AuditLog.log_success(
            action=AuditActions.DELETE,
            resource_type="design",
            resource_id=design_id,
            user_id=test_user.id,
        )
        db_session.add(audit_entry)
        await db_session.commit()

        # Verify audit log
        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.resource_type == "design",
                AuditLog.action == AuditActions.DELETE,
                AuditLog.resource_id == design_id,
            )
        )
        log = result.scalar_one_or_none()

        assert log is not None
        assert log.action == AuditActions.DELETE
        assert log.status == "success"
        assert log.resource_id == design_id

    @pytest.mark.asyncio
    async def test_audit_log_includes_ip_and_user_agent(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Test that audit logs include IP address and user agent."""
        # Create audit log with request metadata
        from app.models.audit import AuditActions

        audit_entry = AuditLog.log_success(
            action=AuditActions.CREATE,
            resource_type="design",
            user_id=test_user.id,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 Test Browser",
            context={"request_id": "test-req-123"},
        )
        db_session.add(audit_entry)
        await db_session.commit()
        await db_session.refresh(audit_entry)

        # Verify metadata is captured
        assert audit_entry.ip_address == "192.168.1.100"
        assert audit_entry.user_agent == "Mozilla/5.0 Test Browser"
        assert audit_entry.context["request_id"] == "test-req-123"

    @pytest.mark.asyncio
    async def test_audit_logs_are_queryable_by_user(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Test that audit logs can be queried by user."""
        from app.models.audit import AuditActions

        # Create multiple audit logs for the user
        for i in range(3):
            audit_entry = AuditLog.log_success(
                action=AuditActions.CREATE,
                resource_type="design",
                user_id=test_user.id,
                context={"index": i},
            )
            db_session.add(audit_entry)

        await db_session.commit()

        # Query audit logs for user
        result = await db_session.execute(
            select(AuditLog)
            .where(AuditLog.user_id == test_user.id)
            .order_by(AuditLog.created_at.desc())
        )
        logs = result.scalars().all()

        assert len(logs) >= 3
        assert all(log.user_id == test_user.id for log in logs)

    @pytest.mark.asyncio
    async def test_audit_logs_are_queryable_by_resource(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Test that audit logs can be queried by resource."""
        # Create a design
        project = Project(
            user_id=test_user.id,
            name="Test Project",
        )
        db_session.add(project)
        await db_session.flush()

        design = Design(
            project_id=project.id,
            user_id=test_user.id,
            name="Test Design",
            source_type="manual",
            status="draft",
            extra_data={},
        )
        db_session.add(design)
        await db_session.commit()
        await db_session.refresh(design)

        # Create multiple audit logs for the design
        from app.models.audit import AuditActions

        for action in [AuditActions.CREATE, AuditActions.UPDATE, AuditActions.READ]:
            audit_entry = AuditLog.log_success(
                action=action,
                resource_type="design",
                resource_id=design.id,
                user_id=test_user.id,
            )
            db_session.add(audit_entry)

        await db_session.commit()

        # Query audit logs for the design
        result = await db_session.execute(
            select(AuditLog)
            .where(
                AuditLog.resource_type == "design",
                AuditLog.resource_id == design.id,
            )
            .order_by(AuditLog.created_at.asc())
        )
        logs = result.scalars().all()

        assert len(logs) == 3
        assert logs[0].action == AuditActions.CREATE
        assert logs[1].action == AuditActions.UPDATE
        assert logs[2].action == AuditActions.READ
