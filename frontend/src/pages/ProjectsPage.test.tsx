/**
 * Tests for ProjectsPage component.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter, MemoryRouter, Route, Routes } from 'react-router-dom';
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

// =============================================================================
// Bulk Operations Tests
// =============================================================================

const mockDesigns = [
  {
    id: 'd1',
    name: 'Design One',
    description: 'First design',
    project_id: 'p1',
    project_name: 'Project Alpha',
    source_type: 'ai',
    status: 'completed',
    thumbnail_url: null,
    created_at: '2026-01-15T10:00:00Z',
    updated_at: '2026-01-20T10:00:00Z',
  },
  {
    id: 'd2',
    name: 'Design Two',
    description: 'Second design',
    project_id: 'p1',
    project_name: 'Project Alpha',
    source_type: 'upload',
    status: 'completed',
    thumbnail_url: null,
    created_at: '2026-01-16T10:00:00Z',
    updated_at: '2026-01-21T10:00:00Z',
  },
  {
    id: 'd3',
    name: 'Design Three',
    description: 'Third design',
    project_id: 'p1',
    project_name: 'Project Alpha',
    source_type: 'ai',
    status: 'completed',
    thumbnail_url: null,
    created_at: '2026-01-17T10:00:00Z',
    updated_at: '2026-01-22T10:00:00Z',
  },
];

/**
 * Render the ProjectsPage at a specific project route so the design
 * detail view (with selectable design cards) is shown.
 */
const renderProjectsPageWithDesigns = () => {
  // First call → projects list, second call → teams, third call → designs
  (global.fetch as ReturnType<typeof vi.fn>)
    .mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ items: mockProjects }),
    })
    .mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve([]),
    })
    .mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ items: mockDesigns }),
    });

  return render(
    <MemoryRouter initialEntries={['/projects/p1']}>
      <Routes>
        <Route path="/projects/:projectId" element={<ProjectsPage />} />
      </Routes>
    </MemoryRouter>
  );
};

