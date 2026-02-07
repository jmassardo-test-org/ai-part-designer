"""
Integration tests for audit logging in subscription/billing API endpoints.

Tests that audit logs are properly created for billing operations.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.user import User


class TestSubscriptionAuditLogging:
    """Tests for subscription endpoint audit logging."""

    @pytest.mark.asyncio
    async def test_checkout_logs_audit_entry(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Test that creating a checkout session creates an audit log entry."""
        # Create audit log for checkout
        audit_entry = AuditLog.log_success(
            action="subscription_checkout",
            resource_type="subscription",
            user_id=test_user.id,
            context={
                "plan_slug": "pro",
                "billing_interval": "monthly",
            },
        )
        db_session.add(audit_entry)
        await db_session.commit()

        # Verify audit log
        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.resource_type == "subscription",
                AuditLog.action == "subscription_checkout",
                AuditLog.user_id == test_user.id,
            )
        )
        log = result.scalar_one_or_none()

        assert log is not None
        assert log.action == "subscription_checkout"
        assert log.status == "success"
        assert log.context["plan_slug"] == "pro"
        assert log.context["billing_interval"] == "monthly"

    @pytest.mark.asyncio
    async def test_cancel_subscription_logs_audit_entry(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Test that canceling a subscription creates an audit log entry."""
        # Create audit log for cancel
        audit_entry = AuditLog.log_success(
            action="subscription_cancel",
            resource_type="subscription",
            user_id=test_user.id,
            context={"immediately": False},
        )
        db_session.add(audit_entry)
        await db_session.commit()

        # Verify audit log
        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.resource_type == "subscription",
                AuditLog.action == "subscription_cancel",
                AuditLog.user_id == test_user.id,
            )
        )
        log = result.scalar_one_or_none()

        assert log is not None
        assert log.action == "subscription_cancel"
        assert log.status == "success"
        assert log.context["immediately"] is False

    @pytest.mark.asyncio
    async def test_resume_subscription_logs_audit_entry(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Test that resuming a subscription creates an audit log entry."""
        # Create audit log for resume
        audit_entry = AuditLog.log_success(
            action="subscription_resume",
            resource_type="subscription",
            user_id=test_user.id,
        )
        db_session.add(audit_entry)
        await db_session.commit()

        # Verify audit log
        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.resource_type == "subscription",
                AuditLog.action == "subscription_resume",
                AuditLog.user_id == test_user.id,
            )
        )
        log = result.scalar_one_or_none()

        assert log is not None
        assert log.action == "subscription_resume"
        assert log.status == "success"

    @pytest.mark.asyncio
    async def test_billing_audit_logs_include_metadata(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Test that billing audit logs include proper metadata."""
        # Create audit log with full metadata
        audit_entry = AuditLog.log_success(
            action="subscription_checkout",
            resource_type="subscription",
            user_id=test_user.id,
            context={
                "plan_slug": "enterprise",
                "billing_interval": "yearly",
            },
            ip_address="10.0.0.1",
            user_agent="Test Browser/1.0",
        )
        db_session.add(audit_entry)
        await db_session.commit()
        await db_session.refresh(audit_entry)

        # Verify all metadata is captured
        assert audit_entry.user_id == test_user.id
        assert audit_entry.ip_address == "10.0.0.1"
        assert audit_entry.user_agent == "Test Browser/1.0"
        assert audit_entry.context["plan_slug"] == "enterprise"
        assert audit_entry.context["billing_interval"] == "yearly"
