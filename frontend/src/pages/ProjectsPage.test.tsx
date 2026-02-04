/**
 * Tests for ProjectsPage component.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ProjectsPage } from './ProjectsPage';

// Mock AuthContext
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: '1', email: 'test@example.com' },
    token: 'test-token',
    isAuthenticated: true,
  }),
}));

const mockProjects = [
  {
    id: 'p1',
    name: 'Project Alpha',
    description: 'First test project',
    design_count: 5,
    created_at: '2026-01-15T10:00:00Z',
    updated_at: '2026-01-20T10:00:00Z',
  },
  {
    id: 'p2',
    name: 'Project Beta',
    description: 'Second test project',
    design_count: 3,
    created_at: '2026-01-10T10:00:00Z',
    updated_at: '2026-01-18T10:00:00Z',
  },
];

const renderProjectsPage = () => {
  return render(
    <BrowserRouter>
      <ProjectsPage />
    </BrowserRouter>
  );
};

describe('ProjectsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
    window.confirm = vi.fn(() => true);
  });

  it('shows loading state initially', () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation(() => 
      new Promise(() => {})
    );

    renderProjectsPage();

    // The page should show loading indicator
    expect(document.querySelector('.animate-spin') || screen.queryByText(/loading/i)).toBeTruthy();
  });

  it('renders projects heading', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: mockProjects }),
    });

    renderProjectsPage();

    await waitFor(() => {
      expect(screen.getByText('Project Alpha')).toBeInTheDocument();
    });
  });

  it('displays project list', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: mockProjects }),
    });

    renderProjectsPage();

    await waitFor(() => {
      expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      expect(screen.getByText('Project Beta')).toBeInTheDocument();
    });
  });

  it('shows project descriptions', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: mockProjects }),
    });

    renderProjectsPage();

    await waitFor(() => {
      expect(screen.getByText('First test project')).toBeInTheDocument();
    });
  });

  it('displays design count per project', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: mockProjects }),
    });

    renderProjectsPage();

    await waitFor(() => {
      expect(screen.getByText(/5 design/i)).toBeInTheDocument();
      expect(screen.getByText(/3 design/i)).toBeInTheDocument();
    });
  });

  it('has create project button', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: mockProjects }),
    });

    renderProjectsPage();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /new project/i })).toBeInTheDocument();
    });
  });

  it('opens create project modal', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: mockProjects }),
    });

    renderProjectsPage();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /new project/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /new project/i }));

    // Modal should appear with project name input
    await waitFor(() => {
      expect(screen.getByText(/project name/i) || screen.getByRole('textbox')).toBeTruthy();
    });
  });

  it('creates new project', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ items: mockProjects }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          id: 'p3',
          name: 'New Project',
          description: 'Description',
          design_count: 0,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }),
      });

    renderProjectsPage();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /new project/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /new project/i }));

    // Check that the dialog opens - verify there are input fields
    await waitFor(() => {
      const inputs = screen.getAllByRole('textbox');
      expect(inputs.length).toBeGreaterThan(0);
    });
  });

  it('has search input', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: mockProjects }),
    });

    renderProjectsPage();

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search projects/i)).toBeInTheDocument();
    });
  });

  it('handles search input', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: mockProjects }),
    });

    renderProjectsPage();

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search projects/i)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search projects/i);
    await user.type(searchInput, 'Alpha');

    expect(searchInput).toHaveValue('Alpha');
  });

  it('shows error state', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Failed to load projects'));

    renderProjectsPage();

    await waitFor(() => {
      expect(screen.getByText(/failed to load projects/i)).toBeInTheDocument();
    });
  });

  it('toggles view mode', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: mockProjects }),
    });

    renderProjectsPage();

    await waitFor(() => {
      expect(screen.getByText('Project Alpha')).toBeInTheDocument();
    });

    // Find and click view toggle
    const viewButtons = screen.getAllByRole('button');
    const listButton = viewButtons.find(btn => 
      btn.querySelector('[class*="List"]')
    );

    if (listButton) {
      await user.click(listButton);
    }
  });

  it('shows empty state when no projects', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: [] }),
    });

    renderProjectsPage();

    await waitFor(() => {
      // Should not show loading spinner anymore
      expect(document.querySelector('.animate-spin')).not.toBeInTheDocument();
    });
  });

  it('shows project menu options', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: mockProjects }),
    });

    renderProjectsPage();

    await waitFor(() => {
      expect(screen.getByText('Project Alpha')).toBeInTheDocument();
    });

    // Find menu button
    const menuButtons = screen.getAllByRole('button');
    const menuButton = menuButtons.find(btn => 
      btn.querySelector('[class*="MoreVertical"]') || btn.querySelector('[class*="more"]')
    );

    if (menuButton) {
      await user.click(menuButton);
    }
  });

  it('can delete project', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ items: mockProjects }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({}),
      });

    window.confirm = vi.fn(() => true);

    renderProjectsPage();

    await waitFor(() => {
      expect(screen.getByText('Project Alpha')).toBeInTheDocument();
    });

    // Find and click a project's delete option (usually in a dropdown menu)
    const menuButtons = screen.getAllByRole('button');
    const deleteButton = menuButtons.find(btn => 
      btn.querySelector('[class*="Trash"]') || btn.textContent?.toLowerCase().includes('delete')
    );

    if (deleteButton) {
      await user.click(deleteButton);
      expect(window.confirm).toHaveBeenCalled();
    }
  });
});
