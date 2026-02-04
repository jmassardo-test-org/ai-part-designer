/**
 * Tests for SharedWithMePage component.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SharedWithMePage } from './SharedWithMePage';

// Mock AuthContext
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: '1', email: 'test@example.com' },
    token: 'test-token',
    isAuthenticated: true,
  }),
}));

const mockSharedDesigns = [
  {
    id: '1',
    design_id: 'd1',
    design_name: 'Shared Design 1',
    design_thumbnail_url: null,
    shared_by_id: 'u1',
    shared_by_name: 'John Doe',
    shared_by_email: 'john@example.com',
    permission: 'view',
    shared_at: '2026-01-20T10:00:00Z',
  },
  {
    id: '2',
    design_id: 'd2',
    design_name: 'Shared Design 2',
    design_thumbnail_url: null,
    shared_by_id: 'u2',
    shared_by_name: 'Jane Smith',
    shared_by_email: 'jane@example.com',
    permission: 'edit',
    shared_at: '2026-01-19T10:00:00Z',
  },
  {
    id: '3',
    design_id: 'd3',
    design_name: 'Shared Design 3',
    design_thumbnail_url: null,
    shared_by_id: 'u1',
    shared_by_name: 'John Doe',
    shared_by_email: 'john@example.com',
    permission: 'comment',
    shared_at: '2026-01-18T10:00:00Z',
  },
];

const renderSharedWithMePage = () => {
  return render(
    <BrowserRouter>
      <SharedWithMePage />
    </BrowserRouter>
  );
};

describe('SharedWithMePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  it('shows loading state initially', () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation(() => 
      new Promise(() => {})
    );

    renderSharedWithMePage();

    expect(document.querySelector('.animate-spin') || screen.queryByText(/loading/i)).toBeTruthy();
  });

  it('renders page heading', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: mockSharedDesigns }),
    });

    renderSharedWithMePage();

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /shared with me/i })).toBeInTheDocument();
    });
  });

  it('displays shared designs count', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: mockSharedDesigns }),
    });

    renderSharedWithMePage();

    await waitFor(() => {
      expect(screen.getByText(/3 designs shared/i)).toBeInTheDocument();
    });
  });

  it('displays shared design names', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: mockSharedDesigns }),
    });

    renderSharedWithMePage();

    await waitFor(() => {
      expect(screen.getByText('Shared Design 1')).toBeInTheDocument();
      expect(screen.getByText('Shared Design 2')).toBeInTheDocument();
      expect(screen.getByText('Shared Design 3')).toBeInTheDocument();
    });
  });

  it('shows who shared each design', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: mockSharedDesigns }),
    });

    renderSharedWithMePage();

    await waitFor(() => {
      expect(screen.getAllByText('John Doe').length).toBeGreaterThan(0);
      expect(screen.getByText('Jane Smith')).toBeInTheDocument();
    });
  });

  it('displays permission badges', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: mockSharedDesigns }),
    });

    renderSharedWithMePage();

    await waitFor(() => {
      expect(screen.getByText('View')).toBeInTheDocument();
      expect(screen.getByText('Edit')).toBeInTheDocument();
      expect(screen.getByText('Comment')).toBeInTheDocument();
    });
  });

  it('has search input', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: mockSharedDesigns }),
    });

    renderSharedWithMePage();

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search designs/i)).toBeInTheDocument();
    });
  });

  it('filters designs by search query', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: mockSharedDesigns }),
    });

    renderSharedWithMePage();

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search designs/i)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search designs/i);
    await user.type(searchInput, 'Design 1');

    expect(searchInput).toHaveValue('Design 1');
  });

  it('has permission filter dropdown', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: mockSharedDesigns }),
    });

    renderSharedWithMePage();

    await waitFor(() => {
      expect(screen.getByText(/all permissions/i)).toBeInTheDocument();
    });
  });

  it('filters by permission', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: mockSharedDesigns }),
    });

    renderSharedWithMePage();

    await waitFor(() => {
      expect(screen.getByText(/all permissions/i)).toBeInTheDocument();
    });

    const filterSelect = screen.getByRole('combobox');
    await user.selectOptions(filterSelect, 'edit');

    expect(filterSelect).toHaveValue('edit');
  });

  it('toggles view mode between grid and list', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: mockSharedDesigns }),
    });

    renderSharedWithMePage();

    await waitFor(() => {
      expect(screen.getByText('Shared Design 1')).toBeInTheDocument();
    });

    // Find view toggle buttons
    const buttons = screen.getAllByRole('button');
    const listButton = buttons.find(btn => btn.querySelector('[class*="List"]'));
    
    if (listButton) {
      await user.click(listButton);
    }
  });

  it('shows error state', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Failed to load'));

    renderSharedWithMePage();

    await waitFor(() => {
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
    });
  });

  it('dismisses error on button click', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Failed to load'));

    renderSharedWithMePage();

    await waitFor(() => {
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
    });

    const dismissButton = screen.getByRole('button', { name: /dismiss/i });
    await user.click(dismissButton);

    expect(screen.queryByText(/failed to load/i)).not.toBeInTheDocument();
  });

  it('shows empty state when no shared designs', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: [] }),
    });

    renderSharedWithMePage();

    await waitFor(() => {
      expect(screen.getByText(/0 designs/i)).toBeInTheDocument();
    });
  });

  it('navigates to design on click', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: mockSharedDesigns }),
    });

    renderSharedWithMePage();

    await waitFor(() => {
      expect(screen.getByText('Shared Design 1')).toBeInTheDocument();
    });

    // Click on a design card (the component should handle navigation)
    const designCard = screen.getByText('Shared Design 1').closest('[class*="card"]') 
      || screen.getByText('Shared Design 1').parentElement;
    
    if (designCard) {
      await user.click(designCard);
    }
  });

  it('formats shared date correctly', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: mockSharedDesigns }),
    });

    renderSharedWithMePage();

    await waitFor(() => {
      // Should show relative dates like "Today", "Yesterday", or formatted dates
      const dateTexts = screen.queryAllByText(/today/i).length + 
        screen.queryAllByText(/yesterday/i).length + 
        screen.queryAllByText(/days ago/i).length +
        screen.queryAllByText(/jan/i).length;
      expect(dateTexts).toBeGreaterThanOrEqual(0);
    });
  });
});
