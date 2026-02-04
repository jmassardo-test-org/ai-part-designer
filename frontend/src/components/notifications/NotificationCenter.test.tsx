/**
 * NotificationCenter Component Tests
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { NotificationCenter } from './NotificationCenter';

// Mock navigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock WebSocket context
const mockSubscribe = vi.fn(() => vi.fn());
const mockSubscribeToRoom = vi.fn();
vi.mock('@/contexts/WebSocketContext', () => ({
  useWebSocket: () => ({
    connected: true,
    connecting: false,
    subscribe: mockSubscribe,
    subscribeToRoom: mockSubscribeToRoom,
    send: vi.fn(),
    reconnect: vi.fn(),
    unsubscribeFromRoom: vi.fn(),
    subscribeToJob: vi.fn(),
  }),
}));

// Mock notifications API
const mockListNotifications = vi.fn();
const mockMarkNotificationRead = vi.fn();
const mockMarkAsRead = vi.fn();
const mockDismissNotification = vi.fn();

vi.mock('../../lib/api/notifications', () => ({
  listNotifications: (...args: unknown[]) => mockListNotifications(...args),
  markNotificationRead: (...args: unknown[]) => mockMarkNotificationRead(...args),
  markAsRead: (...args: unknown[]) => mockMarkAsRead(...args),
  dismissNotification: (...args: unknown[]) => mockDismissNotification(...args),
}));

// Sample notification data
const mockNotifications = [
  {
    id: 'notif-1',
    type: 'job_completed',
    title: 'Design generation complete',
    message: 'Your box design is ready to download',
    is_read: false,
    created_at: new Date().toISOString(),
    action_url: '/designs/123',
    priority: 'normal',
  },
  {
    id: 'notif-2',
    type: 'design_shared',
    title: 'Design shared with you',
    message: 'John shared "Bracket v2" with you',
    is_read: true,
    created_at: new Date(Date.now() - 3600000).toISOString(),
    action_url: '/designs/456',
    priority: 'normal',
  },
];

const renderComponent = () => {
  return render(
    <BrowserRouter>
      <NotificationCenter />
    </BrowserRouter>
  );
};

describe('NotificationCenter', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListNotifications.mockResolvedValue({
      items: mockNotifications,
      unread_count: 1,
      total: 2,
    });
    mockMarkNotificationRead.mockResolvedValue(undefined);
    mockMarkAsRead.mockResolvedValue(undefined);
    mockDismissNotification.mockResolvedValue(undefined);
  });

  describe('Bell Button', () => {
    it('renders notification bell', () => {
      renderComponent();
      expect(screen.getByRole('button', { name: /notifications/i })).toBeInTheDocument();
    });

    it('shows unread badge when there are unread notifications', async () => {
      renderComponent();
      
      await waitFor(() => {
        expect(screen.getByText('1')).toBeInTheDocument();
      });
    });

    it('hides badge when no unread notifications', async () => {
      mockListNotifications.mockResolvedValue({
        items: mockNotifications.map(n => ({ ...n, is_read: true })),
        unread_count: 0,
        total: 2,
      });
      
      renderComponent();
      
      await waitFor(() => {
        expect(mockListNotifications).toHaveBeenCalled();
      });
      
      expect(screen.queryByText('1')).not.toBeInTheDocument();
    });
  });

  describe('Dropdown', () => {
    it('opens dropdown on bell click', async () => {
      const user = userEvent.setup();
      renderComponent();
      
      await waitFor(() => {
        expect(mockListNotifications).toHaveBeenCalled();
      });
      
      await user.click(screen.getByRole('button', { name: /notifications/i }));
      
      expect(screen.getByText('Notifications')).toBeInTheDocument();
    });

    it('displays notifications in dropdown', async () => {
      const user = userEvent.setup();
      renderComponent();
      
      await waitFor(() => {
        expect(mockListNotifications).toHaveBeenCalled();
      });
      
      await user.click(screen.getByRole('button', { name: /notifications/i }));
      
      expect(screen.getByText('Design generation complete')).toBeInTheDocument();
      expect(screen.getByText('Design shared with you')).toBeInTheDocument();
    });

    it('closes dropdown on outside click', async () => {
      const user = userEvent.setup();
      renderComponent();
      
      await waitFor(() => {
        expect(mockListNotifications).toHaveBeenCalled();
      });
      
      await user.click(screen.getByRole('button', { name: /notifications/i }));
      expect(screen.getByText('Notifications')).toBeInTheDocument();
      
      // Click outside
      fireEvent.mouseDown(document.body);
      
      await waitFor(() => {
        expect(screen.queryByText('Notifications')).not.toBeInTheDocument();
      });
    });
  });

  describe('Empty State', () => {
    it('shows empty state when no notifications', async () => {
      mockListNotifications.mockResolvedValue({
        items: [],
        unread_count: 0,
        total: 0,
      });
      
      const user = userEvent.setup();
      renderComponent();
      
      await waitFor(() => {
        expect(mockListNotifications).toHaveBeenCalled();
      });
      
      await user.click(screen.getByRole('button', { name: /notifications/i }));
      
      expect(screen.getByText(/no notifications/i)).toBeInTheDocument();
    });
  });

  describe('Mark as Read', () => {
    it('marks notification as read on click', async () => {
      const user = userEvent.setup();
      renderComponent();
      
      await waitFor(() => {
        expect(mockListNotifications).toHaveBeenCalled();
      });
      
      await user.click(screen.getByRole('button', { name: /notifications/i }));
      
      // Click on unread notification
      await user.click(screen.getByText('Design generation complete'));
      
      expect(mockMarkNotificationRead).toHaveBeenCalledWith('notif-1');
    });

    it('shows mark all as read button when unread notifications exist', async () => {
      const user = userEvent.setup();
      renderComponent();
      
      await waitFor(() => {
        expect(mockListNotifications).toHaveBeenCalled();
      });
      
      await user.click(screen.getByRole('button', { name: /notifications/i }));
      
      expect(screen.getByText(/mark all read/i)).toBeInTheDocument();
    });

    it('calls markAsRead when clicking mark all', async () => {
      const user = userEvent.setup();
      renderComponent();
      
      await waitFor(() => {
        expect(mockListNotifications).toHaveBeenCalled();
      });
      
      await user.click(screen.getByRole('button', { name: /notifications/i }));
      await user.click(screen.getByText(/mark all read/i));
      
      expect(mockMarkAsRead).toHaveBeenCalled();
    });
  });

  describe('Navigation', () => {
    it('navigates to action_url on notification click', async () => {
      const user = userEvent.setup();
      renderComponent();
      
      await waitFor(() => {
        expect(mockListNotifications).toHaveBeenCalled();
      });
      
      await user.click(screen.getByRole('button', { name: /notifications/i }));
      await user.click(screen.getByText('Design generation complete'));
      
      expect(mockNavigate).toHaveBeenCalledWith('/designs/123');
    });

    it('closes dropdown after navigation', async () => {
      const user = userEvent.setup();
      renderComponent();
      
      await waitFor(() => {
        expect(mockListNotifications).toHaveBeenCalled();
      });
      
      await user.click(screen.getByRole('button', { name: /notifications/i }));
      expect(screen.getByText('Notifications')).toBeInTheDocument();
      
      await user.click(screen.getByText('Design generation complete'));
      
      await waitFor(() => {
        expect(screen.queryByText('Notifications')).not.toBeInTheDocument();
      });
    });
  });

  describe('WebSocket Integration', () => {
    it('subscribes to notification room on mount', async () => {
      renderComponent();
      
      await waitFor(() => {
        expect(mockSubscribeToRoom).toHaveBeenCalledWith('notifications');
      });
    });

    it('subscribes to notification events', async () => {
      renderComponent();
      
      await waitFor(() => {
        expect(mockSubscribe).toHaveBeenCalledWith('notification', expect.any(Function));
        expect(mockSubscribe).toHaveBeenCalledWith('notification_read', expect.any(Function));
        expect(mockSubscribe).toHaveBeenCalledWith('notification_dismissed', expect.any(Function));
      });
    });
  });

  describe('Settings Link', () => {
    it('shows settings link in dropdown header', async () => {
      const user = userEvent.setup();
      renderComponent();
      
      await waitFor(() => {
        expect(mockListNotifications).toHaveBeenCalled();
      });
      
      await user.click(screen.getByRole('button', { name: /notifications/i }));
      
      // Settings link is an icon-only link
      const settingsLink = screen.getByRole('link');
      expect(settingsLink).toHaveAttribute('href', '/settings/notifications');
    });
  });
});
