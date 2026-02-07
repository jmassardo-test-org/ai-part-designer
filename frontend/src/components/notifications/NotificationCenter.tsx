/**
 * Notification Center component.
 *
 * Bell icon with dropdown showing recent notifications.
 * Integrates with WebSocket for real-time updates.
 */

import {
  Bell,
  CheckCheck,
  X,
  Share2,
  MessageCircle,
  AlertCircle,
  CheckCircle,
  Building2,
  Megaphone,
  HardDrive,
  CreditCard,
  ChevronRight,
  Settings,
} from 'lucide-react';
import { useState, useEffect, useRef, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useWebSocket } from '@/contexts/WebSocketContext';
import {
  listNotifications,
  markAsRead,
  markNotificationRead,
  dismissNotification,
  type Notification,
  type NotificationType,
} from '../../lib/api/notifications';

// --- Icon Mapping ---

const NOTIFICATION_ICONS: Partial<Record<NotificationType, typeof Bell>> = {
  design_shared: Share2,
  share_permission_changed: Share2,
  share_revoked: Share2,
  comment_added: MessageCircle,
  comment_reply: MessageCircle,
  comment_mention: MessageCircle,
  annotation_added: MessageCircle,
  annotation_resolved: CheckCircle,
  job_completed: CheckCircle,
  job_failed: AlertCircle,
  org_invite: Building2,
  org_role_changed: Building2,
  org_member_joined: Building2,
  system_announcement: Megaphone,
  storage_limit: HardDrive,
  credit_low: CreditCard,
};

interface NotificationItemProps {
  notification: Notification;
  onRead: (id: string) => void;
  onDismiss: (id: string) => void;
  onClick: () => void;
}

/**
 * Single notification item in the dropdown.
 */
function NotificationItem({
  notification,
  onRead,
  onDismiss,
  onClick,
}: NotificationItemProps) {
  const Icon = NOTIFICATION_ICONS[notification.type] || Bell;
  const isUrgent = notification.priority === 'urgent' || notification.priority === 'high';

  const handleClick = () => {
    if (!notification.is_read) {
      onRead(notification.id);
    }
    onClick();
  };

  const handleDismiss = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDismiss(notification.id);
  };

  const timeAgo = getTimeAgo(notification.created_at);

  return (
    <div
      onClick={handleClick}
      className={`
        relative px-4 py-3 cursor-pointer transition-colors
        ${notification.is_read ? 'bg-white dark:bg-gray-800' : 'bg-blue-50 dark:bg-blue-900/30'}
        hover:bg-gray-50 dark:hover:bg-gray-700
      `}
    >
      <div className="flex gap-3">
        {/* Icon */}
        <div
          className={`
            flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center
            ${isUrgent ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'}
          `}
        >
          <Icon className="h-4 w-4" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <p className={`text-sm ${notification.is_read ? 'text-gray-600 dark:text-gray-400' : 'text-gray-900 dark:text-gray-100 font-medium'}`}>
            {notification.title}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-2">
            {notification.message}
          </p>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs text-gray-400">{timeAgo}</span>
            {notification.actor && (
              <>
                <span className="text-xs text-gray-300 dark:text-gray-600">•</span>
                <span className="text-xs text-gray-500 dark:text-gray-400">{notification.actor.display_name}</span>
              </>
            )}
          </div>
        </div>

        {/* Dismiss button */}
        <button
          onClick={handleDismiss}
          className="flex-shrink-0 p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded opacity-0 group-hover:opacity-100 transition-opacity"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Unread indicator */}
      {!notification.is_read && (
        <div className="absolute left-1.5 top-1/2 -translate-y-1/2 w-2 h-2 bg-blue-500 rounded-full" />
      )}
    </div>
  );
}

/**
 * Get relative time string.
 */
function getTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now.getTime() - date.getTime();

  const minutes = Math.floor(diff / (1000 * 60));
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));

  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days}d ago`;
  return date.toLocaleDateString();
}

interface NotificationCenterProps {
  /** Maximum notifications to show in dropdown */
  maxItems?: number;
}

/**
 * Notification center with bell icon and dropdown.
 * Uses WebSocket for real-time updates with fallback to polling.
 */
export function NotificationCenter({ maxItems = 5 }: NotificationCenterProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const { connected, subscribe, subscribeToRoom } = useWebSocket();

  // Load notifications
  const loadNotifications = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await listNotifications({ page_size: maxItems });
      setNotifications(response.items);
      setUnreadCount(response.unread_count);
      setTotal(response.total);
    } catch (error) {
      console.error('Failed to load notifications:', error);
    } finally {
      setIsLoading(false);
    }
  }, [maxItems]);

  // Subscribe to real-time notification updates via WebSocket
  useEffect(() => {
    if (!connected) return;

    // Subscribe to user's notification room
    subscribeToRoom('notifications');

    // Listen for new notifications
    const unsubNewNotification = subscribe('notification', (message) => {
      const newNotification = message.notification as Notification;
      setNotifications((prev) => [newNotification, ...prev.slice(0, maxItems - 1)]);
      setUnreadCount((prev) => prev + 1);
      setTotal((prev) => prev + 1);
    });

    // Listen for notification read events (from other devices)
    const unsubReadNotification = subscribe('notification_read', (message) => {
      const notificationId = message.notification_id as string;
      setNotifications((prev) =>
        prev.map((n) => (n.id === notificationId ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    });

    // Listen for notification dismissed events
    const unsubDismissNotification = subscribe('notification_dismissed', (message) => {
      const notificationId = message.notification_id as string;
      setNotifications((prev) => {
        const notification = prev.find((n) => n.id === notificationId);
        if (notification && !notification.is_read) {
          setUnreadCount((c) => Math.max(0, c - 1));
        }
        return prev.filter((n) => n.id !== notificationId);
      });
      setTotal((prev) => Math.max(0, prev - 1));
    });

    return () => {
      unsubNewNotification();
      unsubReadNotification();
      unsubDismissNotification();
    };
  }, [connected, subscribe, subscribeToRoom, maxItems]);

  // Load on mount and periodically (fallback when WebSocket not connected)
  useEffect(() => {
    loadNotifications();

    // Poll less frequently when WebSocket is connected
    const pollInterval = connected ? 60000 : 30000;
    const interval = setInterval(loadNotifications, pollInterval);
    return () => clearInterval(interval);
  }, [loadNotifications, connected]);

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleRead = async (id: string) => {
    try {
      await markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (error) {
      console.error('Failed to mark notification as read:', error);
    }
  };

  const handleDismiss = async (id: string) => {
    try {
      await dismissNotification(id);
      setNotifications((prev) => prev.filter((n) => n.id !== id));
      const notification = notifications.find((n) => n.id === id);
      if (notification && !notification.is_read) {
        setUnreadCount((prev) => Math.max(0, prev - 1));
      }
      setTotal((prev) => Math.max(0, prev - 1));
    } catch (error) {
      console.error('Failed to dismiss notification:', error);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (error) {
      console.error('Failed to mark all as read:', error);
    }
  };

  const handleNotificationClick = (notification: Notification) => {
    setIsOpen(false);
    if (notification.action_url) {
      navigate(notification.action_url);
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
        aria-label="Notifications"
      >
        <Bell className="h-5 w-5" />

        {/* Unread badge */}
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold text-white bg-red-500 rounded-full">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-96 bg-white dark:bg-gray-800 rounded-lg shadow-xl border dark:border-gray-700 z-50 overflow-hidden">
          {/* Header */}
          <div className="px-4 py-3 border-b dark:border-gray-700 flex items-center justify-between">
            <h3 className="font-medium text-gray-900 dark:text-gray-100">Notifications</h3>
            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1"
                >
                  <CheckCheck className="h-3 w-3" />
                  Mark all read
                </button>
              )}
              <Link
                to="/settings/notifications"
                className="p-1 text-gray-400 hover:text-gray-600 rounded"
                onClick={() => setIsOpen(false)}
              >
                <Settings className="h-4 w-4" />
              </Link>
            </div>
          </div>

          {/* Notification list */}
          <div className="max-h-96 overflow-y-auto">
            {isLoading && notifications.length === 0 ? (
              <div className="p-8 text-center text-gray-400 dark:text-gray-500">
                Loading...
              </div>
            ) : notifications.length === 0 ? (
              <div className="p-8 text-center">
                <Bell className="h-8 w-8 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
                <p className="text-sm text-gray-500 dark:text-gray-400">No notifications yet</p>
              </div>
            ) : (
              <div className="divide-y">
                {notifications.map((notification) => (
                  <NotificationItem
                    key={notification.id}
                    notification={notification}
                    onRead={handleRead}
                    onDismiss={handleDismiss}
                    onClick={() => handleNotificationClick(notification)}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          {total > maxItems && (
            <div className="px-4 py-2 border-t dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
              <Link
                to="/notifications"
                className="flex items-center justify-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300"
                onClick={() => setIsOpen(false)}
              >
                View all notifications
                <ChevronRight className="h-4 w-4" />
              </Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default NotificationCenter;
