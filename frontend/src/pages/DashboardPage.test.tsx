/**
 * Tests for DashboardPage component.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { DashboardPage } from './DashboardPage';

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

// Mock AuthContext
const mockUser = {
  id: '1',
  email: 'test@example.com',
  display_name: 'Test User',
  tier: 'free',
};

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: mockUser,
    token: 'test-token',
    isAuthenticated: true,
  }),
}));

// Mock fetch
const mockDashboardData = {
  stats: {
    total_projects: 5,
    total_designs: 12,
    designs_this_month: 3,
    generations_this_month: 8,
    exports_this_month: 4,
  },
  recent_designs: [
    {
      id: '1',
      name: 'Test Design 1',
      project_id: 'p1',
      project_name: 'Project 1',
      thumbnail_url: null,
      source_type: 'generated',
      status: 'completed',
      created_at: '2026-01-20T10:00:00Z',
      updated_at: '2026-01-20T10:00:00Z',
    },
    {
      id: '2',
      name: 'Test Design 2',
      project_id: 'p2',
      project_name: 'Project 2',
      thumbnail_url: null,
      source_type: 'uploaded',
      status: 'completed',
      created_at: '2026-01-19T10:00:00Z',
      updated_at: '2026-01-19T10:00:00Z',
    },
  ],
  recent_activity: [],
};

const renderDashboardPage = () => {
  return render(
    <BrowserRouter>
      <DashboardPage />
    </BrowserRouter>
  );
};

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  it('shows loading state initially', () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation(() => 
      new Promise(() => {}) // Never resolves to keep loading state
    );

    renderDashboardPage();

    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders welcome message with user name', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockDashboardData),
    });

    renderDashboardPage();

    await waitFor(() => {
      expect(screen.getByText(/welcome back, test user!/i)).toBeInTheDocument();
    });
  });

  it('displays dashboard statistics', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockDashboardData),
    });

    renderDashboardPage();

    await waitFor(() => {
      expect(screen.getByText('5')).toBeInTheDocument(); // total projects
      expect(screen.getByText('12')).toBeInTheDocument(); // total designs
    });
  });

  it('shows quick action links', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockDashboardData),
    });

    renderDashboardPage();

    await waitFor(() => {
      expect(screen.getByRole('link', { name: /new part/i })).toBeInTheDocument();
      expect(screen.getAllByText(/templates/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText(/projects/i).length).toBeGreaterThanOrEqual(1);
    });
  });

  it('links to create page', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockDashboardData),
    });

    renderDashboardPage();

    await waitFor(() => {
      const newPartLink = screen.getByRole('link', { name: /new part/i });
      expect(newPartLink).toHaveAttribute('href', '/create');
    });
  });

  it('links to templates page', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockDashboardData),
    });

    renderDashboardPage();

    await waitFor(() => {
      const templatesLink = screen.getByRole('link', { name: /templates/i });
      expect(templatesLink).toHaveAttribute('href', '/templates');
    });
  });

  it('links to projects page', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockDashboardData),
    });

    renderDashboardPage();

    await waitFor(() => {
      // Multiple project links may exist
      const projectsLinks = screen.getAllByRole('link', { name: /projects/i });
      expect(projectsLinks.length).toBeGreaterThanOrEqual(1);
      expect(projectsLinks[0]).toHaveAttribute('href', '/projects');
    });
  });

  it('shows error state with retry button', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Failed to load dashboard data'));

    renderDashboardPage();

    await waitFor(() => {
      expect(screen.getByText(/failed to load dashboard/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
    });
  });

  it('retries fetch on retry button click', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>)
      .mockRejectedValueOnce(new Error('Failed'))
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockDashboardData),
      });

    renderDashboardPage();

    await waitFor(() => {
      expect(screen.getByText(/failed/i)).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /try again/i }));

    await waitFor(() => {
      expect(screen.getByText(/welcome back/i)).toBeInTheDocument();
    });
  });

  it('handles API error response', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 500,
    });

    renderDashboardPage();

    await waitFor(() => {
      expect(screen.getByText(/failed to load dashboard data/i)).toBeInTheDocument();
    });
  });

  it('displays recent designs', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockDashboardData),
    });

    renderDashboardPage();

    await waitFor(() => {
      expect(screen.getByText('Test Design 1')).toBeInTheDocument();
      expect(screen.getByText('Test Design 2')).toBeInTheDocument();
    });
  });

  it('shows empty state when no data', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        stats: {
          total_projects: 0,
          total_designs: 0,
          designs_this_month: 0,
          generations_this_month: 0,
          exports_this_month: 0,
        },
        recent_designs: [],
        recent_activity: [],
      }),
    });

    renderDashboardPage();

    await waitFor(() => {
      expect(screen.getAllByText('0').length).toBeGreaterThanOrEqual(1);
    });
  });
});
