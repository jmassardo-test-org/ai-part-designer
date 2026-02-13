/**
 * Tests for OrganizationSettingsPage component.
 */

import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { Organization, OrganizationMember } from '@/lib/api/organizations';
import { OrganizationSettingsPage } from './OrganizationSettingsPage';

// Mock data
const mockOrganization: Organization = {
  id: 'org-1',
  name: 'Test Organization',
  slug: 'test-org',
  description: 'A test organization',
  logo_url: undefined,
  owner_id: 'user-1',
  subscription_tier: 'pro',
  max_members: 10,
  max_projects: 100,
  member_count: 3,
  settings: {},
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const mockAdminMember: OrganizationMember = {
  id: 'member-1',
  user_id: 'user-1',
  email: 'admin@example.com',
  display_name: 'Admin User',
  role: 'admin',
  joined_at: '2024-01-01T00:00:00Z',
  invited_by_name: null,
};

const mockRegularMember: OrganizationMember = {
  id: 'member-2',
  user_id: 'user-2',
  email: 'member@example.com',
  display_name: 'Regular Member',
  role: 'member',
  joined_at: '2024-01-02T00:00:00Z',
  invited_by_name: 'Admin User',
};

const mockViewerMember: OrganizationMember = {
  id: 'member-3',
  user_id: 'user-3',
  email: 'viewer@example.com',
  display_name: 'Viewer User',
  role: 'viewer',
  joined_at: '2024-01-03T00:00:00Z',
  invited_by_name: 'Admin User',
};

// Mock AuthContext
const mockUser = {
  id: 'user-1',
  email: 'admin@example.com',
  display_name: 'Admin User',
};

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: mockUser,
    token: 'test-token',
    isAuthenticated: true,
  }),
}));

// Mock organizations API
const mockGet = vi.fn();
const mockUpdate = vi.fn();
const mockDelete = vi.fn();
const mockListMembers = vi.fn();
const mockGetCurrentUserMembership = vi.fn();
const mockChangeMemberRole = vi.fn();
const mockRemoveMember = vi.fn();
const mockInviteMember = vi.fn();
const mockListInvites = vi.fn();
const mockCancelInvite = vi.fn();

vi.mock('@/lib/api/organizations', () => ({
  organizationsApi: {
    get: (orgId: string) => mockGet(orgId),
    update: (orgId: string, data: unknown) => mockUpdate(orgId, data),
    delete: (orgId: string) => mockDelete(orgId),
    listMembers: (orgId: string) => mockListMembers(orgId),
    getCurrentUserMembership: (orgId: string) => mockGetCurrentUserMembership(orgId),
    changeMemberRole: (orgId: string, memberId: string, role: string) => 
      mockChangeMemberRole(orgId, memberId, role),
    removeMember: (orgId: string, memberId: string) => mockRemoveMember(orgId, memberId),
    inviteMember: (orgId: string, data: unknown) => mockInviteMember(orgId, data),
    listInvites: (orgId: string) => mockListInvites(orgId),
    cancelInvite: (orgId: string, inviteId: string) => mockCancelInvite(orgId, inviteId),
  },
}));

// Mock TeamsTab component
vi.mock('@/components/teams/TeamsTab', () => ({
  TeamsTab: ({ isAdmin }: { isAdmin: boolean }) => (
    <div data-testid="teams-tab">
      Teams Tab {isAdmin ? '(Admin)' : '(Non-Admin)'}
    </div>
  ),
}));

const renderOrganizationSettingsPage = (orgId = 'org-1') => {
  return render(
    <MemoryRouter initialEntries={[`/organizations/${orgId}/settings`]}>
      <Routes>
        <Route path="/organizations/:orgId/settings" element={<OrganizationSettingsPage />} />
      </Routes>
    </MemoryRouter>
  );
};

