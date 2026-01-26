/**
 * Settings Page - User profile and preferences.
 */

import { useState, useEffect } from 'react';
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
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// =============================================================================
// Types
// =============================================================================

interface NotificationPreferences {
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

  // Active section
  const [activeSection, setActiveSection] = useState<'profile' | 'password' | 'notifications' | 'account'>('profile');

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

  // Save notification preferences
  const handleSaveNotifications = async () => {
    try {
      setIsNotificationsSaving(true);

      const response = await fetch(`${API_BASE}/users/me/notifications`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(notifications),
      });

      if (!response.ok) throw new Error('Failed to update preferences');

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
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'account', label: 'Account', icon: Trash2 },
  ] as const;

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Settings</h1>

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
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                <section.icon className="w-4 h-4" />
                {section.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 bg-white rounded-lg border p-6">
          {/* Profile Section */}
          {activeSection === 'profile' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold mb-4">Profile Information</h2>
                <p className="text-sm text-gray-500 mb-6">
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
                  <button className="absolute bottom-0 right-0 p-1.5 bg-white border rounded-full shadow hover:bg-gray-50">
                    <Camera className="w-4 h-4 text-gray-600" />
                  </button>
                </div>
                <div>
                  <p className="font-medium">{user?.display_name || 'User'}</p>
                  <p className="text-sm text-gray-500">{user?.email}</p>
                </div>
              </div>

              {/* Display Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Display Name
                </label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
                />
              </div>

              {/* Email (read-only) */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email Address
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="email"
                    value={user?.email || ''}
                    disabled
                    className="flex-1 px-3 py-2 border rounded-lg bg-gray-50 text-gray-500"
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
                <h2 className="text-lg font-semibold mb-4">Change Password</h2>
                <p className="text-sm text-gray-500 mb-6">
                  Ensure your account is using a strong password.
                </p>
              </div>

              {/* Current Password */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Current Password
                </label>
                <div className="relative">
                  <input
                    type={showCurrentPassword ? 'text' : 'password'}
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500"
                  >
                    {showCurrentPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* New Password */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  New Password
                </label>
                <div className="relative">
                  <input
                    type={showNewPassword ? 'text' : 'password'}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500"
                  >
                    {showNewPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Confirm Password */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Confirm New Password
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
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
                <h2 className="text-lg font-semibold mb-4">Notification Preferences</h2>
                <p className="text-sm text-gray-500 mb-6">
                  Choose what notifications you receive.
                </p>
              </div>

              {/* Email Notifications */}
              <div>
                <h3 className="font-medium text-gray-900 mb-3">Email Notifications</h3>
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
              <div>
                <h3 className="font-medium text-gray-900 mb-3">In-App Notifications</h3>
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

          {/* Account Section */}
          {activeSection === 'account' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold mb-4">Account Management</h2>
                <p className="text-sm text-gray-500 mb-6">
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
                  <div className="bg-white rounded-lg p-6 w-full max-w-md">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="p-2 bg-red-100 rounded-full">
                        <AlertTriangle className="w-5 h-5 text-red-600" />
                      </div>
                      <h2 className="text-lg font-semibold">Delete Account</h2>
                    </div>
                    <p className="text-gray-600 mb-4">
                      This action is irreversible. All your data will be permanently deleted.
                      Type <strong>DELETE</strong> to confirm.
                    </p>
                    <input
                      type="text"
                      value={deleteConfirmText}
                      onChange={(e) => setDeleteConfirmText(e.target.value)}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-red-500 mb-4"
                      placeholder="Type DELETE to confirm"
                    />
                    <div className="flex justify-end gap-3">
                      <button
                        onClick={() => {
                          setShowDeleteConfirm(false);
                          setDeleteConfirmText('');
                        }}
                        className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
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
        <p className="text-sm font-medium text-gray-900">{label}</p>
        <p className="text-sm text-gray-500">{description}</p>
      </div>
      <button
        type="button"
        onClick={onChange}
        className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 ${
          checked ? 'bg-primary-600' : 'bg-gray-200'
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
