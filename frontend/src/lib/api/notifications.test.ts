/**
 * Notifications API client tests.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiClient } from './client';
import {
  listNotifications,
  getUnreadCount,
  getNotification,
  markAsRead,
  markNotificationRead,
  dismissNotification,
  getPreferences,
  updatePreference,
  NOTIFICATION_TYPE_LABELS,
  NOTIFICATION_PRIORITY_COLORS,
} from './notifications';

// Mock the apiClient
vi.mock('./client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('notifications API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('listNotifications', () => {
    it('fetches notifications with default params', async () => {
      const mockResponse = {
        items: [
          {
            id: 'notif-1',
            type: 'design_shared',
            priority: 'normal',
            title: 'Design Shared',
            message: 'Alex shared a design with you',
            action_url: '/designs/123',
            action_label: 'View Design',
            actor: { id: 'user-1', display_name: 'Alex' },
            entity_type: 'design',
            entity_id: '123',
            data: null,
            is_read: false,
            read_at: null,
            created_at: '2025-01-27T10:00:00Z',
          },
        ],
        total: 1,
        unread_count: 1,
        page: 1,
        page_size: 20,
        has_more: false,
      };

      (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      const result = await listNotifications();

      expect(apiClient.get).toHaveBeenCalledWith('/notifications', { params: {} });
      expect(result.items).toHaveLength(1);
      expect(result.unread_count).toBe(1);
    });

    it('fetches notifications with custom params', async () => {
      const mockResponse = {
        items: [],
        total: 0,
        unread_count: 0,
        page: 2,
        page_size: 10,
        has_more: false,
      };

      (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      await listNotifications({ page: 2, page_size: 10, unread_only: true });

      expect(apiClient.get).toHaveBeenCalledWith('/notifications', {
        params: { page: 2, page_size: 10, unread_only: true },
      });
    });
  });

  describe('getUnreadCount', () => {
    it('returns unread notification count', async () => {
      (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: { count: 5 },
      });

      const result = await getUnreadCount();

      expect(apiClient.get).toHaveBeenCalledWith('/notifications/unread-count');
      expect(result).toBe(5);
    });

    it('returns zero when no unread notifications', async () => {
      (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: { count: 0 },
      });

      const result = await getUnreadCount();

      expect(result).toBe(0);
    });
  });

  describe('getNotification', () => {
    it('fetches a specific notification', async () => {
      const mockNotification = {
        id: 'notif-123',
        type: 'job_completed',
        priority: 'normal',
        title: 'Job Complete',
        message: 'Your design generation is ready',
        action_url: '/designs/456',
        action_label: 'View',
        actor: null,
        entity_type: 'job',
        entity_id: '789',
        data: { job_type: 'generate' },
        is_read: false,
        read_at: null,
        created_at: '2025-01-27T12:00:00Z',
      };

      (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockNotification,
      });

      const result = await getNotification('notif-123');

      expect(apiClient.get).toHaveBeenCalledWith('/notifications/notif-123');
      expect(result.id).toBe('notif-123');
      expect(result.type).toBe('job_completed');
    });
  });

  describe('markAsRead', () => {
    it('marks specific notifications as read', async () => {
      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: { marked_read: 3 },
      });

      const result = await markAsRead(['notif-1', 'notif-2', 'notif-3']);

      expect(apiClient.post).toHaveBeenCalledWith('/notifications/mark-read', {
        notification_ids: ['notif-1', 'notif-2', 'notif-3'],
      });
      expect(result.marked_read).toBe(3);
    });

    it('marks all as read when no ids provided', async () => {
      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: { marked_read: 10 },
      });

      const result = await markAsRead();

      expect(apiClient.post).toHaveBeenCalledWith('/notifications/mark-read', {
        notification_ids: undefined,
      });
      expect(result.marked_read).toBe(10);
    });
  });

  describe('markNotificationRead', () => {
    it('marks a single notification as read', async () => {
      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({});

      await markNotificationRead('notif-123');

      expect(apiClient.post).toHaveBeenCalledWith('/notifications/notif-123/read');
    });
  });

  describe('dismissNotification', () => {
    it('dismisses a notification', async () => {
      (apiClient.delete as ReturnType<typeof vi.fn>).mockResolvedValueOnce({});

      await dismissNotification('notif-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/notifications/notif-123');
    });
  });

  describe('getPreferences', () => {
    it('fetches notification preferences', async () => {
      const mockPreferences = [
        {
          notification_type: 'design_shared',
          in_app_enabled: true,
          email_enabled: true,
          push_enabled: false,
          email_digest: 'daily',
        },
        {
          notification_type: 'job_completed',
          in_app_enabled: true,
          email_enabled: false,
          push_enabled: true,
          email_digest: null,
        },
      ];

      (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: { preferences: mockPreferences },
      });

      const result = await getPreferences();

      expect(apiClient.get).toHaveBeenCalledWith('/notifications/preferences');
      expect(result).toHaveLength(2);
      expect(result[0].notification_type).toBe('design_shared');
    });
  });

  describe('updatePreference', () => {
    it('updates a notification preference', async () => {
      const updatedPref = {
        notification_type: 'comment_added',
        in_app_enabled: true,
        email_enabled: false,
        push_enabled: false,
        email_digest: null,
      };

      (apiClient.patch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: updatedPref,
      });

      const result = await updatePreference('comment_added', {
        email_enabled: false,
        push_enabled: false,
      });

      expect(apiClient.patch).toHaveBeenCalledWith(
        '/notifications/preferences/comment_added',
        { email_enabled: false, push_enabled: false }
      );
      expect(result.email_enabled).toBe(false);
    });

    it('updates email digest preference', async () => {
      const updatedPref = {
        notification_type: 'system_announcement',
        in_app_enabled: true,
        email_enabled: true,
        push_enabled: false,
        email_digest: 'weekly',
      };

      (apiClient.patch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: updatedPref,
      });

      const result = await updatePreference('system_announcement', {
        email_digest: 'weekly',
      });

      expect(result.email_digest).toBe('weekly');
    });
  });
});

describe('notification constants', () => {
  describe('NOTIFICATION_TYPE_LABELS', () => {
    it('has labels for all notification types', () => {
      expect(NOTIFICATION_TYPE_LABELS.design_shared).toBe('Design Shared');
      expect(NOTIFICATION_TYPE_LABELS.job_completed).toBe('Job Completed');
      expect(NOTIFICATION_TYPE_LABELS.comment_added).toBe('New Comment');
      expect(NOTIFICATION_TYPE_LABELS.org_invite).toBe('Organization Invite');
      expect(NOTIFICATION_TYPE_LABELS.storage_limit).toBe('Storage Warning');
    });

    it('has human-readable labels', () => {
      Object.values(NOTIFICATION_TYPE_LABELS).forEach((label) => {
        expect(typeof label).toBe('string');
        expect(label.length).toBeGreaterThan(0);
      });
    });
  });

  describe('NOTIFICATION_PRIORITY_COLORS', () => {
    it('has colors for all priority levels', () => {
      expect(NOTIFICATION_PRIORITY_COLORS.low).toBeDefined();
      expect(NOTIFICATION_PRIORITY_COLORS.normal).toBeDefined();
      expect(NOTIFICATION_PRIORITY_COLORS.high).toBeDefined();
      expect(NOTIFICATION_PRIORITY_COLORS.urgent).toBeDefined();
    });

    it('has valid hex color values', () => {
      Object.values(NOTIFICATION_PRIORITY_COLORS).forEach((color) => {
        expect(color).toMatch(/^#[0-9a-fA-F]{6}$/);
      });
    });
  });
});
