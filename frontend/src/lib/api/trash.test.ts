import { describe, it, expect, vi, beforeEach } from 'vitest';
import api from '@/lib/api';
import { trashApi } from './trash';

// Mock the main API client
vi.mock('@/lib/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('trashApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('listTrash', () => {
    it('fetches trashed items with default params', async () => {
      const mockData = {
        items: [{ id: '1', name: 'Item 1' }],
        total: 1,
        page: 1,
        page_size: 20,
        retention_days: 30,
      };
      (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockData });

      const result = await trashApi.listTrash();

      expect(api.get).toHaveBeenCalledWith('/trash', {
        params: { page: 1, page_size: 20 },
      });
      expect(result).toEqual(mockData);
    });

    it('fetches trashed items with custom params', async () => {
      const mockData = { items: [], total: 0 };
      (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockData });

      await trashApi.listTrash(2, 10, 'project');

      expect(api.get).toHaveBeenCalledWith('/trash', {
        params: { page: 2, page_size: 10, item_type: 'project' },
      });
    });

    it('excludes item_type when not provided', async () => {
      (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: { items: [] } });

      await trashApi.listTrash(1, 20, undefined);

      expect(api.get).toHaveBeenCalledWith('/trash', {
        params: { page: 1, page_size: 20 },
      });
    });
  });

  describe('restoreItem', () => {
    it('restores a design item', async () => {
      const mockData = {
        id: 'item-123',
        name: 'Restored Item',
        restored_at: '2025-01-25T10:00:00Z',
        message: 'Item restored successfully',
      };
      (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockData });

      const result = await trashApi.restoreItem('item-123', 'design');

      expect(api.post).toHaveBeenCalledWith('/trash/designs/item-123/restore');
      expect(result).toEqual(mockData);
    });

    it('restores a project item', async () => {
      (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: {} });

      await trashApi.restoreItem('proj-123', 'project');

      expect(api.post).toHaveBeenCalledWith('/trash/projects/proj-123/restore');
    });

    it('restores a file item', async () => {
      (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: {} });

      await trashApi.restoreItem('file-123', 'file');

      expect(api.post).toHaveBeenCalledWith('/trash/files/file-123/restore');
    });
  });

  describe('permanentlyDelete', () => {
    it('permanently deletes an item', async () => {
      (api.delete as ReturnType<typeof vi.fn>).mockResolvedValueOnce({});

      await trashApi.permanentlyDelete('item-123', 'design');

      expect(api.delete).toHaveBeenCalledWith('/trash/designs/item-123');
    });

    it('handles different item types', async () => {
      (api.delete as ReturnType<typeof vi.fn>).mockResolvedValue({});

      await trashApi.permanentlyDelete('proj-123', 'project');
      expect(api.delete).toHaveBeenCalledWith('/trash/projects/proj-123');

      await trashApi.permanentlyDelete('file-123', 'file');
      expect(api.delete).toHaveBeenCalledWith('/trash/files/file-123');
    });
  });

  describe('emptyTrash', () => {
    it('empties all trash', async () => {
      const mockData = { deleted_count: 15 };
      (api.delete as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockData });

      const result = await trashApi.emptyTrash();

      expect(api.delete).toHaveBeenCalledWith('/trash/empty');
      expect(result).toEqual(mockData);
    });
  });

  describe('getStats', () => {
    it('fetches trash statistics', async () => {
      const mockData = {
        total_items: 10,
        total_size_bytes: 102400,
        oldest_item_date: '2025-01-01T00:00:00Z',
        items_expiring_soon: 3,
      };
      (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockData });

      const result = await trashApi.getStats();

      expect(api.get).toHaveBeenCalledWith('/trash/stats');
      expect(result).toEqual(mockData);
    });
  });

  describe('getSettings', () => {
    it('fetches trash settings', async () => {
      const mockData = {
        retention_days: 30,
        auto_empty: false,
        next_cleanup: null,
      };
      (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockData });

      const result = await trashApi.getSettings();

      expect(api.get).toHaveBeenCalledWith('/trash/settings');
      expect(result).toEqual(mockData);
    });
  });

  describe('updateSettings', () => {
    it('updates trash settings', async () => {
      const mockData = {
        retention_days: 60,
        auto_empty: true,
        next_cleanup: '2025-02-01T00:00:00Z',
      };
      (api.put as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockData });

      const result = await trashApi.updateSettings({
        retention_days: 60,
        auto_empty: true,
      });

      expect(api.put).toHaveBeenCalledWith('/trash/settings', {
        retention_days: 60,
        auto_empty: true,
      });
      expect(result).toEqual(mockData);
    });

    it('updates partial settings', async () => {
      (api.put as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: {} });

      await trashApi.updateSettings({ retention_days: 14 });

      expect(api.put).toHaveBeenCalledWith('/trash/settings', { retention_days: 14 });
    });
  });
});
