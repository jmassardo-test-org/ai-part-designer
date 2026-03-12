/**
 * TrashTab Tests.
 *
 * Unit tests for the TrashTab component.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { adminApi } from '@/lib/api/admin';

// Mock the admin API
vi.mock('@/lib/api/admin', () => ({
  adminApi: {
    trash: {
      getStats: vi.fn(),
      updateRetentionPolicy: vi.fn(),
      permanentDelete: vi.fn(),
      restore: vi.fn(),
      cleanup: vi.fn(),
      getReclamationPotential: vi.fn(),
    },
  },
}));

const mockAdminApi = vi.mocked(adminApi, true);

// Import after mocks
import { TrashTab } from './TrashTab';

describe('TrashTab', () => {
  const mockStatsResponse = {
    total_deleted: 120,
    deleted_designs: 50,
    deleted_projects: 30,
    deleted_assemblies: 25,
    deleted_files: 15,
    oldest_deleted_at: '2024-01-01T00:00:00Z',
  };

  const mockReclamationResponse = {
    reclaimable_files: 45,
    reclaimable_bytes: 104857600,
    reclaimable_human: '100 MB',
    by_type: { design: 20, project: 15, file: 10 },
  };

  const mockCleanupResponse = {
    message: 'Cleanup completed successfully',
    total_cleaned: 12,
    retention_days: 30,
    cleaned: { designs: 5, projects: 4, files: 3 },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockAdminApi.trash.getStats.mockResolvedValue(mockStatsResponse);
    mockAdminApi.trash.getReclamationPotential.mockResolvedValue(mockReclamationResponse);
    mockAdminApi.trash.cleanup.mockResolvedValue(mockCleanupResponse);
  });

  it('renders the trash heading', async () => {
    render(<TrashTab />);

    expect(screen.getByText('Trash & Data Retention')).toBeInTheDocument();
  });

  it('fetches and displays trash stats on mount', async () => {
    render(<TrashTab />);

    await waitFor(() => {
      expect(mockAdminApi.trash.getStats).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText('120')).toBeInTheDocument(); // Total Deleted
      expect(screen.getByText('50')).toBeInTheDocument(); // Designs
      expect(screen.getByText('30')).toBeInTheDocument(); // Projects
    });
  });

  it('opens retention policy modal', async () => {
    render(<TrashTab />);

    await waitFor(() => {
      expect(screen.getByText('120')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Retention Policy'));

    await waitFor(() => {
      expect(screen.getByText('Retention Period (days)')).toBeInTheDocument();
    });
  });

  it('updates retention policy', async () => {
    mockAdminApi.trash.updateRetentionPolicy.mockResolvedValue({ message: 'Updated' });

    render(<TrashTab />);

    await waitFor(() => {
      expect(screen.getByText('120')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Retention Policy'));

    await waitFor(() => {
      expect(screen.getByText('Retention Period (days)')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Update'));

    await waitFor(() => {
      expect(mockAdminApi.trash.updateRetentionPolicy).toHaveBeenCalledWith({ retention_days: 30 });
    });
  });

  it('fetches and displays reclamation potential', async () => {
    render(<TrashTab />);

    await waitFor(() => {
      expect(screen.getByText('120')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Reclamation'));

    await waitFor(() => {
      expect(mockAdminApi.trash.getReclamationPotential).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText('Reclamation Potential')).toBeInTheDocument();
      expect(screen.getByText('100 MB')).toBeInTheDocument();
    });
  });

  it('runs cleanup and displays result', async () => {
    render(<TrashTab />);

    await waitFor(() => {
      expect(screen.getByText('120')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Run Cleanup'));

    await waitFor(() => {
      expect(mockAdminApi.trash.cleanup).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText('Cleanup Complete')).toBeInTheDocument();
      expect(screen.getByText('Cleanup completed successfully')).toBeInTheDocument();
    });
  });

  it('shows restore confirmation dialog', async () => {
    render(<TrashTab />);

    await waitFor(() => {
      expect(screen.getByText('120')).toBeInTheDocument();
    });

    // Enter a resource ID
    const idInput = screen.getByPlaceholderText('UUID');
    fireEvent.change(idInput, { target: { value: 'test-resource-id' } });

    // Click restore
    fireEvent.click(screen.getByText('Restore'));

    await waitFor(() => {
      expect(screen.getByText('Restore Item')).toBeInTheDocument();
    });
  });

  it('performs restore action', async () => {
    mockAdminApi.trash.restore.mockResolvedValue({ message: 'Restored' });

    render(<TrashTab />);

    await waitFor(() => {
      expect(screen.getByText('120')).toBeInTheDocument();
    });

    const idInput = screen.getByPlaceholderText('UUID');
    fireEvent.change(idInput, { target: { value: 'test-id' } });

    // Click Restore button in the actions area
    const restoreButtons = screen.getAllByText('Restore');
    fireEvent.click(restoreButtons[0]);

    // Confirm in modal
    await waitFor(() => {
      expect(screen.getByText('Restore Item')).toBeInTheDocument();
    });

    // Find the confirm button inside the modal
    const confirmButton = screen.getAllByText('Restore');
    fireEvent.click(confirmButton[confirmButton.length - 1]);

    await waitFor(() => {
      expect(mockAdminApi.trash.restore).toHaveBeenCalledWith('design', 'test-id');
    });
  });

  it('shows permanent delete confirmation requiring typed confirmation', async () => {
    render(<TrashTab />);

    await waitFor(() => {
      expect(screen.getByText('120')).toBeInTheDocument();
    });

    const idInput = screen.getByPlaceholderText('UUID');
    fireEvent.change(idInput, { target: { value: 'del-id' } });

    fireEvent.click(screen.getByText('Delete Permanently'));

    await waitFor(() => {
      expect(screen.getByText('Permanent Delete')).toBeInTheDocument();
      expect(screen.getByText(/cannot be undone/i)).toBeInTheDocument();
    });

    // Button should be disabled until typing DELETE
    const deleteButton = screen.getByText('Permanently Delete');
    expect(deleteButton).toBeDisabled();
  });

  it('handles cleanup error gracefully', async () => {
    mockAdminApi.trash.cleanup.mockRejectedValue(new Error('Server error'));

    render(<TrashTab />);

    await waitFor(() => {
      expect(screen.getByText('120')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Run Cleanup'));

    await waitFor(() => {
      expect(screen.getByText('Cleanup failed')).toBeInTheDocument();
    });
  });
});
