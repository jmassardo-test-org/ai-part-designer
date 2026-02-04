import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor, act } from '@testing-library/react';
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useTrash } from './useTrash';

// Mock the trash API
vi.mock('@/lib/api/trash', () => ({
  default: {
    listTrash: vi.fn(),
    getStats: vi.fn(),
    getSettings: vi.fn(),
    restoreItem: vi.fn(),
    permanentlyDelete: vi.fn(),
    emptyTrash: vi.fn(),
    updateSettings: vi.fn(),
  },
}));

// Mock the toast hook
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

import trashApi, { type TrashedItem } from '@/lib/api/trash';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

const mockTrashedItem: TrashedItem = {
  id: 'item-123',
  name: 'Test Item',
  item_type: 'design',
  deleted_at: '2025-01-20T10:00:00Z',
  deleted_by: 'user-123',
  original_location: '/projects/project-1',
  size_bytes: 1024,
  expires_at: '2025-02-19T10:00:00Z',
  days_until_deletion: 30,
};

describe('useTrash', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    (trashApi.listTrash as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [mockTrashedItem],
      total: 1,
      page: 1,
      page_size: 20,
      retention_days: 30,
    });

    (trashApi.getStats as ReturnType<typeof vi.fn>).mockResolvedValue({
      total_items: 5,
      total_size_bytes: 5120,
      oldest_item_date: '2025-01-15T10:00:00Z',
      items_expiring_soon: 2,
    });

    (trashApi.getSettings as ReturnType<typeof vi.fn>).mockResolvedValue({
      retention_days: 30,
      auto_empty: false,
      next_cleanup: null,
    });
  });

  it('fetches trashed items on mount', async () => {
    const { result } = renderHook(() => useTrash(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(trashApi.listTrash).toHaveBeenCalledWith(1, 20, undefined);
    expect(result.current.items).toHaveLength(1);
    expect(result.current.items[0].id).toBe('item-123');
  });

  it('fetches with custom pagination options', async () => {
    const { result } = renderHook(
      () => useTrash({ page: 2, pageSize: 10, itemType: 'project' }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(trashApi.listTrash).toHaveBeenCalledWith(2, 10, 'project');
  });

  it('fetches stats and settings', async () => {
    const { result } = renderHook(() => useTrash(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.stats).toBeDefined();
    });

    expect(result.current.stats?.total_items).toBe(5);
    expect(result.current.settings?.retention_days).toBe(30);
  });

  it('restores an item', async () => {
    (trashApi.restoreItem as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 'item-123',
      name: 'Test Item',
      restored_at: '2025-01-25T10:00:00Z',
      message: 'Item restored successfully',
    });

    const { result } = renderHook(() => useTrash(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    act(() => {
      result.current.restoreItem(mockTrashedItem);
    });

    await waitFor(() => {
      expect(trashApi.restoreItem).toHaveBeenCalledWith('item-123', 'design');
    });
  });

  it('permanently deletes an item', async () => {
    (trashApi.permanentlyDelete as ReturnType<typeof vi.fn>).mockResolvedValue(undefined);

    const { result } = renderHook(() => useTrash(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    act(() => {
      result.current.deleteItem(mockTrashedItem);
    });

    await waitFor(() => {
      expect(trashApi.permanentlyDelete).toHaveBeenCalledWith('item-123', 'design');
    });
  });

  it('empties trash', async () => {
    (trashApi.emptyTrash as ReturnType<typeof vi.fn>).mockResolvedValue({
      deleted_count: 5,
    });

    const { result } = renderHook(() => useTrash(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    act(() => {
      result.current.emptyTrash();
    });

    await waitFor(() => {
      expect(trashApi.emptyTrash).toHaveBeenCalled();
    });
  });

  it('updates settings', async () => {
    (trashApi.updateSettings as ReturnType<typeof vi.fn>).mockResolvedValue({
      retention_days: 60,
      auto_empty: true,
      next_cleanup: '2025-02-01T00:00:00Z',
    });

    const { result } = renderHook(() => useTrash(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    act(() => {
      result.current.updateSettings({ retention_days: 60, auto_empty: true });
    });

    await waitFor(() => {
      expect(trashApi.updateSettings).toHaveBeenCalledWith({
        retention_days: 60,
        auto_empty: true,
      });
    });
  });

  it('returns default values when data is not loaded', () => {
    (trashApi.listTrash as ReturnType<typeof vi.fn>).mockReturnValue(
      new Promise(() => {}) // Never resolves
    );

    const { result } = renderHook(() => useTrash(), {
      wrapper: createWrapper(),
    });

    expect(result.current.items).toEqual([]);
    expect(result.current.total).toBe(0);
    expect(result.current.retentionDays).toBe(30);
  });

  it('exposes loading states for mutations', async () => {
    (trashApi.restoreItem as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 100))
    );

    const { result } = renderHook(() => useTrash(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isRestoring).toBe(false);
    expect(result.current.isDeleting).toBe(false);
    expect(result.current.isEmptying).toBe(false);
    expect(result.current.isUpdatingSettings).toBe(false);
  });

  it('handles restore error', async () => {
    const error = new Error('Restore failed');
    (trashApi.restoreItem as ReturnType<typeof vi.fn>).mockRejectedValue(error);

    const { result } = renderHook(() => useTrash(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    act(() => {
      result.current.restoreItem(mockTrashedItem);
    });

    // Error is handled internally with toast
    await waitFor(() => {
      expect(trashApi.restoreItem).toHaveBeenCalled();
    });
  });
});
