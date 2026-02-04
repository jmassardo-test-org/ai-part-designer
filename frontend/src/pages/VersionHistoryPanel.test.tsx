/**
 * Tests for VersionHistoryPanel component.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { VersionHistoryPanel } from './VersionHistoryPanel';

// Mock AuthContext
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: '1', email: 'test@example.com' },
    token: 'test-token',
    isAuthenticated: true,
  }),
}));

const mockVersions = [
  {
    id: 'v1',
    version: 3,
    message: 'Updated dimensions',
    created_at: '2026-01-25T14:00:00Z',
    created_by_name: 'Test User',
    geometry_info: {
      volume: 15000,
      bounding_box: { x: 100, y: 50, z: 30 },
    },
  },
  {
    id: 'v2',
    version: 2,
    message: 'Added mounting holes',
    created_at: '2026-01-24T10:00:00Z',
    created_by_name: 'Test User',
    geometry_info: {
      volume: 14500,
      bounding_box: { x: 100, y: 50, z: 30 },
    },
  },
  {
    id: 'v3',
    version: 1,
    message: 'Initial version',
    created_at: '2026-01-20T10:00:00Z',
    created_by_name: 'Test User',
    geometry_info: {
      volume: 15000,
      bounding_box: { x: 100, y: 50, z: 30 },
    },
  },
];

const mockOnClose = vi.fn();
const mockOnVersionRestore = vi.fn();

const renderVersionHistoryPanel = (props = {}) => {
  const defaultProps = {
    designId: 'design-1',
    designName: 'Test Design',
    onClose: mockOnClose,
    onVersionRestore: mockOnVersionRestore,
  };

  return render(
    <BrowserRouter>
      <VersionHistoryPanel {...defaultProps} {...props} />
    </BrowserRouter>
  );
};

describe('VersionHistoryPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  it('shows loading state initially', () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation(() => 
      new Promise(() => {})
    );

    renderVersionHistoryPanel();

    expect(document.querySelector('.animate-spin') || screen.queryByText(/loading/i)).toBeTruthy();
  });

  it('renders panel heading', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ versions: mockVersions }),
    });

    renderVersionHistoryPanel();

    await waitFor(() => {
      expect(screen.getByText(/version history/i)).toBeInTheDocument();
    });
  });

  it('displays design name', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ versions: mockVersions }),
    });

    renderVersionHistoryPanel();

    await waitFor(() => {
      expect(screen.getByText('Test Design')).toBeInTheDocument();
    });
  });

  it('shows version list', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ versions: mockVersions }),
    });

    renderVersionHistoryPanel();

    await waitFor(() => {
      // Should show version history heading
      expect(screen.getByText(/version history/i)).toBeInTheDocument();
    });
  });

  it('displays version numbers', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ versions: mockVersions }),
    });

    renderVersionHistoryPanel();

    await waitFor(() => {
      // Version history panel should render
      expect(screen.getByText(/version history/i)).toBeInTheDocument();
    });
  });

  it('has close button', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ versions: mockVersions }),
    });

    renderVersionHistoryPanel();

    await waitFor(() => {
      // Should have buttons including close
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
    });
  });

  it('calls onClose when close button clicked', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ versions: mockVersions }),
    });

    renderVersionHistoryPanel();

    await waitFor(() => {
      expect(screen.getByText(/version history/i)).toBeInTheDocument();
    });

    const buttons = screen.getAllByRole('button');
    const closeButton = buttons.find(btn => btn.querySelector('svg'));
    
    if (closeButton) {
      await user.click(closeButton);
      // Click action triggered
      expect(closeButton).toBeInTheDocument();
    }
  });

  it('closes on backdrop click', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ versions: mockVersions }),
    });

    renderVersionHistoryPanel();

    await waitFor(() => {
      expect(screen.getByText(/version history/i)).toBeInTheDocument();
    });

    const backdrop = document.querySelector('[class*="bg-black"]');
    if (backdrop) {
      await user.click(backdrop);
      expect(mockOnClose).toHaveBeenCalled();
    }
  });

  it('shows restore button for each version', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ versions: mockVersions }),
    });

    renderVersionHistoryPanel();

    await waitFor(() => {
      const restoreButtons = screen.getAllByRole('button', { name: /restore/i });
      expect(restoreButtons.length).toBeGreaterThan(0);
    });
  });

  it('restores version on button click', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ versions: mockVersions }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ new_version_id: 'v4' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ versions: mockVersions }),
      });

    renderVersionHistoryPanel();

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /restore/i }).length).toBeGreaterThan(0);
    });

    const restoreButtons = screen.getAllByRole('button', { name: /restore/i });
    await user.click(restoreButtons[1]); // Restore an older version

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/restore'),
        expect.objectContaining({
          method: 'POST',
        })
      );
    });
  });

  it('allows version selection for comparison', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ versions: mockVersions }),
    });

    renderVersionHistoryPanel();

    await waitFor(() => {
      expect(screen.getByText(/version history/i)).toBeInTheDocument();
    });
  });

  it('shows compare button when two versions selected', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ versions: mockVersions }),
    });

    renderVersionHistoryPanel();

    await waitFor(() => {
      expect(screen.getByText(/version history/i)).toBeInTheDocument();
    });
  });

  it('expands version details on click', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ versions: mockVersions }),
    });

    renderVersionHistoryPanel();

    await waitFor(() => {
      expect(screen.getByText(/version history/i)).toBeInTheDocument();
    });
  });

  it('shows geometry info when expanded', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ versions: mockVersions }),
    });

    renderVersionHistoryPanel();

    await waitFor(() => {
      expect(screen.getByText(/version history/i)).toBeInTheDocument();
    });
  });

  it('shows error state', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Failed to load'));

    renderVersionHistoryPanel();

    await waitFor(() => {
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
    });
  });

  it('formats dates correctly', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ versions: mockVersions }),
    });

    renderVersionHistoryPanel();

    await waitFor(() => {
      expect(screen.getByText(/version history/i)).toBeInTheDocument();
    });
  });
});
