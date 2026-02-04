"""Add notification tables

Revision ID: 014_notifications
Revises: 013_add_org_to_projects
Create Date: 2026-01-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '014_notifications'
down_revision: Union[str, None] = '013_add_org_to_projects'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create notification_type enum if it doesn't exist
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE notificationtype AS ENUM (
                'design_shared',
                'share_permission_changed',
                'share_revoked',
                'comment_added',
                'comment_reply',
                'comment_mention',
                'annotation_added',
                'annotation_resolved',
                'job_completed',
                'job_failed',
                'org_invite',
                'org_role_changed',
                'org_member_joined',
                'system_announcement'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create notifications table if it doesn't exist
    op.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            notification_type notificationtype NOT NULL,
            title VARCHAR(255) NOT NULL,
            message TEXT NOT NULL,
            data JSONB,
            is_read BOOLEAN NOT NULL DEFAULT false,
            read_at TIMESTAMP WITH TIME ZONE,
            expires_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    
    op.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON notifications(user_id, is_read) WHERE is_read = false")
    op.execute("CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(notification_type)")
    
    # Create notification_preferences table if it doesn't exist
    op.execute("""
        CREATE TABLE IF NOT EXISTS notification_preferences (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            notification_type notificationtype NOT NULL,
            in_app_enabled BOOLEAN NOT NULL DEFAULT true,
            email_enabled BOOLEAN NOT NULL DEFAULT true,
            push_enabled BOOLEAN NOT NULL DEFAULT false,
            email_digest VARCHAR(20),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            UNIQUE(user_id, notification_type)
        )
    """)
    
    op.execute("CREATE INDEX IF NOT EXISTS idx_notification_preferences_user_id ON notification_preferences(user_id)")


def downgrade() -> None:
    op.drop_table('notification_preferences')
    op.drop_table('notifications')
    op.execute("DROP TYPE IF EXISTS notificationtype")
