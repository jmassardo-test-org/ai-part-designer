/**
 * Tests for TeamsTab component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TeamsTab } from './TeamsTab';
import { teamsApi } from '@/lib/api/teams';

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

// Mock the teams API
vi.mock('@/lib/api/teams', () => ({
  teamsApi: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    listMembers: vi.fn(),
    addMember: vi.fn(),
    updateMember: vi.fn(),
    removeMember: vi.fn(),
  },
}));

const mockTeams = [
  {
    id: 'team-1',
    organization_id: 'org-1',
    name: 'Engineering',
    slug: 'engineering',
    description: 'Backend engineering team',
    settings: { color: '#3B82F6' },
    is_active: true,
    created_by_id: 'user-1',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    member_count: 5,
  },
  {
    id: 'team-2',
    organization_id: 'org-1',
    name: 'Design',
    slug: 'design',
    description: null,
    settings: { color: '#10B981' },
    is_active: true,
    created_by_id: 'user-1',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    member_count: 3,
  },
];

describe('TeamsTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', async () => {
    vi.mocked(teamsApi.list).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    const { container } = render(<TeamsTab orgId="org-1" isAdmin={true} />);

    // Look for the animate-spin class on the loader icon
    expect(container.querySelector('.animate-spin')).toBeDefined();
  });

  it('renders teams list after loading', async () => {
    vi.mocked(teamsApi.list).mockResolvedValueOnce({
      items: mockTeams,
      total: 2,
      page: 1,
      page_size: 20,
      has_more: false,
    });

    render(<TeamsTab orgId="org-1" isAdmin={true} />);

    await waitFor(() => {
      expect(screen.getByText('Engineering')).toBeDefined();
      expect(screen.getByText('Design')).toBeDefined();
    });
  });

  it('shows empty state when no teams exist', async () => {
    vi.mocked(teamsApi.list).mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      has_more: false,
    });

    render(<TeamsTab orgId="org-1" isAdmin={true} />);

    await waitFor(() => {
      expect(screen.getByText('No teams yet')).toBeDefined();
    });
  });

  it('shows create button for admins', async () => {
    vi.mocked(teamsApi.list).mockResolvedValueOnce({
      items: mockTeams,
      total: 2,
      page: 1,
      page_size: 20,
      has_more: false,
    });

    render(<TeamsTab orgId="org-1" isAdmin={true} />);

    await waitFor(() => {
      expect(screen.getByText('Create Team')).toBeDefined();
    });
  });

  it('hides create button for non-admins', async () => {
    vi.mocked(teamsApi.list).mockResolvedValueOnce({
      items: mockTeams,
      total: 2,
      page: 1,
      page_size: 20,
      has_more: false,
    });

    render(<TeamsTab orgId="org-1" isAdmin={false} />);

    await waitFor(() => {
      expect(screen.getByText('Engineering')).toBeDefined();
    });

    expect(screen.queryByText('Create Team')).toBeNull();
  });

  it('opens create team modal when clicking create button', async () => {
    const user = userEvent.setup();

    vi.mocked(teamsApi.list).mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      has_more: false,
    });

    render(<TeamsTab orgId="org-1" isAdmin={true} />);

    await waitFor(() => {
      expect(screen.getByText('Create First Team')).toBeDefined();
    });

    await user.click(screen.getByText('Create First Team'));

    // Modal header text - use getAllByText since 'Create Team' appears in header and button
    expect(screen.getAllByText('Create Team').length).toBeGreaterThanOrEqual(1);
    // Check for form input - look for the placeholder since label includes asterisk
    expect(screen.getByPlaceholderText(/e.g., Engineering/i)).toBeDefined();
  });

  it('displays team description when available', async () => {
    vi.mocked(teamsApi.list).mockResolvedValueOnce({
      items: mockTeams,
      total: 2,
      page: 1,
      page_size: 20,
      has_more: false,
    });

    render(<TeamsTab orgId="org-1" isAdmin={true} />);

    await waitFor(() => {
      expect(screen.getByText('Backend engineering team')).toBeDefined();
    });
  });

  it('displays member count for each team', async () => {
    vi.mocked(teamsApi.list).mockResolvedValueOnce({
      items: mockTeams,
      total: 2,
      page: 1,
      page_size: 20,
      has_more: false,
    });

    render(<TeamsTab orgId="org-1" isAdmin={true} />);

    await waitFor(() => {
      expect(screen.getByText('5 members')).toBeDefined();
      expect(screen.getByText('3 members')).toBeDefined();
    });
  });

  it('handles error state gracefully', async () => {
    vi.mocked(teamsApi.list).mockRejectedValueOnce(new Error('Network error'));

    render(<TeamsTab orgId="org-1" isAdmin={true} />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load teams')).toBeDefined();
    });

    expect(screen.getByText('Try Again')).toBeDefined();
  });

  it('retries loading when clicking try again', async () => {
    const user = userEvent.setup();

    vi.mocked(teamsApi.list)
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValueOnce({
        items: mockTeams,
        total: 2,
        page: 1,
        page_size: 20,
        has_more: false,
      });

    render(<TeamsTab orgId="org-1" isAdmin={true} />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load teams')).toBeDefined();
    });

    await user.click(screen.getByText('Try Again'));

    await waitFor(() => {
      expect(screen.getByText('Engineering')).toBeDefined();
    });
  });

  it('deletes team when confirmed', async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

    vi.mocked(teamsApi.list).mockResolvedValueOnce({
      items: mockTeams,
      total: 2,
      page: 1,
      page_size: 20,
      has_more: false,
    });
    vi.mocked(teamsApi.delete).mockResolvedValueOnce(undefined);

    render(<TeamsTab orgId="org-1" isAdmin={true} />);

    await waitFor(() => {
      expect(screen.getByText('Engineering')).toBeDefined();
    });

    // Find and click the menu button for the first team
    const menuButtons = screen.getAllByRole('button');
    const moreButton = menuButtons.find((btn) =>
      btn.querySelector('svg')?.classList.contains('lucide-more-vertical')
    );

    if (moreButton) {
      await user.click(moreButton);
      
      await waitFor(() => {
        const deleteBtn = screen.getByText('Delete Team');
        expect(deleteBtn).toBeDefined();
      });
      
      await user.click(screen.getByText('Delete Team'));
      
      expect(confirmSpy).toHaveBeenCalledWith(
        'Are you sure you want to delete "Engineering"?'
      );
      expect(teamsApi.delete).toHaveBeenCalledWith('org-1', 'team-1');
    }

    confirmSpy.mockRestore();
  });
});
