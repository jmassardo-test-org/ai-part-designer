/**
 * Settings Page - User profile and preferences.
 */

import {
  User,
  Lock,
  Bell,
  Trash2,
  Save,
  Camera,
  Eye,
  EyeOff,
  Check,
  X,
  AlertTriangle,
  Loader2,
  CreditCard,
  Link2,
  Unlink,
  BellOff,
  FileText,
} from 'lucide-react';
import { useState, useEffect } from 'react';
import { useSearchParams, useLocation } from 'react-router-dom';
import AuditLogViewer from '@/components/settings/AuditLogViewer';
import { useAuth } from '@/contexts/AuthContext';
import { useSubscription } from '@/hooks/useSubscription';
import { getNotificationPreferences, updateNotificationPreference } from '@/lib/api/notifications';
import { oauthApi, OAuthConnection } from '@/lib/api/oauth';

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

// =============================================================================
// Billing Section Component
// =============================================================================

function BillingSection() {
  const {
    subscription,
    usage,
    isLoading,
    tier,
    isPremium,
    isCanceling,
    cancelSubscription,
    resumeSubscription,
    redirectToPortal,
    redirectToCheckout,
  } = useSubscription();

  const [cancelLoading, setCancelLoading] = useState(false);
  const [resumeLoading, setResumeLoading] = useState(false);
  const [upgradeLoading, setUpgradeLoading] = useState(false);
  const [upgradeError, setUpgradeError] = useState<string | null>(null);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);

  const handleUpgrade = async () => {
    try {
      setUpgradeLoading(true);
      setUpgradeError(null);
      await redirectToCheckout('pro');
    } catch (err) {
      console.error('Failed to initiate checkout:', err);
      setUpgradeError('Failed to start upgrade process. Please try again.');
    } finally {
      setUpgradeLoading(false);
    }
  };

  const handleCancel = async () => {
    try {
      setCancelLoading(true);
      await cancelSubscription(false);
      setShowCancelConfirm(false);
    } catch (err) {
      console.error('Failed to cancel:', err);
    } finally {
      setCancelLoading(false);
    }
  };

  const handleResume = async () => {
    try {
      setResumeLoading(true);
      await resumeSubscription();
    } catch (err) {
      console.error('Failed to resume:', err);
    } finally {
      setResumeLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">Subscription & Billing</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
          Manage your subscription plan and billing details.
        </p>
      </div>

      {/* Current Plan */}
      <div className="border dark:border-gray-700 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-medium text-gray-900 dark:text-gray-100 capitalize">
                {tier} Plan
              </span>
              {isPremium && (
                <span className="px-2 py-0.5 bg-cyan-100 text-cyan-700 text-xs font-medium rounded">
                  Premium
                </span>
              )}
              {isCanceling && (
                <span className="px-2 py-0.5 bg-amber-100 text-amber-700 text-xs font-medium rounded">
                  Cancels {subscription?.current_period_end ? new Date(subscription.current_period_end).toLocaleDateString() : 'soon'}
                </span>
              )}
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              {isPremium && subscription?.current_period_end
                ? `Next billing: ${new Date(subscription.current_period_end).toLocaleDateString()}`
                : 'Free forever'}
            </p>
            {upgradeError && (
              <p className="text-sm text-red-500 mt-1">{upgradeError}</p>
            )}
          </div>
          <div className="flex gap-2">
            {!isPremium && (
              <button
                onClick={handleUpgrade}
                disabled={upgradeLoading}
                className="px-4 py-2 bg-cyan-600 text-white text-sm font-medium rounded-lg hover:bg-cyan-700 disabled:opacity-50"
              >
                {upgradeLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Upgrade to Pro'}
              </button>
            )}
            {isPremium && !isCanceling && (
              <button
                onClick={() => setShowCancelConfirm(true)}
                className="px-4 py-2 text-gray-600 dark:text-gray-400 text-sm font-medium hover:text-gray-900 dark:hover:text-gray-200"
              >
                Cancel Plan
              </button>
            )}
            {isCanceling && (
              <button
                onClick={handleResume}
                disabled={resumeLoading}
                className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:opacity-50"
              >
                {resumeLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Resume Subscription'}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Usage Stats */}
      {usage && (
        <div className="border dark:border-gray-700 rounded-lg p-4">
          <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-4">Usage This Period</h3>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {usage.generations_this_period}
                <span className="text-sm text-gray-400 dark:text-gray-500 font-normal">/{usage.generations_limit}</span>
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Generations</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {usage.storage_used_gb.toFixed(1)}
                <span className="text-sm text-gray-400 dark:text-gray-500 font-normal">/{usage.storage_limit_gb} GB</span>
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Storage</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {usage.credits_remaining}
                <span className="text-sm text-gray-400 dark:text-gray-500 font-normal">/{usage.credits_total}</span>
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Credits</p>
            </div>
          </div>
        </div>
      )}

      {/* Manage Billing */}
      {isPremium && (
        <div className="border dark:border-gray-700 rounded-lg p-4">
          <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-2">Payment Method</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            Update your payment method or view invoices in the billing portal.
          </p>
          <button
            onClick={() => redirectToPortal()}
            className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-sm font-medium rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
          >
            Manage Billing
          </button>
        </div>
      )}

      {/* Cancel Confirmation Modal */}
      {showCancelConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
              Cancel Subscription?
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              Your subscription will remain active until{' '}
              {subscription?.current_period_end
                ? new Date(subscription.current_period_end).toLocaleDateString()
                : 'the end of your billing period'}
              . After that, you'll be downgraded to the Free plan.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowCancelConfirm(false)}
                className="flex-1 px-4 py-2 border dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                Keep Subscription
              </button>
              <button
                onClick={handleCancel}
                disabled={cancelLoading}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                {cancelLoading ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : 'Cancel'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Connected Accounts Section Component
// =============================================================================

function ConnectedAccountsSection() {
  const [connections, setConnections] = useState<OAuthConnection[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Fetch connected accounts on mount
  useEffect(() => {
    const fetchConnections = async () => {
      try {
        const response = await oauthApi.getConnections();
        setConnections(response.connections);
      } catch (err) {
        console.error('Failed to fetch OAuth connections:', err);
        setError('Failed to load connected accounts');
      } finally {
        setIsLoading(false);
      }
    };

    fetchConnections();
  }, []);

  const handleConnect = async (provider: 'google' | 'github') => {
    setActionLoading(provider);
    setError(null);
    try {
      const response = await oauthApi.initiateLink(provider);
      // Redirect to OAuth provider for linking
      window.location.href = response.authorization_url;
    } catch (err) {
      console.error(`Failed to initiate ${provider} link:`, err);
      setError(`Failed to connect ${provider}. Please try again.`);
      setActionLoading(null);
    }
  };

  const handleDisconnect = async (provider: string) => {
    // Check if this is the last connection and user has no password
    if (connections.length <= 1) {
      setError('Cannot disconnect your only sign-in method. Add another method first.');
      return;
    }

    setActionLoading(provider);
    setError(null);
    try {
      await oauthApi.unlinkProvider(provider);
      setConnections(prev => prev.filter(c => c.provider !== provider));
      setSuccessMessage(`${provider.charAt(0).toUpperCase() + provider.slice(1)} disconnected successfully`);
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      console.error(`Failed to disconnect ${provider}:`, err);
      setError(`Failed to disconnect ${provider}. Please try again.`);
    } finally {
      setActionLoading(null);
    }
  };

  const isConnected = (provider: string) =>
    connections.some(c => c.provider === provider);

  const getConnection = (provider: string) =>
    connections.find(c => c.provider === provider);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">Connected Accounts</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
          Connect your social accounts for easier sign-in.
        </p>
      </div>

      {/* Error Message */}
      {error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Success Message */}
      {successMessage && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-green-50 border border-green-200 text-green-700 text-sm">
          <Check className="w-4 h-4 flex-shrink-0" />
          {successMessage}
        </div>
      )}

      {/* Google */}
      <div className="border dark:border-gray-700 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white dark:bg-gray-200 border dark:border-gray-600 rounded-lg flex items-center justify-center">
              <svg className="h-5 w-5" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
            </div>
            <div>
              <p className="font-medium text-gray-900 dark:text-gray-100">Google</p>
              {isConnected('google') ? (
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {getConnection('google')?.provider_email || 'Connected'}
                </p>
              ) : (
                <p className="text-sm text-gray-500 dark:text-gray-400">Not connected</p>
              )}
            </div>
          </div>
          {isConnected('google') ? (
            <button
              onClick={() => handleDisconnect('google')}
              disabled={actionLoading === 'google'}
              className="flex items-center gap-2 px-4 py-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg disabled:opacity-50"
            >
              {actionLoading === 'google' ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Unlink className="w-4 h-4" />
              )}
              Disconnect
            </button>
          ) : (
            <button
              onClick={() => handleConnect('google')}
              disabled={actionLoading === 'google'}
              className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg disabled:opacity-50"
            >
              {actionLoading === 'google' ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Link2 className="w-4 h-4" />
              )}
              Connect
            </button>
          )}
        </div>
      </div>

      {/* GitHub */}
      <div className="border dark:border-gray-700 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gray-900 rounded-lg flex items-center justify-center">
              <svg className="h-5 w-5 text-white" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
              </svg>
            </div>
            <div>
              <p className="font-medium text-gray-900 dark:text-gray-100">GitHub</p>
              {isConnected('github') ? (
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {getConnection('github')?.provider_username || getConnection('github')?.provider_email || 'Connected'}
                </p>
              ) : (
                <p className="text-sm text-gray-500 dark:text-gray-400">Not connected</p>
              )}
            </div>
          </div>
          {isConnected('github') ? (
            <button
              onClick={() => handleDisconnect('github')}
              disabled={actionLoading === 'github'}
              className="flex items-center gap-2 px-4 py-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg disabled:opacity-50"
            >
              {actionLoading === 'github' ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Unlink className="w-4 h-4" />
              )}
              Disconnect
            </button>
          ) : (
            <button
              onClick={() => handleConnect('github')}
              disabled={actionLoading === 'github'}
              className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg disabled:opacity-50"
            >
              {actionLoading === 'github' ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Link2 className="w-4 h-4" />
              )}
              Connect
            </button>
          )}
        </div>
      </div>

      {/* Info */}
      <p className="text-sm text-gray-500 dark:text-gray-400">
        Connecting accounts allows you to sign in with either method. You must have at least one
        sign-in method connected to your account.
      </p>
    </div>
  );
}

// =============================================================================
// Types
// =============================================================================

interface NotificationPreferences {
  mute_all: boolean;
  email_design_complete: boolean;
  email_comments: boolean;
  email_shares: boolean;
  email_marketing: boolean;
  in_app_design_complete: boolean;
  in_app_comments: boolean;
  in_app_shares: boolean;
}

// =============================================================================
// Settings Page Component
// =============================================================================

export function SettingsPage() {
  const { user, token, logout } = useAuth();
  const [searchParams] = useSearchParams();
  const location = useLocation();

  // Determine initial section from URL path or search params
  type SectionId = 'profile' | 'password' | 'connected' | 'notifications' | 'billing' | 'audit' | 'account';
  
  const getInitialSection = (): SectionId => {
    // Check if path is /settings/notifications
    if (location.pathname.endsWith('/notifications')) {
      return 'notifications';
    }
    // Fall back to search param
    const sectionParam = searchParams.get('section') as SectionId;
    return sectionParam || 'profile';
  };

  // Active section
  const [activeSection, setActiveSection] = useState<SectionId>(getInitialSection());

  // Profile state
  const [displayName, setDisplayName] = useState(user?.display_name || '');
  const [avatarUrl] = useState<string | null>(null);
  const [isProfileSaving, setIsProfileSaving] = useState(false);
  const [profileSuccess, setProfileSuccess] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);

  // Password state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [isPasswordSaving, setIsPasswordSaving] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  // Notification preferences
  const [notifications, setNotifications] = useState<NotificationPreferences>({
    mute_all: false,
    email_design_complete: true,
    email_comments: true,
    email_shares: true,
    email_marketing: false,
    in_app_design_complete: true,
    in_app_comments: true,
    in_app_shares: true,
  });
  const [isNotificationsSaving, setIsNotificationsSaving] = useState(false);
  const [notificationsSuccess, setNotificationsSuccess] = useState(false);

  // Delete account state
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);

  // Load user profile
  useEffect(() => {
    if (user) {
      setDisplayName(user.display_name || '');
    }
  }, [user]);

  // Save profile
  const handleSaveProfile = async () => {
    try {
      setIsProfileSaving(true);
      setProfileError(null);

      const response = await fetch(`${API_BASE}/users/me`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          display_name: displayName,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to update profile');
      }

      setProfileSuccess(true);
      setTimeout(() => setProfileSuccess(false), 3000);
    } catch (err) {
      setProfileError(err instanceof Error ? err.message : 'Failed to update profile');
    } finally {
      setIsProfileSaving(false);
    }
  };

  // Change password
  const handleChangePassword = async () => {
    if (newPassword !== confirmPassword) {
      setPasswordError('Passwords do not match');
      return;
    }

    if (newPassword.length < 8) {
      setPasswordError('Password must be at least 8 characters');
      return;
    }

    try {
      setIsPasswordSaving(true);
      setPasswordError(null);

      const response = await fetch(`${API_BASE}/auth/change-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to change password');
      }

      setPasswordSuccess(true);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setTimeout(() => setPasswordSuccess(false), 3000);
    } catch (err) {
      setPasswordError(err instanceof Error ? err.message : 'Failed to change password');
    } finally {
      setIsPasswordSaving(false);
    }
  };

  // Load notification preferences when entering notifications section
  useEffect(() => {
    if (activeSection === 'notifications' && token) {
      const loadPreferences = async () => {
        try {
          const prefs = await getNotificationPreferences(token);
          const prefMap = Object.fromEntries(
            prefs.map((p) => [p.notification_type, p])
          );

          // Derive mute_all: true when all key preference channels are disabled
          const keyTypes = ['job_completed', 'comment_added', 'design_shared', 'system_announcement'] as const;
          const allMuted = keyTypes.every(
            (t) => prefMap[t] && !prefMap[t].in_app_enabled && !prefMap[t].email_enabled
          );

          setNotifications((prev) => ({
            ...prev,
            mute_all: allMuted,
            email_design_complete: prefMap['job_completed']?.email_enabled ?? prev.email_design_complete,
            email_comments: prefMap['comment_added']?.email_enabled ?? prev.email_comments,
            email_shares: prefMap['design_shared']?.email_enabled ?? prev.email_shares,
            email_marketing: prefMap['system_announcement']?.email_enabled ?? prev.email_marketing,
            in_app_design_complete: prefMap['job_completed']?.in_app_enabled ?? prev.in_app_design_complete,
            in_app_comments: prefMap['comment_added']?.in_app_enabled ?? prev.in_app_comments,
            in_app_shares: prefMap['design_shared']?.in_app_enabled ?? prev.in_app_shares,
          }));
        } catch (err) {
          console.error('Failed to load notification preferences:', err);
        }
      };
      loadPreferences();
    }
  }, [activeSection, token]);

  // Save notification preferences using correct API
  const handleSaveNotifications = async () => {
    if (!token) return;
    try {
      setIsNotificationsSaving(true);

      const inApp = notifications.mute_all ? false : notifications.in_app_design_complete;
      const email = notifications.mute_all ? false : notifications.email_design_complete;

      await Promise.all([
        updateNotificationPreference('job_completed', { in_app_enabled: inApp, email_enabled: email }, token),
        updateNotificationPreference('job_failed', { in_app_enabled: inApp, email_enabled: true }, token),
        updateNotificationPreference('comment_added', {
          in_app_enabled: notifications.mute_all ? false : notifications.in_app_comments,
          email_enabled: notifications.mute_all ? false : notifications.email_comments,
        }, token),
        updateNotificationPreference('comment_reply', {
          in_app_enabled: notifications.mute_all ? false : notifications.in_app_comments,
          email_enabled: notifications.mute_all ? false : notifications.email_comments,
        }, token),
        updateNotificationPreference('comment_mention', {
          in_app_enabled: notifications.mute_all ? false : notifications.in_app_comments,
          email_enabled: notifications.mute_all ? false : notifications.email_comments,
        }, token),
        updateNotificationPreference('design_shared', {
          in_app_enabled: notifications.mute_all ? false : notifications.in_app_shares,
          email_enabled: notifications.mute_all ? false : notifications.email_shares,
        }, token),
        updateNotificationPreference('share_permission_changed', {
          in_app_enabled: notifications.mute_all ? false : notifications.in_app_shares,
          email_enabled: notifications.mute_all ? false : notifications.email_shares,
        }, token),
        updateNotificationPreference('share_revoked', {
          in_app_enabled: notifications.mute_all ? false : notifications.in_app_shares,
          email_enabled: notifications.mute_all ? false : notifications.email_shares,
        }, token),
        updateNotificationPreference('system_announcement', {
          in_app_enabled: notifications.mute_all ? false : true,
          email_enabled: notifications.mute_all ? false : notifications.email_marketing,
        }, token),
      ]);

      setNotificationsSuccess(true);
      setTimeout(() => setNotificationsSuccess(false), 3000);
    } catch (err) {
      console.error('Failed to save notifications:', err);
    } finally {
      setIsNotificationsSaving(false);
    }
  };

  // Delete account
  const handleDeleteAccount = async () => {
    if (deleteConfirmText !== 'DELETE') return;

    try {
      setIsDeleting(true);

      const response = await fetch(`${API_BASE}/users/me`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Failed to delete account');

      await logout();
    } catch (err) {
      console.error('Failed to delete account:', err);
    } finally {
      setIsDeleting(false);
    }
  };

  // Toggle notification preference
  const toggleNotification = (key: keyof NotificationPreferences) => {
    setNotifications(prev => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const sections = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'password', label: 'Password', icon: Lock },
    { id: 'connected', label: 'Connected Accounts', icon: Link2 },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'billing', label: 'Billing', icon: CreditCard },
    { id: 'audit', label: 'Audit Log', icon: FileText },
    { id: 'account', label: 'Account', icon: Trash2 },
  ] as const;

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">Settings</h1>

      <div className="flex gap-6">
        {/* Sidebar */}
        <div className="w-48 flex-shrink-0">
          <nav className="space-y-1">
            {sections.map(section => (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left ${
                  activeSection === section.id
                    ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700'
                }`}
              >
                <section.icon className="w-4 h-4" />
                {section.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 p-6">
          {/* Profile Section */}
          {activeSection === 'profile' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">Profile Information</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
                  Update your account's profile information.
                </p>
              </div>

              {/* Avatar */}
              <div className="flex items-center gap-4">
                <div className="relative">
                  <div className="w-20 h-20 rounded-full bg-primary-100 flex items-center justify-center">
                    {avatarUrl ? (
                      <img
                        src={avatarUrl}
                        alt="Avatar"
                        className="w-full h-full rounded-full object-cover"
                      />
                    ) : (
                      <User className="w-8 h-8 text-primary-600" />
                    )}
                  </div>
                  <button className="absolute bottom-0 right-0 p-1.5 bg-white dark:bg-gray-700 border dark:border-gray-600 rounded-full shadow hover:bg-gray-50 dark:hover:bg-gray-600">
                    <Camera className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                  </button>
                </div>
                <div>
                  <p className="font-medium text-gray-900 dark:text-gray-100">{user?.display_name || 'User'}</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">{user?.email}</p>
                </div>
              </div>

              {/* Display Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Display Name
                </label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full px-3 py-2 border dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
              </div>

              {/* Email (read-only) */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Email Address
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="email"
                    value={user?.email || ''}
                    disabled
                    className="flex-1 px-3 py-2 border dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700 text-gray-500 dark:text-gray-400"
                  />
                  {user?.email_verified_at ? (
                    <span className="flex items-center gap-1 text-sm text-green-600">
                      <Check className="w-4 h-4" />
                      Verified
                    </span>
                  ) : (
                    <button className="text-sm text-primary-600 hover:underline">
                      Verify
                    </button>
                  )}
                </div>
              </div>

              {/* Error/Success Messages */}
              {profileError && (
                <div className="flex items-center gap-2 text-red-600 text-sm">
                  <X className="w-4 h-4" />
                  {profileError}
                </div>
              )}
              {profileSuccess && (
                <div className="flex items-center gap-2 text-green-600 text-sm">
                  <Check className="w-4 h-4" />
                  Profile updated successfully
                </div>
              )}

              {/* Save Button */}
              <div className="flex justify-end">
                <button
                  onClick={handleSaveProfile}
                  disabled={isProfileSaving}
                  className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                >
                  {isProfileSaving ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Save className="w-4 h-4" />
                  )}
                  Save Changes
                </button>
              </div>
            </div>
          )}

          {/* Password Section */}
          {activeSection === 'password' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">Change Password</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
                  Ensure your account is using a strong password.
                </p>
              </div>

              {/* Current Password */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Current Password
                </label>
                <div className="relative">
                  <input
                    type={showCurrentPassword ? 'text' : 'password'}
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    className="w-full px-3 py-2 border dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 pr-10 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  />
                  <button
                    type="button"
                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 dark:text-gray-400"
                  >
                    {showCurrentPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* New Password */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  New Password
                </label>
                <div className="relative">
                  <input
                    type={showNewPassword ? 'text' : 'password'}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full px-3 py-2 border dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 pr-10 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 dark:text-gray-400"
                  >
                    {showNewPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Confirm Password */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Confirm New Password
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full px-3 py-2 border dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
              </div>

              {/* Error/Success Messages */}
              {passwordError && (
                <div className="flex items-center gap-2 text-red-600 text-sm">
                  <X className="w-4 h-4" />
                  {passwordError}
                </div>
              )}
              {passwordSuccess && (
                <div className="flex items-center gap-2 text-green-600 text-sm">
                  <Check className="w-4 h-4" />
                  Password changed successfully
                </div>
              )}

              {/* Save Button */}
              <div className="flex justify-end">
                <button
                  onClick={handleChangePassword}
                  disabled={isPasswordSaving || !currentPassword || !newPassword || !confirmPassword}
                  className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                >
                  {isPasswordSaving ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Lock className="w-4 h-4" />
                  )}
                  Update Password
                </button>
              </div>
            </div>
          )}

          {/* Notifications Section */}
          {activeSection === 'notifications' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">Notification Preferences</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
                  Choose what notifications you receive.
                </p>
              </div>

              {/* Mute All Option */}
              <div className="border border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/30 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <BellOff className="w-5 h-5 text-amber-600 dark:text-amber-500" />
                    <div>
                      <p className="font-medium text-gray-900 dark:text-gray-100">Mute All Notifications</p>
                      <p className="text-sm text-gray-500 dark:text-gray-400">Temporarily disable all notifications</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => toggleNotification('mute_all')}
                    className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2 ${
                      notifications.mute_all ? 'bg-amber-500' : 'bg-gray-200'
                    }`}
                  >
                    <span
                      className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                        notifications.mute_all ? 'translate-x-5' : 'translate-x-0'
                      }`}
                    />
                  </button>
                </div>
              </div>

              {/* Email Notifications */}
              <div className={notifications.mute_all ? 'opacity-50 pointer-events-none' : ''}>
                <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-3">Email Notifications</h3>
                <div className="space-y-3">
                  <NotificationToggle
                    label="Design completion"
                    description="Get notified when your designs finish generating"
                    checked={notifications.email_design_complete}
                    onChange={() => toggleNotification('email_design_complete')}
                  />
                  <NotificationToggle
                    label="Comments"
                    description="Get notified when someone comments on your design"
                    checked={notifications.email_comments}
                    onChange={() => toggleNotification('email_comments')}
                  />
                  <NotificationToggle
                    label="Shares"
                    description="Get notified when someone shares a design with you"
                    checked={notifications.email_shares}
                    onChange={() => toggleNotification('email_shares')}
                  />
                  <NotificationToggle
                    label="Product updates"
                    description="Receive news about new features and updates"
                    checked={notifications.email_marketing}
                    onChange={() => toggleNotification('email_marketing')}
                  />
                </div>
              </div>

              {/* In-App Notifications */}
              <div className={notifications.mute_all ? 'opacity-50 pointer-events-none' : ''}>
                <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-3">In-App Notifications</h3>
                <div className="space-y-3">
                  <NotificationToggle
                    label="Design completion"
                    description="Show notification when designs finish"
                    checked={notifications.in_app_design_complete}
                    onChange={() => toggleNotification('in_app_design_complete')}
                  />
                  <NotificationToggle
                    label="Comments"
                    description="Show notification for new comments"
                    checked={notifications.in_app_comments}
                    onChange={() => toggleNotification('in_app_comments')}
                  />
                  <NotificationToggle
                    label="Shares"
                    description="Show notification for new shared designs"
                    checked={notifications.in_app_shares}
                    onChange={() => toggleNotification('in_app_shares')}
                  />
                </div>
              </div>

              {/* Success Message */}
              {notificationsSuccess && (
                <div className="flex items-center gap-2 text-green-600 text-sm">
                  <Check className="w-4 h-4" />
                  Preferences saved successfully
                </div>
              )}

              {/* Save Button */}
              <div className="flex justify-end">
                <button
                  onClick={handleSaveNotifications}
                  disabled={isNotificationsSaving}
                  className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                >
                  {isNotificationsSaving ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Save className="w-4 h-4" />
                  )}
                  Save Preferences
                </button>
              </div>
            </div>
          )}

          {/* Connected Accounts Section */}
          {activeSection === 'connected' && (
            <ConnectedAccountsSection />
          )}

          {/* Billing Section */}
          {activeSection === 'billing' && (
            <BillingSection />
          )}

          {/* Audit Log Section */}
          {activeSection === 'audit' && (
            <AuditLogViewer />
          )}

          {/* Account Section */}
          {activeSection === 'account' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">Account Management</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
                  Manage your account settings and data.
                </p>
              </div>

              {/* Danger Zone */}
              <div className="border border-red-200 rounded-lg p-4 bg-red-50">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <h3 className="font-medium text-red-800">Delete Account</h3>
                    <p className="text-sm text-red-700 mt-1">
                      Once you delete your account, there is no going back. All your designs,
                      projects, and data will be permanently removed.
                    </p>
                    <button
                      onClick={() => setShowDeleteConfirm(true)}
                      className="mt-3 px-4 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700"
                    >
                      Delete Account
                    </button>
                  </div>
                </div>
              </div>

              {/* Delete Confirmation Modal */}
              {showDeleteConfirm && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                  <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="p-2 bg-red-100 dark:bg-red-900/50 rounded-full">
                        <AlertTriangle className="w-5 h-5 text-red-600" />
                      </div>
                      <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Delete Account</h2>
                    </div>
                    <p className="text-gray-600 dark:text-gray-400 mb-4">
                      This action is irreversible. All your data will be permanently deleted.
                      Type <strong>DELETE</strong> to confirm.
                    </p>
                    <input
                      type="text"
                      value={deleteConfirmText}
                      onChange={(e) => setDeleteConfirmText(e.target.value)}
                      className="w-full px-3 py-2 border dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-red-500 mb-4 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                      placeholder="Type DELETE to confirm"
                    />
                    <div className="flex justify-end gap-3">
                      <button
                        onClick={() => {
                          setShowDeleteConfirm(false);
                          setDeleteConfirmText('');
                        }}
                        className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleDeleteAccount}
                        disabled={deleteConfirmText !== 'DELETE' || isDeleting}
                        className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
                      >
                        {isDeleting ? 'Deleting...' : 'Delete Account'}
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Helper Components
// =============================================================================

interface NotificationToggleProps {
  label: string;
  description: string;
  checked: boolean;
  onChange: () => void;
}

function NotificationToggle({ label, description, checked, onChange }: NotificationToggleProps) {
  return (
    <label className="flex items-center justify-between cursor-pointer">
      <div>
        <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{label}</p>
        <p className="text-sm text-gray-500 dark:text-gray-400">{description}</p>
      </div>
      <button
        type="button"
        onClick={onChange}
        className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 ${
          checked ? 'bg-primary-600' : 'bg-gray-200 dark:bg-gray-600'
        }`}
      >
        <span
          className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
            checked ? 'translate-x-5' : 'translate-x-0'
          }`}
        />
      </button>
    </label>
  );
}

export default SettingsPage;
