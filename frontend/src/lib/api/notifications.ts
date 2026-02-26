/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Notifications API client.
 *
 * Handles user notification management.
 */

/** Backend notification type enum values. */
export type NotificationType =
  | 'design_shared'
  | 'share_permission_changed'
  | 'share_revoked'
  | 'comment_added'
  | 'comment_reply'
  | 'comment_mention'
  | 'annotation_added'
  | 'annotation_resolved'
  | 'job_completed'
  | 'job_failed'
  | 'org_invite'
  | 'org_role_changed'
  | 'org_member_joined'
  | 'system_announcement'
  | 'storage_limit'
  | 'credit_low';

/** Notification entity. */
export interface Notification {
  [key: string]: any;
  id: string;
  type: string;
  title: string;
  message: string;
  read: boolean;
  created_at: string;
  action_url?: string;
}

/** Notifications API methods. */
export const notificationsApi: any = {
  async list(token?: string): Promise<Notification[]> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/notifications', { headers });
    if (!resp.ok) throw new Error(`Failed to list notifications: ${resp.status}`);
    return resp.json();
  },
  async markRead(notificationId: string, token?: string): Promise<void> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(`/api/v1/notifications/${notificationId}/read`, { method: 'POST', headers });
    if (!resp.ok) throw new Error(`Failed to mark notification read: ${resp.status}`);
  },
  async markAllRead(token?: string): Promise<void> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/notifications/read-all', { method: 'POST', headers });
    if (!resp.ok) throw new Error(`Failed to mark all read: ${resp.status}`);
  },
};

/** List all notifications. Alias for notificationsApi.list. */
export const listNotifications = notificationsApi.list;

/** Mark a single notification as read. Alias for notificationsApi.markRead. */
export const markAsRead = notificationsApi.markRead;

/** Mark a notification as read (alias). */
export const markNotificationRead = notificationsApi.markRead;

/** Dismiss (mark read) a notification. */
export const dismissNotification = notificationsApi.markRead;

/** Notification preference from API. */
export interface NotificationPreference {
  notification_type: string;
  in_app_enabled: boolean;
  email_enabled: boolean;
  push_enabled: boolean;
  email_digest: string | null;
}

/** Get all notification preferences. */
export async function getNotificationPreferences(
  token?: string
): Promise<NotificationPreference[]> {
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch('/api/v1/notifications/preferences', { headers });
  if (!resp.ok) throw new Error(`Failed to get preferences: ${resp.status}`);
  const data = await resp.json();
  return data.preferences ?? [];
}

/** Update a single notification preference by type. */
export async function updateNotificationPreference(
  notificationType: NotificationType,
  updates: { in_app_enabled?: boolean; email_enabled?: boolean; push_enabled?: boolean; email_digest?: string },
  token?: string
): Promise<NotificationPreference> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`/api/v1/notifications/preferences/${notificationType}`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify(updates),
  });
  if (!resp.ok) throw new Error(`Failed to update preference: ${resp.status}`);
  return resp.json();
}
