/**
 * Admin Dashboard Tests.
 *
 * Unit tests for the AdminDashboard component and its tabs.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AdminDashboard } from './AdminDashboard';
import { adminApi } from '@/lib/api/admin';

// Mock the ThemeContext
vi.mock('@/contexts/ThemeContext', () => ({
  useTheme: () => ({
    theme: 'dark',
    resolvedTheme: 'dark',
    setTheme: vi.fn(),
    toggleTheme: vi.fn(),
    isLoading: false,
  }),
  ThemeProvider: ({ children }: { children: React.ReactNode }) => children,
}));

// Mock the WebSocketContext
vi.mock('@/contexts/WebSocketContext', () => ({
  useWebSocket: () => ({
    isConnected: false,
    connectionState: 'disconnected',
    subscribe: vi.fn(),
    unsubscribe: vi.fn(),
    sendMessage: vi.fn(),
  }),
}));

// Mock Recharts to avoid rendering issues in tests
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => children,
  LineChart: ({ children }: { children: React.ReactNode }) => <div data-testid="line-chart">{children}</div>,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
}));

// Mock the auth context
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    token: 'mock-token',
    user: { role: 'admin' },
  }),
}));

// Mock the admin API
vi.mock('@/lib/api/admin', () => ({
  adminApi: {
    analytics: {
      getOverview: vi.fn(),
      getTimeSeriesAnalytics: vi.fn(),
      getUserAnalytics: vi.fn(),
      getGenerationAnalytics: vi.fn(),
      getJobAnalytics: vi.fn(),
      getStorageAnalytics: vi.fn(),
    },
    users: {
      listUsers: vi.fn(),
      getUser: vi.fn(),
      updateUser: vi.fn(),
      suspendUser: vi.fn(),
      unsuspendUser: vi.fn(),
      deleteUser: vi.fn(),
      warnUser: vi.fn(),
    },
    projects: {
      listProjects: vi.fn(),
      getProject: vi.fn(),
      deleteProject: vi.fn(),
      transferProject: vi.fn(),
      suspendProject: vi.fn(),
      unsuspendProject: vi.fn(),
    },
    designs: {
      listDesigns: vi.fn(),
      getDesign: vi.fn(),
      deleteDesign: vi.fn(),
      restoreDesign: vi.fn(),
      setVisibility: vi.fn(),
    },
    templates: {
      listTemplates: vi.fn(),
      getTemplate: vi.fn(),
      createTemplate: vi.fn(),
      updateTemplate: vi.fn(),
      deleteTemplate: vi.fn(),
      enableTemplate: vi.fn(),
      disableTemplate: vi.fn(),
      featureTemplate: vi.fn(),
      unfeatureTemplate: vi.fn(),
      cloneTemplate: vi.fn(),
    },
    jobs: {
      listJobs: vi.fn(),
      getJob: vi.fn(),
      cancelJob: vi.fn(),
      retryJob: vi.fn(),
    },
    moderation: {
      getQueue: vi.fn(),
      getStats: vi.fn(),
      getItem: vi.fn(),
      approveItem: vi.fn(),
      rejectItem: vi.fn(),
      escalateItem: vi.fn(),
    },
  },
}));

const mockAdminApi = vi.mocked(adminApi, true);

// Wrapper for rendering with Router
const renderWithRouter = (ui: React.ReactElement) => {
  return render(
    <MemoryRouter>
      {ui}
    </MemoryRouter>
  );
};

describe('AdminDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Setup default mock responses
    mockAdminApi.analytics.getOverview.mockResolvedValue({
      total_users: 100,
      active_users_today: 25,
      active_users_week: 50,
      active_users_month: 75,
      total_projects: 200,
      total_designs: 500,
      total_templates: 20,
      total_jobs: 1000,
      pending_jobs: 5,
      failed_jobs: 2,
      storage_used_bytes: 1073741824, // 1 GB
      storage_limit_bytes: 10737418240, // 10 GB
    });

    // Setup mock time series data
    mockAdminApi.analytics.getTimeSeriesAnalytics.mockResolvedValue({
      new_users: [
        { date: '2024-01-01', value: 5 },
        { date: '2024-01-02', value: 8 },
        { date: '2024-01-03', value: 3 },
      ],
      active_users: [
        { date: '2024-01-01', value: 20 },
        { date: '2024-01-02', value: 25 },
        { date: '2024-01-03', value: 18 },
      ],
      new_projects: [
        { date: '2024-01-01', value: 10 },
        { date: '2024-01-02', value: 12 },
        { date: '2024-01-03', value: 8 },
      ],
      new_designs: [
        { date: '2024-01-01', value: 15 },
        { date: '2024-01-02', value: 22 },
        { date: '2024-01-03', value: 18 },
      ],
      jobs_completed: [
        { date: '2024-01-01', value: 50 },
        { date: '2024-01-02', value: 45 },
        { date: '2024-01-03', value: 60 },
      ],
    });

    mockAdminApi.users.listUsers.mockResolvedValue({
      users: [
        {
          id: '1',
          email: 'user1@example.com',
          full_name: 'Test User',
          role: 'user',
          is_active: true,
          is_suspended: false,
          suspension_reason: null,
          suspended_until: null,
          email_verified: true,
          created_at: '2024-01-01T00:00:00Z',
          last_login_at: '2024-01-15T00:00:00Z',
          storage_used_bytes: 1048576,
          project_count: 5,
          design_count: 10,
          warning_count: 0,
          subscription_tier: 'free',
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
    });

    mockAdminApi.projects.listProjects.mockResolvedValue({
      projects: [],
      total: 0,
      page: 1,
      page_size: 20,
    });

    mockAdminApi.designs.listDesigns.mockResolvedValue({
      designs: [],
      total: 0,
      page: 1,
      page_size: 20,
    });

    mockAdminApi.templates.listTemplates.mockResolvedValue({
      templates: [],
      total: 0,
      page: 1,
      page_size: 20,
    });

    mockAdminApi.jobs.listJobs.mockResolvedValue({
      jobs: [],
      total: 0,
      page: 1,
      page_size: 20,
    });

    mockAdminApi.moderation.getQueue.mockResolvedValue({
      items: [],
      total: 0,
    });

    mockAdminApi.moderation.getStats.mockResolvedValue({
      pending_count: 3,
      escalated_count: 1,
      approved_today: 10,
      rejected_today: 2,
      appeals_pending: 0,
      avg_review_time_hours: 2.5,
    });
  });

  describe('Layout and Navigation', () => {
    it('renders the admin dashboard header', async () => {
      renderWithRouter(<AdminDashboard />);

      expect(screen.getByText('Admin Dashboard')).toBeInTheDocument();
      expect(screen.getByText('System management and monitoring')).toBeInTheDocument();
    });

    it('renders all navigation tabs', async () => {
      renderWithRouter(<AdminDashboard />);

      expect(screen.getByRole('button', { name: /analytics/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /users/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /projects/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /designs/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /templates/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /jobs/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /moderation/i })).toBeInTheDocument();
    });

    it('defaults to analytics tab', async () => {
      renderWithRouter(<AdminDashboard />);

      await waitFor(() => {
        expect(mockAdminApi.analytics.getOverview).toHaveBeenCalled();
      });
    });

    it('switches to users tab when clicked', async () => {
      renderWithRouter(<AdminDashboard />);

      fireEvent.click(screen.getByRole('button', { name: /users/i }));

      await waitFor(() => {
        expect(mockAdminApi.users.listUsers).toHaveBeenCalled();
      });
    });

    it('switches to projects tab when clicked', async () => {
      renderWithRouter(<AdminDashboard />);

      fireEvent.click(screen.getByRole('button', { name: /projects/i }));

      await waitFor(() => {
        expect(mockAdminApi.projects.listProjects).toHaveBeenCalled();
      });
    });
  });

  describe('Analytics Tab', () => {
    it('displays analytics overview stats', async () => {
      renderWithRouter(<AdminDashboard />);

      await waitFor(() => {
        expect(screen.getByText('100')).toBeInTheDocument(); // Total Users
        expect(screen.getByText('25')).toBeInTheDocument(); // Active Today
      });
    });

    it('displays storage information', async () => {
      renderWithRouter(<AdminDashboard />);

      await waitFor(() => {
        expect(screen.getByText('Storage')).toBeInTheDocument();
      });
    });

    it('displays job queue stats', async () => {
      renderWithRouter(<AdminDashboard />);

      await waitFor(() => {
        expect(screen.getByText('Job Queue')).toBeInTheDocument();
        expect(screen.getByText('5')).toBeInTheDocument(); // Pending Jobs
        expect(screen.getByText('2')).toBeInTheDocument(); // Failed Jobs
      });
    });

    it('shows error state when API fails', async () => {
      mockAdminApi.analytics.getOverview.mockRejectedValueOnce(new Error('API Error'));

      renderWithRouter(<AdminDashboard />);

      await waitFor(() => {
        expect(screen.getByText('Failed to load analytics data')).toBeInTheDocument();
      });
    });

    it('allows retry on error', async () => {
      mockAdminApi.analytics.getOverview.mockRejectedValueOnce(new Error('API Error'));

      renderWithRouter(<AdminDashboard />);

      await waitFor(() => {
        expect(screen.getByText('Retry')).toBeInTheDocument();
      });

      // Reset mock to succeed
      mockAdminApi.analytics.getOverview.mockResolvedValueOnce({
        total_users: 100,
        active_users_today: 25,
        active_users_week: 50,
        active_users_month: 75,
        total_projects: 200,
        total_designs: 500,
        total_templates: 20,
        total_jobs: 1000,
        pending_jobs: 5,
        failed_jobs: 2,
        storage_used_bytes: 1073741824,
        storage_limit_bytes: 10737418240,
      });

      fireEvent.click(screen.getByText('Retry'));

      await waitFor(() => {
        expect(mockAdminApi.analytics.getOverview).toHaveBeenCalledTimes(2);
      });
    });

    it('fetches time series data on load', async () => {
      renderWithRouter(<AdminDashboard />);

      await waitFor(() => {
        expect(mockAdminApi.analytics.getTimeSeriesAnalytics).toHaveBeenCalledWith(30); // Default 30 days
      });
    });

    it('displays date range selector with correct options', async () => {
      renderWithRouter(<AdminDashboard />);

      await waitFor(() => {
        const select = screen.getByRole('combobox');
        expect(select).toBeInTheDocument();
        expect(screen.getByText('Last 7 Days')).toBeInTheDocument();
        expect(screen.getByText('Last 30 Days')).toBeInTheDocument();
        expect(screen.getByText('Last 90 Days')).toBeInTheDocument();
      });
    });

    it('changes date range and refetches data', async () => {
      renderWithRouter(<AdminDashboard />);

      await waitFor(() => {
        expect(mockAdminApi.analytics.getTimeSeriesAnalytics).toHaveBeenCalled();
      });

      const select = screen.getByRole('combobox');
      fireEvent.change(select, { target: { value: '7' } });

      await waitFor(() => {
        expect(mockAdminApi.analytics.getTimeSeriesAnalytics).toHaveBeenCalledWith(7);
      });
    });

    it('displays export CSV button', async () => {
      renderWithRouter(<AdminDashboard />);

      await waitFor(() => {
        expect(screen.getByText('Export CSV')).toBeInTheDocument();
      });
    });

    it('displays trends chart section', async () => {
      renderWithRouter(<AdminDashboard />);

      await waitFor(() => {
        expect(screen.getByText('Trends Over Time')).toBeInTheDocument();
      });
    });

    it('clickable stat cards navigate to correct tabs', async () => {
      renderWithRouter(<AdminDashboard />);

      await waitFor(() => {
        expect(screen.getByText('Total Users')).toBeInTheDocument();
      });

      // Click on Total Users stat card (it should be a button)
      const userStatCard = screen.getByRole('button', { name: /total users/i });
      fireEvent.click(userStatCard);

      await waitFor(() => {
        // Should now be on users tab and loading users
        expect(mockAdminApi.users.listUsers).toHaveBeenCalled();
      });
    });

    it('clickable stat cards for projects navigate to projects tab', async () => {
      renderWithRouter(<AdminDashboard />);

      await waitFor(() => {
        expect(screen.getByText('Total Projects')).toBeInTheDocument();
      });

      const projectStatCard = screen.getByRole('button', { name: /total projects/i });
      fireEvent.click(projectStatCard);

      await waitFor(() => {
        expect(mockAdminApi.projects.listProjects).toHaveBeenCalled();
      });
    });
  });

  describe('Users Tab', () => {
    it('displays user list', async () => {
      renderWithRouter(<AdminDashboard />);

      fireEvent.click(screen.getByRole('button', { name: /users/i }));

      await waitFor(() => {
        expect(screen.getByText('user1@example.com')).toBeInTheDocument();
        expect(screen.getByText('Test User')).toBeInTheDocument();
      });
    });

    it('displays role and status badges', async () => {
      renderWithRouter(<AdminDashboard />);

      fireEvent.click(screen.getByRole('button', { name: /users/i }));

      await waitFor(() => {
        // Check for role badge - RoleBadge displays 'User' (capitalized)
        expect(screen.getAllByText('User').length).toBeGreaterThan(0);
        // Check for status badge with getAllByText since 'Active' appears in dropdown too
        const activeBadges = screen.getAllByText('Active');
        expect(activeBadges.length).toBeGreaterThan(0);
      });
    });

    it('has search input', async () => {
      renderWithRouter(<AdminDashboard />);

      fireEvent.click(screen.getByRole('button', { name: /users/i }));

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Search by email or name...')).toBeInTheDocument();
      });
    });

    it('has role filter dropdown', async () => {
      renderWithRouter(<AdminDashboard />);

      fireEvent.click(screen.getByRole('button', { name: /users/i }));

      await waitFor(() => {
        expect(screen.getByDisplayValue('All Roles')).toBeInTheDocument();
      });
    });

    it('has status filter dropdown', async () => {
      renderWithRouter(<AdminDashboard />);

      fireEvent.click(screen.getByRole('button', { name: /users/i }));

      await waitFor(() => {
        expect(screen.getByDisplayValue('All Status')).toBeInTheDocument();
      });
    });

    it('shows empty state when no users', async () => {
      mockAdminApi.users.listUsers.mockResolvedValueOnce({
        users: [],
        total: 0,
        page: 1,
        page_size: 20,
      });

      renderWithRouter(<AdminDashboard />);

      fireEvent.click(screen.getByRole('button', { name: /users/i }));

      await waitFor(() => {
        expect(screen.getByText('No users found')).toBeInTheDocument();
      });
    });
  });

  describe('Projects Tab', () => {
    it('displays project list header', async () => {
      renderWithRouter(<AdminDashboard />);

      fireEvent.click(screen.getByRole('button', { name: /projects/i }));

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Search projects...')).toBeInTheDocument();
      });
    });

    it('has visibility filter', async () => {
      renderWithRouter(<AdminDashboard />);

      fireEvent.click(screen.getByRole('button', { name: /projects/i }));

      await waitFor(() => {
        expect(screen.getByDisplayValue('All Visibility')).toBeInTheDocument();
      });
    });

    it('shows empty state when no projects', async () => {
      renderWithRouter(<AdminDashboard />);

      fireEvent.click(screen.getByRole('button', { name: /projects/i }));

      await waitFor(() => {
        expect(screen.getByText('No projects found')).toBeInTheDocument();
      });
    });

    it('has status filter dropdown', async () => {
      renderWithRouter(<AdminDashboard />);

      fireEvent.click(screen.getByRole('button', { name: /projects/i }));

      await waitFor(() => {
        expect(screen.getByDisplayValue('All Status')).toBeInTheDocument();
      });
    });

    it('displays projects with status column', async () => {
      mockAdminApi.projects.listProjects.mockResolvedValue({
        projects: [{
          id: 'proj-1',
          name: 'Test Project',
          description: 'A test project',
          owner_id: 'user-1',
          owner_email: 'test@example.com',
          is_public: true,
          design_count: 5,
          storage_used_bytes: 1024,
          status: 'active',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }],
        total: 1,
        page: 1,
        page_size: 20,
      });

      renderWithRouter(<AdminDashboard />);

      fireEvent.click(screen.getByRole('button', { name: /projects/i }));

      await waitFor(() => {
        expect(screen.getByText('Test Project')).toBeInTheDocument();
        // 'Active' appears multiple times (in dropdown and status badge), use getAllByText
        expect(screen.getAllByText('Active').length).toBeGreaterThan(0);
      });
    });
  });

  describe('Designs Tab', () => {
    it('displays design list header', async () => {
      renderWithRouter(<AdminDashboard />);

      fireEvent.click(screen.getByRole('button', { name: /designs/i }));

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Search designs...')).toBeInTheDocument();
      });
    });

    it('has show deleted checkbox', async () => {
      renderWithRouter(<AdminDashboard />);

      fireEvent.click(screen.getByRole('button', { name: /designs/i }));

      await waitFor(() => {
        expect(screen.getByText('Show Deleted')).toBeInTheDocument();
      });
    });

    it('shows empty state when no designs', async () => {
      renderWithRouter(<AdminDashboard />);

      fireEvent.click(screen.getByRole('button', { name: /designs/i }));

      await waitFor(() => {
        expect(screen.getByText('No designs found')).toBeInTheDocument();
      });
    });
  });

  describe('Templates Tab', () => {
    it('displays template list header', async () => {
      renderWithRouter(<AdminDashboard />);

      fireEvent.click(screen.getByRole('button', { name: /templates/i }));

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Search templates...')).toBeInTheDocument();
      });
    });

    it('has category filter', async () => {
      renderWithRouter(<AdminDashboard />);

      fireEvent.click(screen.getByRole('button', { name: /templates/i }));

      await waitFor(() => {
        expect(screen.getByDisplayValue('All Categories')).toBeInTheDocument();
      });
    });

    it('has create template button', async () => {
      renderWithRouter(<AdminDashboard />);

      fireEvent.click(screen.getByRole('button', { name: /templates/i }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /create template/i })).toBeInTheDocument();
      });
    });

    it('displays template tier column', async () => {
      mockAdminApi.templates.listTemplates.mockResolvedValue({
        templates: [{
          id: 'tmpl-1',
          name: 'Test Template',
          slug: 'test-template',
          description: 'A test template',
          category: 'enclosure',
          min_tier: 'professional',
          created_by: 'user-1',
          creator_email: 'admin@example.com',
          is_active: true,
          is_enabled: true,
          is_featured: false,
          use_count: 10,
          parameter_schema: {},
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }],
        total: 1,
        page: 1,
        page_size: 20,
      });

      renderWithRouter(<AdminDashboard />);

      fireEvent.click(screen.getByRole('button', { name: /templates/i }));

      await waitFor(() => {
        expect(screen.getByText('Test Template')).toBeInTheDocument();
        expect(screen.getByText('Pro')).toBeInTheDocument();
      });
    });

    it('shows empty state when no templates', async () => {
      renderWithRouter(<AdminDashboard />);

      fireEvent.click(screen.getByRole('button', { name: /templates/i }));

      await waitFor(() => {
        expect(screen.getByText('No templates found')).toBeInTheDocument();
      });
    });
  });

  describe('Jobs Tab', () => {
    it('displays job filters', async () => {
      renderWithRouter(<AdminDashboard />);

      fireEvent.click(screen.getByRole('button', { name: /jobs/i }));

      await waitFor(() => {
        expect(screen.getByDisplayValue('All Status')).toBeInTheDocument();
        expect(screen.getByDisplayValue('All Types')).toBeInTheDocument();
      });
    });

    it('shows empty state when no jobs', async () => {
      renderWithRouter(<AdminDashboard />);

      fireEvent.click(screen.getByRole('button', { name: /jobs/i }));

      await waitFor(() => {
        expect(screen.getByText('No jobs found')).toBeInTheDocument();
      });
    });
  });

  describe('Moderation Tab', () => {
    it('displays moderation stats', async () => {
      renderWithRouter(<AdminDashboard />);

      fireEvent.click(screen.getByRole('button', { name: /moderation/i }));

      await waitFor(() => {
        // Use getAllByText since these texts appear in both stats cards and dropdowns
        const pendingReviewElements = screen.getAllByText('Pending Review');
        expect(pendingReviewElements.length).toBeGreaterThan(0);
        const escalatedElements = screen.getAllByText('Escalated');
        expect(escalatedElements.length).toBeGreaterThan(0);
        expect(screen.getByText('Approved Today')).toBeInTheDocument();
        expect(screen.getByText('Rejected Today')).toBeInTheDocument();
      });
    });

    it('displays moderation queue header', async () => {
      renderWithRouter(<AdminDashboard />);

      fireEvent.click(screen.getByRole('button', { name: /moderation/i }));

      await waitFor(() => {
        expect(screen.getByText('Moderation Queue')).toBeInTheDocument();
      });
    });

    it('has status filter dropdown', async () => {
      renderWithRouter(<AdminDashboard />);

      fireEvent.click(screen.getByRole('button', { name: /moderation/i }));

      await waitFor(() => {
        // The dropdown should have 'Pending Review' as default
        const selects = screen.getAllByRole('combobox');
        expect(selects.length).toBeGreaterThan(0);
      });
    });

    it('shows empty state when no moderation items', async () => {
      renderWithRouter(<AdminDashboard />);

      fireEvent.click(screen.getByRole('button', { name: /moderation/i }));

      await waitFor(() => {
        expect(screen.getByText('No items in queue')).toBeInTheDocument();
      });
    });
  });
});
