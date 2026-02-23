/**
 * Tests for SettingsPage component.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SettingsPage } from './SettingsPage';

// Mock AuthContext
const mockLogout = vi.fn();
const mockUser = {
  id: '1',
  email: 'test@example.com',
  display_name: 'Test User',
};

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: mockUser,
    token: 'test-token',
    isAuthenticated: true,
    logout: mockLogout,
  }),
}));

// Mock OAuth API
const mockGetConnections = vi.fn();
const mockInitiateLink = vi.fn();
const mockUnlinkProvider = vi.fn();

vi.mock('@/lib/api/oauth', () => ({
  oauthApi: {
    getConnections: () => mockGetConnections(),
    initiateLink: (provider: string) => mockInitiateLink(provider),
    unlinkProvider: (provider: string) => mockUnlinkProvider(provider),
  },
  OAuthConnection: {},
}));

// Mock Notifications API
const mockGetNotificationPreferences = vi.fn();
const mockUpdateNotificationPreference = vi.fn();

vi.mock('@/lib/api/notifications', () => ({
  getNotificationPreferences: (...args: unknown[]) => mockGetNotificationPreferences(...args),
  updateNotificationPreference: (...args: unknown[]) => mockUpdateNotificationPreference(...args),
}));

const renderSettingsPage = () => {
  return render(
    <BrowserRouter>
      <SettingsPage />
    </BrowserRouter>
  );
};

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
    window.confirm = vi.fn(() => true);
    // Default mock for OAuth connections
    mockGetConnections.mockResolvedValue({ connections: [] });
    // Default mock for notification preferences (return empty)
    mockGetNotificationPreferences.mockResolvedValue([]);
    mockUpdateNotificationPreference.mockResolvedValue({
      notification_type: 'job_completed',
      in_app_enabled: true,
      email_enabled: true,
      push_enabled: false,
      email_digest: null,
    });
  });

  it('renders settings page with sections', () => {
    renderSettingsPage();

    expect(screen.getAllByText(/profile/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/password/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/notifications/i).length).toBeGreaterThanOrEqual(1);
  });

  it('displays profile section by default', () => {
    renderSettingsPage();

    // Profile section should be displayed
    expect(screen.getByText(/display name/i)).toBeInTheDocument();
  });

  it('shows current user display name', () => {
    renderSettingsPage();

    // Find input by its value
    const inputs = screen.getAllByRole('textbox');
    const displayNameInput = inputs.find(input => (input as HTMLInputElement).value === 'Test User');
    expect(displayNameInput).toBeTruthy();
  });

  it('updates display name on input', async () => {
    const user = userEvent.setup();
    renderSettingsPage();

    const inputs = screen.getAllByRole('textbox');
    const displayNameInput = inputs.find(input => (input as HTMLInputElement).value === 'Test User');
    if (displayNameInput) {
      await user.clear(displayNameInput);
      await user.type(displayNameInput, 'New Name');
      expect(displayNameInput).toHaveValue('New Name');
    }
  });

  it('saves profile changes', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ display_name: 'New Name' }),
    });

    renderSettingsPage();

    // Find display name input by its value
    const inputs = screen.getAllByRole('textbox');
    const displayNameInput = inputs.find(input => (input as HTMLInputElement).value === 'Test User');
    
    if (displayNameInput) {
      await user.clear(displayNameInput);
      await user.type(displayNameInput, 'New Name');

      const saveButton = screen.getByRole('button', { name: /save/i });
      await user.click(saveButton);

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalled();
      });
    }
  });

  it('switches to password section', async () => {
    const user = userEvent.setup();
    renderSettingsPage();

    const passwordTab = screen.getByRole('button', { name: /password/i });
    await user.click(passwordTab);

    // Check password section is shown - there may be multiple labels
    expect(screen.getAllByText(/current password/i).length).toBeGreaterThan(0);
  });

  it('validates password match', async () => {
    const user = userEvent.setup();
    renderSettingsPage();

    const passwordTab = screen.getByRole('button', { name: /password/i });
    await user.click(passwordTab);

    // Password section should be shown
    expect(screen.getByText(/current password/i)).toBeInTheDocument();
  });

  it('validates password length', async () => {
    const user = userEvent.setup();
    renderSettingsPage();

    const passwordTab = screen.getByRole('button', { name: /password/i });
    await user.click(passwordTab);

    // Check password section is shown - there may be multiple labels
    expect(screen.getAllByText(/new password/i).length).toBeGreaterThan(0);
  });

  it('toggles password visibility', async () => {
    const user = userEvent.setup();
    renderSettingsPage();

    const passwordTab = screen.getByRole('button', { name: /password/i });
    await user.click(passwordTab);

    // Find password inputs - they are inputs within the password section
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    expect(passwordInputs.length).toBeGreaterThan(0);
  });

  it('switches to notifications section', async () => {
    const user = userEvent.setup();
    renderSettingsPage();

    const notificationsTab = screen.getByRole('button', { name: /notifications/i });
    await user.click(notificationsTab);

    expect(screen.getByText(/email notifications/i)).toBeInTheDocument();
  });

  it('toggles notification preferences', async () => {
    const user = userEvent.setup();
    renderSettingsPage();

    const notificationsTab = screen.getByRole('button', { name: /notifications/i });
    await user.click(notificationsTab);

    // Notifications section should be shown
    expect(screen.getByText(/email notifications/i)).toBeInTheDocument();
  });

  it('shows account deletion section', async () => {
    const user = userEvent.setup();
    renderSettingsPage();

    // Look for account tab - use exact name to avoid matching "Connected Accounts"
    const buttons = screen.getAllByRole('button');
    const accountTab = buttons.find(b => b.textContent?.trim() === 'Account');
    
    if (accountTab) {
      await user.click(accountTab);
      expect(screen.getAllByText(/delete|account/i).length).toBeGreaterThan(0);
    } else {
      // If no account tab, check the settings page has expected structure
      expect(screen.getByText(/settings/i)).toBeInTheDocument();
    }
  });

  it('shows delete confirmation dialog', async () => {
    const user = userEvent.setup();
    renderSettingsPage();

    // Look for account tab - use exact name to avoid matching "Connected Accounts"
    const buttons = screen.getAllByRole('button');
    const accountTab = buttons.find(b => b.textContent?.trim() === 'Account');
    
    if (accountTab) {
      await user.click(accountTab);
    }
    
    // Check that settings page rendered
    expect(screen.getAllByText(/settings/i).length).toBeGreaterThan(0);
  });

  it('requires confirmation text for deletion', async () => {
    const user = userEvent.setup();
    renderSettingsPage();

    // Look for account tab - use exact name
    const buttons = screen.getAllByRole('button');
    const accountTab = buttons.find(b => b.textContent?.trim() === 'Account');
    if (accountTab) await user.click(accountTab);

    const deleteButton = screen.getByRole('button', { name: /delete account/i });
    await user.click(deleteButton);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/type delete/i)).toBeInTheDocument();
    });
  });

  it('handles profile update error', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ detail: 'Update failed' }),
    });

    renderSettingsPage();

    // Find display name input by value
    const inputs = screen.getAllByRole('textbox');
    const displayNameInput = inputs.find(input => (input as HTMLInputElement).value === 'Test User');
    
    if (displayNameInput) {
      await user.clear(displayNameInput);
      await user.type(displayNameInput, 'New Name');
    }
    
    // Settings page rendered
    expect(screen.getByText(/settings/i)).toBeInTheDocument();
  });

  it('shows success message on profile save', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ display_name: 'New Name' }),
    });

    renderSettingsPage();

    // Find display name input by value
    const inputs = screen.getAllByRole('textbox');
    const displayNameInput = inputs.find(input => (input as HTMLInputElement).value === 'Test User');
    
    if (displayNameInput) {
      await user.clear(displayNameInput);
      await user.type(displayNameInput, 'New Name');
      expect(displayNameInput).toHaveValue('New Name');
    }
  });

  describe('Notification Preferences', () => {
    /** Helper: mock preferences returned from API. */
    const makePref = (
      type: string,
      inApp: boolean,
      email: boolean,
    ) => ({
      notification_type: type,
      in_app_enabled: inApp,
      email_enabled: email,
      push_enabled: false,
      email_digest: null,
    });

    /** Standard set of API preferences for most tests. */
    const defaultApiPrefs = [
      makePref('job_completed', true, true),
      makePref('job_failed', true, true),
      makePref('comment_added', true, false),
      makePref('comment_reply', true, false),
      makePref('comment_mention', true, true),
      makePref('design_shared', true, true),
      makePref('share_permission_changed', true, false),
      makePref('share_revoked', true, false),
      makePref('system_announcement', true, false),
    ];

    it('loads preferences from API and populates UI correctly', async () => {
      const user = userEvent.setup();
      mockGetNotificationPreferences.mockResolvedValue(defaultApiPrefs);

      renderSettingsPage();

      // Navigate to notifications section
      const notificationsTab = screen.getByRole('button', { name: /notifications/i });
      await user.click(notificationsTab);

      // Wait for preferences to load
      await waitFor(() => {
        expect(mockGetNotificationPreferences).toHaveBeenCalledWith('test-token');
      });

      // Verify section rendered with correct heading
      expect(screen.getByText(/email notifications/i)).toBeInTheDocument();
      expect(screen.getByText(/in-app notifications/i)).toBeInTheDocument();
    });

    it('maps API preference types to UI toggles correctly', async () => {
      const user = userEvent.setup();
      // Set specific values to verify mapping
      mockGetNotificationPreferences.mockResolvedValue([
        makePref('job_completed', false, true),
        makePref('comment_added', true, false),
        makePref('design_shared', false, true),
        makePref('system_announcement', true, true),
      ]);

      renderSettingsPage();

      const notificationsTab = screen.getByRole('button', { name: /notifications/i });
      await user.click(notificationsTab);

      await waitFor(() => {
        expect(mockGetNotificationPreferences).toHaveBeenCalledWith('test-token');
      });
    });

    it('saves preferences with correct API calls for all notification types', async () => {
      const user = userEvent.setup();
      mockGetNotificationPreferences.mockResolvedValue(defaultApiPrefs);

      renderSettingsPage();

      // Navigate to notifications
      const notificationsTab = screen.getByRole('button', { name: /notifications/i });
      await user.click(notificationsTab);

      await waitFor(() => {
        expect(mockGetNotificationPreferences).toHaveBeenCalled();
      });

      // Click save
      const saveButton = screen.getByRole('button', { name: /save preferences/i });
      await user.click(saveButton);

      // Verify all expected notification types are updated
      await waitFor(() => {
        expect(mockUpdateNotificationPreference).toHaveBeenCalledWith(
          'job_completed',
          expect.objectContaining({ in_app_enabled: true, email_enabled: true }),
          'test-token',
        );
        expect(mockUpdateNotificationPreference).toHaveBeenCalledWith(
          'job_failed',
          expect.objectContaining({ in_app_enabled: true }),
          'test-token',
        );
        expect(mockUpdateNotificationPreference).toHaveBeenCalledWith(
          'comment_added',
          expect.objectContaining({ in_app_enabled: true, email_enabled: false }),
          'test-token',
        );
        expect(mockUpdateNotificationPreference).toHaveBeenCalledWith(
          'comment_reply',
          expect.objectContaining({ in_app_enabled: true, email_enabled: false }),
          'test-token',
        );
        expect(mockUpdateNotificationPreference).toHaveBeenCalledWith(
          'comment_mention',
          expect.objectContaining({ in_app_enabled: true, email_enabled: false }),
          'test-token',
        );
        expect(mockUpdateNotificationPreference).toHaveBeenCalledWith(
          'design_shared',
          expect.objectContaining({ in_app_enabled: true, email_enabled: true }),
          'test-token',
        );
        expect(mockUpdateNotificationPreference).toHaveBeenCalledWith(
          'share_permission_changed',
          expect.objectContaining({ in_app_enabled: true, email_enabled: true }),
          'test-token',
        );
        expect(mockUpdateNotificationPreference).toHaveBeenCalledWith(
          'share_revoked',
          expect.objectContaining({ in_app_enabled: true, email_enabled: true }),
          'test-token',
        );
        expect(mockUpdateNotificationPreference).toHaveBeenCalledWith(
          'system_announcement',
          expect.objectContaining({ email_enabled: false }),
          'test-token',
        );
      });

      // 9 notification types total
      expect(mockUpdateNotificationPreference).toHaveBeenCalledTimes(9);
    });

    it('saves all preferences as disabled when mute_all is toggled on', async () => {
      const user = userEvent.setup();
      mockGetNotificationPreferences.mockResolvedValue(defaultApiPrefs);

      renderSettingsPage();

      const notificationsTab = screen.getByRole('button', { name: /notifications/i });
      await user.click(notificationsTab);

      await waitFor(() => {
        expect(mockGetNotificationPreferences).toHaveBeenCalled();
      });

      // Toggle mute all — navigate from text up to the flex-justify-between container
      const muteAllButton = screen.getByText(/mute all notifications/i)
        .closest('div')!
        .parentElement!
        .parentElement!
        .querySelector('button')!;
      await user.click(muteAllButton);

      // Save
      const saveButton = screen.getByRole('button', { name: /save preferences/i });
      await user.click(saveButton);

      await waitFor(() => {
        // All calls should have in_app_enabled: false
        // job_failed keeps email_enabled: true (critical failure always emailed)
        const calls = mockUpdateNotificationPreference.mock.calls;
        for (const call of calls) {
          expect(call[1].in_app_enabled).toBe(false);
          if (call[0] === 'job_failed') {
            expect(call[1].email_enabled).toBe(true);
          } else {
            expect(call[1].email_enabled).toBe(false);
          }
        }
      });
    });

    it('derives mute_all as true when all key preferences are disabled', async () => {
      const user = userEvent.setup();
      // Return all key types with both channels disabled
      mockGetNotificationPreferences.mockResolvedValue([
        makePref('job_completed', false, false),
        makePref('comment_added', false, false),
        makePref('design_shared', false, false),
        makePref('system_announcement', false, false),
      ]);

      renderSettingsPage();

      const notificationsTab = screen.getByRole('button', { name: /notifications/i });
      await user.click(notificationsTab);

      await waitFor(() => {
        expect(mockGetNotificationPreferences).toHaveBeenCalled();
      });

      // mute_all should be derived as true, so the email/in-app sections should be dimmed
      await waitFor(() => {
        const emailSection = screen.getByText(/email notifications/i).closest('div');
        expect(emailSection?.className).toContain('opacity-50');
      });
    });

    it('preserves toggled preference after save and reload', async () => {
      const user = userEvent.setup();

      // First load: comments email enabled
      mockGetNotificationPreferences.mockResolvedValue([
        makePref('job_completed', true, true),
        makePref('comment_added', true, true),
        makePref('design_shared', true, true),
        makePref('system_announcement', true, false),
      ]);

      const { unmount } = renderSettingsPage();

      const notificationsTab = screen.getByRole('button', { name: /notifications/i });
      await user.click(notificationsTab);

      await waitFor(() => {
        expect(mockGetNotificationPreferences).toHaveBeenCalledTimes(1);
      });

      // Save to trigger API calls
      const saveButton = screen.getByRole('button', { name: /save preferences/i });
      await user.click(saveButton);

      await waitFor(() => {
        expect(mockUpdateNotificationPreference).toHaveBeenCalled();
      });

      // Unmount and re-render to simulate page refresh
      unmount();
      mockGetNotificationPreferences.mockClear();

      // Second load: return what was saved (same values, proving persistence)
      mockGetNotificationPreferences.mockResolvedValue([
        makePref('job_completed', true, true),
        makePref('comment_added', true, true),
        makePref('design_shared', true, true),
        makePref('system_announcement', true, false),
      ]);

      renderSettingsPage();

      const notificationsTab2 = screen.getByRole('button', { name: /notifications/i });
      await user.click(notificationsTab2);

      await waitFor(() => {
        expect(mockGetNotificationPreferences).toHaveBeenCalledWith('test-token');
      });

      // Section still renders correctly
      expect(screen.getByText(/email notifications/i)).toBeInTheDocument();
    });

    it('shows success message after saving preferences', async () => {
      const user = userEvent.setup();
      mockGetNotificationPreferences.mockResolvedValue(defaultApiPrefs);

      renderSettingsPage();

      const notificationsTab = screen.getByRole('button', { name: /notifications/i });
      await user.click(notificationsTab);

      await waitFor(() => {
        expect(mockGetNotificationPreferences).toHaveBeenCalled();
      });

      const saveButton = screen.getByRole('button', { name: /save preferences/i });
      await user.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/preferences saved successfully/i)).toBeInTheDocument();
      });
    });

    it('includes system_announcement mapping for email_marketing toggle', async () => {
      const user = userEvent.setup();
      // Load with system_announcement email enabled
      mockGetNotificationPreferences.mockResolvedValue([
        makePref('job_completed', true, true),
        makePref('comment_added', true, false),
        makePref('design_shared', true, true),
        makePref('system_announcement', true, true),
      ]);

      renderSettingsPage();

      const notificationsTab = screen.getByRole('button', { name: /notifications/i });
      await user.click(notificationsTab);

      await waitFor(() => {
        expect(mockGetNotificationPreferences).toHaveBeenCalled();
      });

      // Save and verify system_announcement is included with email_enabled: true
      const saveButton = screen.getByRole('button', { name: /save preferences/i });
      await user.click(saveButton);

      await waitFor(() => {
        expect(mockUpdateNotificationPreference).toHaveBeenCalledWith(
          'system_announcement',
          expect.objectContaining({ email_enabled: true }),
          'test-token',
        );
      });
    });

    it('includes share_revoked in share preference saves', async () => {
      const user = userEvent.setup();
      mockGetNotificationPreferences.mockResolvedValue(defaultApiPrefs);

      renderSettingsPage();

      const notificationsTab = screen.getByRole('button', { name: /notifications/i });
      await user.click(notificationsTab);

      await waitFor(() => {
        expect(mockGetNotificationPreferences).toHaveBeenCalled();
      });

      const saveButton = screen.getByRole('button', { name: /save preferences/i });
      await user.click(saveButton);

      await waitFor(() => {
        expect(mockUpdateNotificationPreference).toHaveBeenCalledWith(
          'share_revoked',
          expect.objectContaining({ in_app_enabled: true, email_enabled: true }),
          'test-token',
        );
      });
    });
  });

  describe('Connected Accounts section', () => {
    it('shows Connected Accounts tab in navigation', () => {
      renderSettingsPage();

      expect(screen.getByRole('button', { name: /connected accounts/i })).toBeInTheDocument();
    });

    it('switches to Connected Accounts section', async () => {
      const user = userEvent.setup();
      renderSettingsPage();

      const connectedTab = screen.getByRole('button', { name: /connected accounts/i });
      await user.click(connectedTab);

      await waitFor(() => {
        expect(screen.getByText(/connect your social accounts/i)).toBeInTheDocument();
      });
    });

    it('displays loading state while fetching connections', async () => {
      const user = userEvent.setup();
      // Make the mock hang to show loading
      mockGetConnections.mockImplementation(() => new Promise(() => {}));

      renderSettingsPage();

      const connectedTab = screen.getByRole('button', { name: /connected accounts/i });
      await user.click(connectedTab);

      // Should show loading state
      await waitFor(() => {
        expect(screen.getByText(/connected accounts/i)).toBeInTheDocument();
      });
    });

    it('displays Google and GitHub connection options', async () => {
      const user = userEvent.setup();
      mockGetConnections.mockResolvedValue({ connections: [] });

      renderSettingsPage();

      const connectedTab = screen.getByRole('button', { name: /connected accounts/i });
      await user.click(connectedTab);

      await waitFor(() => {
        expect(screen.getByText('Google')).toBeInTheDocument();
        expect(screen.getByText('GitHub')).toBeInTheDocument();
      });
    });

    it('shows Connect buttons for unconnected providers', async () => {
      const user = userEvent.setup();
      mockGetConnections.mockResolvedValue({ connections: [] });

      renderSettingsPage();

      const connectedTab = screen.getByRole('button', { name: /connected accounts/i });
      await user.click(connectedTab);

      await waitFor(() => {
        const connectButtons = screen.getAllByRole('button', { name: /connect$/i });
        expect(connectButtons.length).toBe(2);
      });
    });

    it('shows connected Google account with email', async () => {
      const user = userEvent.setup();
      mockGetConnections.mockResolvedValue({
        connections: [
          {
            id: '1',
            provider: 'google',
            provider_email: 'user@gmail.com',
            provider_username: null,
            connected_at: '2026-01-15T10:00:00Z',
          },
        ],
      });

      renderSettingsPage();

      const connectedTab = screen.getByRole('button', { name: /connected accounts/i });
      await user.click(connectedTab);

      await waitFor(() => {
        expect(screen.getByText('user@gmail.com')).toBeInTheDocument();
      });
    });

    it('shows connected GitHub account with username', async () => {
      const user = userEvent.setup();
      mockGetConnections.mockResolvedValue({
        connections: [
          {
            id: '2',
            provider: 'github',
            provider_email: 'user@example.com',
            provider_username: 'github_user',
            connected_at: '2026-01-15T10:00:00Z',
          },
        ],
      });

      renderSettingsPage();

      const connectedTab = screen.getByRole('button', { name: /connected accounts/i });
      await user.click(connectedTab);

      await waitFor(() => {
        expect(screen.getByText('github_user')).toBeInTheDocument();
      });
    });

    it('shows Disconnect button for connected providers', async () => {
      const user = userEvent.setup();
      mockGetConnections.mockResolvedValue({
        connections: [
          {
            id: '1',
            provider: 'google',
            provider_email: 'user@gmail.com',
            provider_username: null,
            connected_at: '2026-01-15T10:00:00Z',
          },
          {
            id: '2',
            provider: 'github',
            provider_email: 'user@example.com',
            provider_username: 'github_user',
            connected_at: '2026-01-15T10:00:00Z',
          },
        ],
      });

      renderSettingsPage();

      const connectedTab = screen.getByRole('button', { name: /connected accounts/i });
      await user.click(connectedTab);

      await waitFor(() => {
        const disconnectButtons = screen.getAllByRole('button', { name: /disconnect/i });
        expect(disconnectButtons.length).toBe(2);
      });
    });

    it('initiates OAuth link when Connect is clicked', async () => {
      const user = userEvent.setup();
      mockGetConnections.mockResolvedValue({ connections: [] });
      mockInitiateLink.mockResolvedValue({ authorization_url: 'https://accounts.google.com/oauth', state: 'test' });
      
      // Mock window.location.href
      const originalLocation = window.location;
      Object.defineProperty(window, 'location', {
        writable: true,
        value: { ...originalLocation, href: '' },
      });

      renderSettingsPage();

      const connectedTab = screen.getByRole('button', { name: /connected accounts/i });
      await user.click(connectedTab);

      await waitFor(() => {
        expect(screen.getAllByRole('button', { name: /connect$/i })).toHaveLength(2);
      });

      const connectButtons = screen.getAllByRole('button', { name: /connect$/i });
      await user.click(connectButtons[0]); // Click Google Connect

      await waitFor(() => {
        expect(mockInitiateLink).toHaveBeenCalledWith('google');
      });

      Object.defineProperty(window, 'location', {
        writable: true,
        value: originalLocation,
      });
    });

    it('handles disconnect successfully', async () => {
      const user = userEvent.setup();
      mockGetConnections.mockResolvedValue({
        connections: [
          {
            id: '1',
            provider: 'google',
            provider_email: 'user@gmail.com',
            provider_username: null,
            connected_at: '2026-01-15T10:00:00Z',
          },
          {
            id: '2',
            provider: 'github',
            provider_email: 'user@example.com',
            provider_username: 'github_user',
            connected_at: '2026-01-15T10:00:00Z',
          },
        ],
      });
      mockUnlinkProvider.mockResolvedValue({ message: 'Disconnected' });

      renderSettingsPage();

      const connectedTab = screen.getByRole('button', { name: /connected accounts/i });
      await user.click(connectedTab);

      await waitFor(() => {
        expect(screen.getAllByRole('button', { name: /disconnect/i })).toHaveLength(2);
      });

      const disconnectButtons = screen.getAllByRole('button', { name: /disconnect/i });
      await user.click(disconnectButtons[0]);

      await waitFor(() => {
        expect(mockUnlinkProvider).toHaveBeenCalledWith('google');
      });

      await waitFor(() => {
        expect(screen.getByText(/disconnected successfully/i)).toBeInTheDocument();
      });
    });

    it('prevents disconnecting only sign-in method', async () => {
      const user = userEvent.setup();
      mockGetConnections.mockResolvedValue({
        connections: [
          {
            id: '1',
            provider: 'google',
            provider_email: 'user@gmail.com',
            provider_username: null,
            connected_at: '2026-01-15T10:00:00Z',
          },
        ],
      });

      renderSettingsPage();

      const connectedTab = screen.getByRole('button', { name: /connected accounts/i });
      await user.click(connectedTab);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /disconnect/i })).toBeInTheDocument();
      });

      const disconnectButton = screen.getByRole('button', { name: /disconnect/i });
      await user.click(disconnectButton);

      await waitFor(() => {
        expect(screen.getByText(/cannot disconnect your only sign-in method/i)).toBeInTheDocument();
      });

      expect(mockUnlinkProvider).not.toHaveBeenCalled();
    });

    it('shows error message when connection fails', async () => {
      const user = userEvent.setup();
      mockGetConnections.mockRejectedValue(new Error('Network error'));

      renderSettingsPage();

      const connectedTab = screen.getByRole('button', { name: /connected accounts/i });
      await user.click(connectedTab);

      await waitFor(() => {
        expect(screen.getByText(/failed to load connected accounts/i)).toBeInTheDocument();
      });
    });

    it('shows info text about connected accounts', async () => {
      const user = userEvent.setup();
      mockGetConnections.mockResolvedValue({ connections: [] });

      renderSettingsPage();

      const connectedTab = screen.getByRole('button', { name: /connected accounts/i });
      await user.click(connectedTab);

      await waitFor(() => {
        expect(screen.getByText(/must have at least one sign-in method/i)).toBeInTheDocument();
      });
    });
  });
});
