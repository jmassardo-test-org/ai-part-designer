/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Notifications API client.
 *
 * Handles user notification management.
 */

/** Notification type. */
export type NotificationType = 'info' | 'warning' | 'error' | 'success' | 'system' | string;

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
