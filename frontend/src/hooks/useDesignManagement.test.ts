/**
 * Tests for useDesignManagement Hook
 */

import { renderHook, act } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import * as designsApi from '@/lib/designs';
import { useDesignManagement } from './useDesignManagement';

// Mock the designs API
vi.mock('@/lib/designs', () => ({
  updateDesign: vi.fn(),
  copyDesign: vi.fn(),
  deleteDesignWithUndo: vi.fn(),
  undoDeleteDesign: vi.fn(),
}));

// Mock the toast hook
const mockToast = vi.fn();
const mockDismiss = vi.fn();

vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: mockToast,
    dismiss: mockDismiss,
  }),
}));

// Mock design
const mockDesign = {
  id: 'design-1',
  name: 'Test Design',
  description: 'A test design',
  project_id: 'project-1',
  project_name: 'Test Project',
  source_type: 'ai_generated',
  status: 'completed',
  thumbnail_url: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

describe('useDesignManagement', () => {
  const token = 'test-token';
  const onDesignChange = vi.fn();
  const onDesignDelete = vi.fn();
  // @ts-expect-error - Kept for potential future tests
  const _onDesignRestore = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockToast.mockReturnValue({ id: 'toast-1' });
  });

  describe('renameDesign', () => {
    it('calls updateDesign with new name', async () => {
      const updatedDesign = { ...mockDesign, name: 'New Name' };
      vi.mocked(designsApi.updateDesign).mockResolvedValue(updatedDesign);

      const { result } = renderHook(() =>
        useDesignManagement({
          token,
          onDesignChange,
        })
      );

      await act(async () => {
        await result.current.renameDesign('design-1', 'New Name');
      });

      expect(designsApi.updateDesign).toHaveBeenCalledWith(
        'design-1',
        { name: 'New Name' },
        token
      );
    });

    it('shows success toast on rename', async () => {
      const updatedDesign = { ...mockDesign, name: 'New Name' };
      vi.mocked(designsApi.updateDesign).mockResolvedValue(updatedDesign);

      const { result } = renderHook(() =>
        useDesignManagement({ token })
      );

      await act(async () => {
        await result.current.renameDesign('design-1', 'New Name');
      });

      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Design renamed',
        })
      );
    });

    it('calls onDesignChange callback', async () => {
      const updatedDesign = { ...mockDesign, name: 'New Name' };
      vi.mocked(designsApi.updateDesign).mockResolvedValue(updatedDesign);

      const { result } = renderHook(() =>
        useDesignManagement({
          token,
          onDesignChange,
        })
      );

      await act(async () => {
        await result.current.renameDesign('design-1', 'New Name');
      });

      expect(onDesignChange).toHaveBeenCalledWith(updatedDesign);
    });

    it('shows error toast on failure', async () => {
      vi.mocked(designsApi.updateDesign).mockRejectedValue(
        new Error('Network error')
      );

      const { result } = renderHook(() =>
        useDesignManagement({ token })
      );

      await act(async () => {
        try {
          await result.current.renameDesign('design-1', 'New Name');
        } catch {
          // Expected to throw
        }
      });

      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Error',
          variant: 'destructive',
        })
      );
    });

    it('sets isLoading during operation', async () => {
      let resolvePromise: (value: unknown) => void;
      const pendingPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });
      vi.mocked(designsApi.updateDesign).mockReturnValue(
        pendingPromise as Promise<typeof mockDesign>
      );

      const { result } = renderHook(() =>
        useDesignManagement({ token })
      );

      expect(result.current.isLoading).toBe(false);

      act(() => {
        result.current.renameDesign('design-1', 'New Name');
      });

      expect(result.current.isLoading).toBe(true);

      await act(async () => {
        resolvePromise!(mockDesign);
      });

      expect(result.current.isLoading).toBe(false);
    });
  });

  describe('copyDesignTo', () => {
    it('calls copyDesign with options', async () => {
      const copiedDesign = { ...mockDesign, id: 'copy-1', name: 'Copy' };
      vi.mocked(designsApi.copyDesign).mockResolvedValue(copiedDesign as designsApi.CopyResponse);

      const { result } = renderHook(() =>
        useDesignManagement({ token })
      );

      await act(async () => {
        await result.current.copyDesignTo('design-1', {
          name: 'Copy',
          targetProjectId: 'project-2',
          includeVersions: true,
        });
      });

      expect(designsApi.copyDesign).toHaveBeenCalledWith(
        'design-1',
        'Copy',
        {
          name: 'Copy',
          targetProjectId: 'project-2',
          includeVersions: true,
        },
        token
      );
    });

    it('shows success toast on copy', async () => {
      const copiedDesign = { ...mockDesign, id: 'copy-1', name: 'Copy' };
      vi.mocked(designsApi.copyDesign).mockResolvedValue(copiedDesign as designsApi.CopyResponse);

      const { result } = renderHook(() =>
        useDesignManagement({ token })
      );

      await act(async () => {
        await result.current.copyDesignTo('design-1', {
          name: 'Copy',
          includeVersions: false,
        });
      });

      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Design copied',
        })
      );
    });
  });

  describe('moveDesign', () => {
    it('calls updateDesign with projectId', async () => {
      const movedDesign = {
        ...mockDesign,
        project_id: 'project-2',
        project_name: 'Other Project',
      };
      vi.mocked(designsApi.updateDesign).mockResolvedValue(movedDesign);

      const { result } = renderHook(() =>
        useDesignManagement({ token })
      );

      await act(async () => {
        await result.current.moveDesign('design-1', 'project-2');
      });

      expect(designsApi.updateDesign).toHaveBeenCalledWith(
        'design-1',
        { projectId: 'project-2' },
        token
      );
    });

    it('shows success toast with new project name', async () => {
      const movedDesign = {
        ...mockDesign,
        project_id: 'project-2',
        project_name: 'Other Project',
      };
      vi.mocked(designsApi.updateDesign).mockResolvedValue(movedDesign);

      const { result } = renderHook(() =>
        useDesignManagement({ token })
      );

      await act(async () => {
        await result.current.moveDesign('design-1', 'project-2');
      });

      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Design moved',
          description: 'Moved to "Other Project"',
        })
      );
    });
  });

  describe('deleteDesignWithToast', () => {
    const deleteResult = {
      message: 'Design deleted',
      undo_token: 'undo-123',
      undo_expires_at: new Date(Date.now() + 30000).toISOString(),
    };

    it('calls deleteDesignWithUndo', async () => {
      vi.mocked(designsApi.deleteDesignWithUndo).mockResolvedValue(deleteResult);

      const { result } = renderHook(() =>
        useDesignManagement({
          token,
          onDesignDelete,
        })
      );

      await act(async () => {
        await result.current.deleteDesignWithToast(mockDesign);
      });

      expect(designsApi.deleteDesignWithUndo).toHaveBeenCalledWith(
        'design-1',
        token
      );
    });

    it('calls onDesignDelete callback', async () => {
      vi.mocked(designsApi.deleteDesignWithUndo).mockResolvedValue(deleteResult);

      const { result } = renderHook(() =>
        useDesignManagement({
          token,
          onDesignDelete,
        })
      );

      await act(async () => {
        await result.current.deleteDesignWithToast(mockDesign);
      });

      expect(onDesignDelete).toHaveBeenCalledWith('design-1');
    });

    it('shows toast with undo action', async () => {
      vi.mocked(designsApi.deleteDesignWithUndo).mockResolvedValue(deleteResult);

      const { result } = renderHook(() =>
        useDesignManagement({ token })
      );

      await act(async () => {
        await result.current.deleteDesignWithToast(mockDesign);
      });

      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Design deleted',
          description: expect.stringContaining('Test Design'),
        })
      );
    });
  });

  describe('currentOperation', () => {
    it('tracks current operation', async () => {
      let resolvePromise: (value: unknown) => void;
      const pendingPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });
      vi.mocked(designsApi.updateDesign).mockReturnValue(
        pendingPromise as Promise<typeof mockDesign>
      );

      const { result } = renderHook(() =>
        useDesignManagement({ token })
      );

      expect(result.current.currentOperation).toBeNull();

      act(() => {
        result.current.renameDesign('design-1', 'New Name');
      });

      expect(result.current.currentOperation).toBe('rename');

      await act(async () => {
        resolvePromise!(mockDesign);
      });

      expect(result.current.currentOperation).toBeNull();
    });
  });
});
