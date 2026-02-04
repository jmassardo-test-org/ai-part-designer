import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  useLayout,
  useProjectLayouts,
  useCreateLayout,
  useUpdateLayout,
  useDeleteLayout,
  useAddPlacement,
  useUpdatePlacement,
  useRemovePlacement,
  useValidateLayout,
  useAutoLayout,
  layoutKeys,
} from './useLayout';

// Mock the API
vi.mock('@/lib/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import api from '@/lib/api';

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

describe('useLayout hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('layoutKeys', () => {
    it('generates correct query keys', () => {
      expect(layoutKeys.all).toEqual(['layouts']);
      expect(layoutKeys.lists()).toEqual(['layouts', 'list']);
      expect(layoutKeys.list('proj-123')).toEqual(['layouts', 'list', 'proj-123']);
      expect(layoutKeys.details()).toEqual(['layouts', 'detail']);
      expect(layoutKeys.detail('lay-123')).toEqual(['layouts', 'detail', 'lay-123']);
    });
  });

  describe('useLayout', () => {
    it('fetches layout by id', async () => {
      const mockLayout = {
        id: 'lay-123',
        name: 'Test Layout',
        placements: [],
      };

      (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockLayout });

      const { result } = renderHook(() => useLayout('lay-123'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.get).toHaveBeenCalledWith('/layouts/lay-123');
      expect(result.current.data).toEqual(mockLayout);
    });

    it('does not fetch when layoutId is undefined', () => {
      renderHook(() => useLayout(undefined), {
        wrapper: createWrapper(),
      });

      expect(api.get).not.toHaveBeenCalled();
    });
  });

  describe('useProjectLayouts', () => {
    it('fetches layouts for a project', async () => {
      const mockLayouts = [
        { id: 'lay-1', name: 'Layout 1' },
        { id: 'lay-2', name: 'Layout 2' },
      ];

      (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockLayouts });

      const { result } = renderHook(() => useProjectLayouts('proj-123'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.get).toHaveBeenCalledWith('/projects/proj-123/layouts');
      expect(result.current.data).toEqual(mockLayouts);
    });

    it('does not fetch when projectId is undefined', () => {
      renderHook(() => useProjectLayouts(undefined), {
        wrapper: createWrapper(),
      });

      expect(api.get).not.toHaveBeenCalled();
    });
  });

  describe('useCreateLayout', () => {
    it('creates a new layout', async () => {
      const mockLayout = {
        id: 'lay-new',
        name: 'New Layout',
        projectId: 'proj-123',
      };

      (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockLayout });

      const { result } = renderHook(() => useCreateLayout(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        projectId: 'proj-123',
        name: 'New Layout',
        internalWidth: 100,
        internalDepth: 100,
        internalHeight: 50,
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.post).toHaveBeenCalledWith('/layouts', expect.objectContaining({
        projectId: 'proj-123',
        name: 'New Layout',
      }));
    });
  });

  describe('useUpdateLayout', () => {
    it('updates layout properties', async () => {
      const mockLayout = {
        id: 'lay-123',
        name: 'Updated Layout',
      };

      (api.patch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockLayout });

      const { result } = renderHook(() => useUpdateLayout(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        layoutId: 'lay-123',
        updates: { name: 'Updated Layout' },
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.patch).toHaveBeenCalledWith('/layouts/lay-123', { name: 'Updated Layout' });
    });
  });

  describe('useDeleteLayout', () => {
    it('deletes a layout', async () => {
      (api.delete as ReturnType<typeof vi.fn>).mockResolvedValueOnce({});

      const { result } = renderHook(() => useDeleteLayout(), {
        wrapper: createWrapper(),
      });

      result.current.mutate('lay-123');

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.delete).toHaveBeenCalledWith('/layouts/lay-123');
    });
  });

  describe('useAddPlacement', () => {
    it('adds a placement to layout', async () => {
      const mockPlacement = {
        id: 'place-123',
        componentId: 'comp-123',
        xPosition: 10,
        yPosition: 20,
      };

      (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockPlacement });

      const { result } = renderHook(() => useAddPlacement(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        layoutId: 'lay-123',
        componentId: 'comp-123',
        xPosition: 10,
        yPosition: 20,
        width: 50,
        depth: 30,
        height: 20,
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.post).toHaveBeenCalledWith('/layouts/lay-123/placements', expect.objectContaining({
        componentId: 'comp-123',
        xPosition: 10,
        yPosition: 20,
      }));
    });
  });

  describe('useUpdatePlacement', () => {
    it('updates a placement with optimistic update', async () => {
      const mockPlacement = {
        id: 'place-123',
        xPosition: 30,
        yPosition: 40,
      };

      (api.patch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockPlacement });

      const { result } = renderHook(() => useUpdatePlacement(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        layoutId: 'lay-123',
        placementId: 'place-123',
        updates: { xPosition: 30, yPosition: 40 },
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.patch).toHaveBeenCalledWith(
        '/layouts/lay-123/placements/place-123',
        { xPosition: 30, yPosition: 40 }
      );
    });
  });

  describe('useRemovePlacement', () => {
    it('removes a placement from layout', async () => {
      (api.delete as ReturnType<typeof vi.fn>).mockResolvedValueOnce({});

      const { result } = renderHook(() => useRemovePlacement(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        layoutId: 'lay-123',
        placementId: 'place-123',
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.delete).toHaveBeenCalledWith('/layouts/lay-123/placements/place-123');
    });
  });

  describe('useValidateLayout', () => {
    it('validates layout', async () => {
      const mockValidation = {
        valid: true,
        collisions: [],
        boundaryViolations: [],
      };

      (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockValidation });

      const { result } = renderHook(() => useValidateLayout(), {
        wrapper: createWrapper(),
      });

      result.current.mutate('lay-123');

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.post).toHaveBeenCalledWith('/layouts/lay-123/validate');
      expect(result.current.data).toEqual(mockValidation);
    });

    it('returns validation errors', async () => {
      const mockValidation = {
        valid: false,
        collisions: [{ placement1: 'p1', placement2: 'p2' }],
        boundaryViolations: ['Component exceeds boundary'],
      };

      (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockValidation });

      const { result } = renderHook(() => useValidateLayout(), {
        wrapper: createWrapper(),
      });

      result.current.mutate('lay-123');

      await waitFor(() => {
        expect(result.current.data?.valid).toBe(false);
        expect(result.current.data?.collisions).toHaveLength(1);
      });
    });
  });

  describe('useAutoLayout', () => {
    it('auto-arranges components', async () => {
      const mockLayout = {
        id: 'lay-123',
        placements: [
          { id: 'p1', xPosition: 0, yPosition: 0 },
          { id: 'p2', xPosition: 50, yPosition: 0 },
        ],
      };

      (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockLayout });

      const { result } = renderHook(() => useAutoLayout(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ layoutId: 'lay-123', algorithm: 'grid' });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.post).toHaveBeenCalledWith('/layouts/lay-123/auto-layout', {
        algorithm: 'grid',
      });
    });
  });
});