describe('OrganizationSettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset mockUser to default admin
    mockUser.id = 'user-1';
    mockUser.email = 'admin@example.com';
    mockUser.display_name = 'Admin User';
    
    mockGet.mockResolvedValue(mockOrganization);
    mockListMembers.mockResolvedValue([mockAdminMember, mockRegularMember, mockViewerMember]);
    mockListInvites.mockResolvedValue([]);
  });

  describe('Admin Role Check', () => {
    it('shows admin features when user is admin', async () => {
      mockGetCurrentUserMembership.mockResolvedValue(mockAdminMember);
      renderOrganizationSettingsPage();

      await waitFor(() => {
        expect(screen.getByText('Test Organization')).toBeInTheDocument();
      });

      // Switch to members tab
      const membersTab = screen.getAllByText('Members')[0];
      membersTab.click();

      await waitFor(() => {
        // Admin should see role change controls
        const selects = screen.getAllByRole('combobox');
        expect(selects.length).toBeGreaterThan(0);
      });
    });

    it('shows admin features when user is owner', async () => {
      const ownerMember: OrganizationMember = {
        ...mockAdminMember,
        role: 'owner',
      };
      mockGetCurrentUserMembership.mockResolvedValue(ownerMember);
      renderOrganizationSettingsPage();

      await waitFor(() => {
        expect(screen.getByText('Test Organization')).toBeInTheDocument();
      });

      // Switch to members tab
      const membersTab = screen.getAllByText('Members')[0];
      membersTab.click();

      await waitFor(() => {
        // Owner should see role change controls
        const selects = screen.getAllByRole('combobox');
        expect(selects.length).toBeGreaterThan(0);
      });
    });

    it('hides admin features when user is regular member', async () => {
      // Change mock user to regular member
      mockUser.id = 'user-2';
      mockUser.email = 'member@example.com';
      mockUser.display_name = 'Regular Member';
      
      mockGetCurrentUserMembership.mockResolvedValue(mockRegularMember);
      renderOrganizationSettingsPage();

      await waitFor(() => {
        expect(screen.getByText('Test Organization')).toBeInTheDocument();
      });

      // Switch to members tab
      const membersTab = screen.getAllByText('Members')[0];
      membersTab.click();

      await waitFor(() => {
        expect(screen.getByText('Regular Member')).toBeInTheDocument();
      });

      // Regular member should NOT see role change controls
      const selects = screen.queryAllByRole('combobox');
      expect(selects.length).toBe(0);
    });

    it('hides admin features when user is viewer', async () => {
      // Change mock user to viewer
      mockUser.id = 'user-3';
      mockUser.email = 'viewer@example.com';
      mockUser.display_name = 'Viewer User';
      
      mockGetCurrentUserMembership.mockResolvedValue(mockViewerMember);
      renderOrganizationSettingsPage();

      await waitFor(() => {
        expect(screen.getByText('Test Organization')).toBeInTheDocument();
      });

      // Switch to members tab
      const membersTab = screen.getAllByText('Members')[0];
      membersTab.click();

      await waitFor(() => {
        expect(screen.getByText('Viewer User')).toBeInTheDocument();
      });

      // Viewer should NOT see role change controls
      const selects = screen.queryAllByRole('combobox');
      expect(selects.length).toBe(0);
    });

    it('passes correct isAdmin prop to TeamsTab', async () => {
      mockGetCurrentUserMembership.mockResolvedValue(mockAdminMember);
      renderOrganizationSettingsPage();

      await waitFor(() => {
        expect(screen.getByText('Test Organization')).toBeInTheDocument();
      });

      // Switch to teams tab
      const teamsTab = screen.getByText('Teams');
      teamsTab.click();

      await waitFor(() => {
        expect(screen.getByTestId('teams-tab')).toHaveTextContent('(Admin)');
      });
    });

    it('passes correct isAdmin prop to TeamsTab for non-admin', async () => {
      mockUser.id = 'user-2';
      mockGetCurrentUserMembership.mockResolvedValue(mockRegularMember);
      renderOrganizationSettingsPage();

      await waitFor(() => {
        expect(screen.getByText('Test Organization')).toBeInTheDocument();
      });

      // Switch to teams tab
      const teamsTab = screen.getByText('Teams');
      teamsTab.click();

      await waitFor(() => {
        expect(screen.getByTestId('teams-tab')).toHaveTextContent('(Non-Admin)');
      });
    });
  });

  describe('Membership Loading', () => {
    it('fetches organization and membership on mount', async () => {
      mockGetCurrentUserMembership.mockResolvedValue(mockAdminMember);
      renderOrganizationSettingsPage();

      await waitFor(() => {
        expect(mockGet).toHaveBeenCalledWith('org-1');
        expect(mockGetCurrentUserMembership).toHaveBeenCalledWith('org-1');
      });
    });

    it('handles membership fetch failure gracefully', async () => {
      mockGetCurrentUserMembership.mockRejectedValue(new Error('Failed to fetch'));
      renderOrganizationSettingsPage();

      await waitFor(() => {
        expect(screen.getByText(/failed to load organization/i)).toBeInTheDocument();
      });
    });

    it('handles missing membership (non-member access)', async () => {
      mockGetCurrentUserMembership.mockResolvedValue(null);
      renderOrganizationSettingsPage();

      await waitFor(() => {
        expect(screen.getByText('Test Organization')).toBeInTheDocument();
      });

      // Non-member should not have admin access
      const membersTab = screen.getAllByText('Members')[0];
      membersTab.click();

      await waitFor(() => {
        // Should not see role change controls
        const selects = screen.queryAllByRole('combobox');
        expect(selects.length).toBe(0);
      });
    });
  });

  describe('Tab Navigation', () => {
    it('shows general tab by default', async () => {
      mockGetCurrentUserMembership.mockResolvedValue(mockAdminMember);
      renderOrganizationSettingsPage();

      await waitFor(() => {
        expect(screen.getByText('Test Organization')).toBeInTheDocument();
      });

      expect(screen.getByText(/organization name/i)).toBeInTheDocument();
    });

    it('switches to members tab', async () => {
      mockGetCurrentUserMembership.mockResolvedValue(mockAdminMember);
      renderOrganizationSettingsPage();

      await waitFor(() => {
        expect(screen.getByText('Test Organization')).toBeInTheDocument();
      });

      const membersTab = screen.getAllByText('Members')[0];
      membersTab.click();

      await waitFor(() => {
        expect(mockListMembers).toHaveBeenCalledWith('org-1');
      });
    });

    it('switches to invites tab', async () => {
      mockGetCurrentUserMembership.mockResolvedValue(mockAdminMember);
      renderOrganizationSettingsPage();

      await waitFor(() => {
        expect(screen.getByText('Test Organization')).toBeInTheDocument();
      });

      const invitesTab = screen.getAllByText('Invites')[0];
      invitesTab.click();

      await waitFor(() => {
        expect(mockListInvites).toHaveBeenCalledWith('org-1');
      });
    });
  });
});