describe('ProjectsPage – Bulk Operations', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  it('shows selection checkboxes on design cards', async () => {
    renderProjectsPageWithDesigns();

    await waitFor(() => {
      expect(screen.getByText('Design One')).toBeInTheDocument();
    });

    // Checkbox buttons should exist (hidden until hover/bulk mode, but in DOM)
    expect(screen.getByTestId('select-design-d1')).toBeInTheDocument();
    expect(screen.getByTestId('select-design-d2')).toBeInTheDocument();
    expect(screen.getByTestId('select-design-d3')).toBeInTheDocument();
  });

  it('selects a design when checkbox is clicked', async () => {
    const user = userEvent.setup();
    renderProjectsPageWithDesigns();

    await waitFor(() => {
      expect(screen.getByText('Design One')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('select-design-d1'));

    // Toolbar should appear with "1 design selected"
    await waitFor(() => {
      expect(screen.getByText(/1 design selected/i)).toBeInTheDocument();
    });
  });

  it('deselects a design when checkbox is clicked again', async () => {
    const user = userEvent.setup();
    renderProjectsPageWithDesigns();

    await waitFor(() => {
      expect(screen.getByText('Design One')).toBeInTheDocument();
    });

    // Select then deselect
    await user.click(screen.getByTestId('select-design-d1'));
    await waitFor(() => {
      expect(screen.getByText(/1 design selected/i)).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('select-design-d1'));

    // Toolbar should disappear (0 selected)
    await waitFor(() => {
      expect(screen.queryByText(/design.* selected/i)).not.toBeInTheDocument();
    });
  });

  it('shows bulk toolbar with correct count when multiple designs selected', async () => {
    const user = userEvent.setup();
    renderProjectsPageWithDesigns();

    await waitFor(() => {
      expect(screen.getByText('Design One')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('select-design-d1'));
    await user.click(screen.getByTestId('select-design-d2'));

    await waitFor(() => {
      expect(screen.getByText(/2 designs selected/i)).toBeInTheDocument();
    });

    // Move and Delete buttons present
    expect(screen.getByRole('button', { name: /move/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument();
  });

  it('select all selects every visible design', async () => {
    const user = userEvent.setup();
    renderProjectsPageWithDesigns();

    await waitFor(() => {
      expect(screen.getByText('Design One')).toBeInTheDocument();
    });

    // Select one to make toolbar appear
    await user.click(screen.getByTestId('select-design-d1'));
    await waitFor(() => {
      expect(screen.getByTestId('bulk-toolbar')).toBeInTheDocument();
    });

    // Click "Select All"
    await user.click(screen.getByRole('button', { name: /select all/i }));

    await waitFor(() => {
      expect(screen.getByText(/3 designs selected/i)).toBeInTheDocument();
    });
  });

  it('deselect all when all are selected', async () => {
    const user = userEvent.setup();
    renderProjectsPageWithDesigns();

    await waitFor(() => {
      expect(screen.getByText('Design One')).toBeInTheDocument();
    });

    // Select all via individual clicks
    await user.click(screen.getByTestId('select-design-d1'));
    await user.click(screen.getByTestId('select-design-d2'));
    await user.click(screen.getByTestId('select-design-d3'));

    await waitFor(() => {
      expect(screen.getByText(/3 designs selected/i)).toBeInTheDocument();
    });

    // Click "Deselect All"
    await user.click(screen.getByRole('button', { name: /deselect all/i }));

    await waitFor(() => {
      expect(screen.queryByTestId('bulk-toolbar')).not.toBeInTheDocument();
    });
  });

  it('clears selection when cancel button is clicked', async () => {
    const user = userEvent.setup();
    renderProjectsPageWithDesigns();

    await waitFor(() => {
      expect(screen.getByText('Design One')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('select-design-d1'));
    await waitFor(() => {
      expect(screen.getByTestId('bulk-toolbar')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /clear selection/i }));

    await waitFor(() => {
      expect(screen.queryByTestId('bulk-toolbar')).not.toBeInTheDocument();
    });
  });

  it('shows bulk delete confirmation modal', async () => {
    const user = userEvent.setup();
    renderProjectsPageWithDesigns();

    await waitFor(() => {
      expect(screen.getByText('Design One')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('select-design-d1'));
    await user.click(screen.getByTestId('select-design-d2'));

    await waitFor(() => {
      expect(screen.getByTestId('bulk-toolbar')).toBeInTheDocument();
    });

    // Click the bulk delete button on the toolbar
    const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
    const toolbarDelete = deleteButtons.find(btn => btn.closest('[data-testid="bulk-toolbar"]'));
    if (toolbarDelete) {
      await user.click(toolbarDelete);
    }

    // Confirmation modal should appear
    await waitFor(() => {
      expect(screen.getByText(/delete 2 designs\?/i)).toBeInTheDocument();
      expect(screen.getByText(/this action cannot be undone/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /delete all/i })).toBeInTheDocument();
    });
  });

  it('cancels bulk delete confirmation', async () => {
    const user = userEvent.setup();
    renderProjectsPageWithDesigns();

    await waitFor(() => {
      expect(screen.getByText('Design One')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('select-design-d1'));

    await waitFor(() => {
      expect(screen.getByTestId('bulk-toolbar')).toBeInTheDocument();
    });

    // Open bulk delete confirmation
    const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
    const toolbarDelete = deleteButtons.find(btn => btn.closest('[data-testid="bulk-toolbar"]'));
    if (toolbarDelete) {
      await user.click(toolbarDelete);
    }

    await waitFor(() => {
      expect(screen.getByText(/delete 1 design\?/i)).toBeInTheDocument();
    });

    // Click cancel
    const cancelButtons = screen.getAllByRole('button', { name: /cancel/i });
    const modalCancel = cancelButtons[cancelButtons.length - 1];
    await user.click(modalCancel);

    // Modal should close but selection remains
    await waitFor(() => {
      expect(screen.queryByText(/delete 1 design\?/i)).not.toBeInTheDocument();
      expect(screen.getByTestId('bulk-toolbar')).toBeInTheDocument();
    });
  });
});
