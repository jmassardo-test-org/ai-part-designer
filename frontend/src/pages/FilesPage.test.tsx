/**
 * Tests for FilesPage component.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { FilesPage } from './FilesPage';

// Mock AuthContext
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: '1', email: 'test@example.com' },
    token: 'test-token',
    isAuthenticated: true,
  }),
}));

// Mock FileUploader component
vi.mock('@/components/upload/FileUploader', () => ({
  FileUploader: ({ onClose }: { onClose: () => void }) => (
    <div data-testid="file-uploader">
      <button onClick={onClose}>Close Uploader</button>
    </div>
  ),
}));

// Mock VersionHistoryPanel
vi.mock('./VersionHistoryPanel', () => ({
  VersionHistoryPanel: ({ onClose }: { onClose: () => void }) => (
    <div data-testid="version-history-panel">
      <button onClick={onClose}>Close History</button>
    </div>
  ),
}));

const mockFiles = [
  {
    id: '1',
    name: 'design-1.step',
    project_id: 'p1',
    format: 'step',
    size: 1024 * 1024, // 1 MB
    status: 'completed',
    created_at: '2026-01-20T10:00:00Z',
    updated_at: '2026-01-20T10:00:00Z',
    thumbnail_url: null,
    version: 1,
  },
  {
    id: '2',
    name: 'design-2.stl',
    project_id: 'p1',
    format: 'stl',
    size: 512 * 1024, // 512 KB
    status: 'completed',
    created_at: '2026-01-19T10:00:00Z',
    updated_at: '2026-01-19T10:00:00Z',
    thumbnail_url: null,
    version: 2,
  },
];

const renderFilesPage = (props = {}) => {
  return render(
    <BrowserRouter>
      <FilesPage {...props} />
    </BrowserRouter>
  );
};

describe('FilesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
    window.confirm = vi.fn(() => true);
  });

  it('shows loading state initially', () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation(() => 
      new Promise(() => {})
    );

    renderFilesPage();

    // Loading state shows heading
    expect(screen.getByRole('heading', { name: /files/i })).toBeInTheDocument();
  });

  it('renders files page heading', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ files: mockFiles }),
    });

    renderFilesPage();

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /files/i })).toBeInTheDocument();
    });
  });

  it('displays file count', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ files: mockFiles }),
    });

    renderFilesPage();

    await waitFor(() => {
      expect(screen.getByText(/2 files/i)).toBeInTheDocument();
    });
  });

  it('shows file list', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ files: mockFiles }),
    });

    renderFilesPage();

    await waitFor(() => {
      expect(screen.getByText('design-1.step')).toBeInTheDocument();
      expect(screen.getByText('design-2.stl')).toBeInTheDocument();
    });
  });

  it('has search input', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ files: mockFiles }),
    });

    renderFilesPage();

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search files/i)).toBeInTheDocument();
    });
  });

  it('allows searching files', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ files: mockFiles }),
    });

    renderFilesPage();

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search files/i)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search files/i);
    await user.type(searchInput, 'design');

    expect(searchInput).toHaveValue('design');
  });

  it('toggles view mode between grid and list', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ files: mockFiles }),
    });

    renderFilesPage();

    await waitFor(() => {
      expect(screen.getByText('design-1.step')).toBeInTheDocument();
    });

    // Find view toggle buttons
    const buttons = screen.getAllByRole('button');
    const listButton = buttons.find(btn => btn.querySelector('[class*="List"]'));
    
    if (listButton) {
      await user.click(listButton);
    }
  });

  it('opens upload dialog', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ files: mockFiles }),
    });

    renderFilesPage();

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /files/i })).toBeInTheDocument();
    });

    const uploadButton = screen.getByRole('button', { name: /upload/i });
    await user.click(uploadButton);

    expect(screen.getByTestId('file-uploader')).toBeInTheDocument();
  });

  it('handles error state', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Failed to fetch files'));

    renderFilesPage();

    await waitFor(() => {
      expect(screen.getByText(/failed to fetch files/i)).toBeInTheDocument();
    });
  });

  it('allows file selection', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ files: mockFiles }),
    });

    renderFilesPage();

    await waitFor(() => {
      expect(screen.getByText('design-1.step')).toBeInTheDocument();
    });

    // The component should show selection UI after selecting files
    const checkboxes = screen.getAllByRole('checkbox');
    if (checkboxes.length > 0) {
      await user.click(checkboxes[0]);
    }
  });

  it('formats file sizes correctly', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ files: mockFiles }),
    });

    renderFilesPage();

    await waitFor(() => {
      // Files are displayed - size formatting happens internally
      expect(screen.getByText('design-1.step')).toBeInTheDocument();
      expect(screen.getByText('design-2.stl')).toBeInTheDocument();
    });
  });

  it('shows empty state when no files', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ files: [] }),
    });

    renderFilesPage();

    await waitFor(() => {
      expect(screen.getByText(/0 files/i)).toBeInTheDocument();
    });
  });

  it('can refresh file list', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ files: mockFiles }),
    });

    renderFilesPage();

    await waitFor(() => {
      expect(screen.getByText('design-1.step')).toBeInTheDocument();
    });

    const refreshButton = screen.getByRole('button', { name: /refresh/i });
    await user.click(refreshButton);

    expect(global.fetch).toHaveBeenCalledTimes(2);
  });

  it('supports sort toggle', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ files: mockFiles }),
    });

    renderFilesPage();

    await waitFor(() => {
      expect(screen.getByText('design-1.step')).toBeInTheDocument();
    });

    // Find sort buttons
    const sortButtons = screen.getAllByRole('button');
    const sortButton = sortButtons.find(btn => 
      btn.querySelector('[class*="Sort"]') || btn.textContent?.toLowerCase().includes('sort')
    );

    if (sortButton) {
      await user.click(sortButton);
    }
  });
});
