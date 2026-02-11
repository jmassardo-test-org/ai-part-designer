import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { EnclosureGenerationOptions } from '@/components/enclosure';
// Mock the API
vi.mock('@/lib/api', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));
import {
  useGenerateEnclosure,
  useCheckJobStatus,
  useDownloadEnclosure,
} from './useEnclosure';
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

describe('useEnclosure hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useGenerateEnclosure', () => {
    it('calls API with correct parameters', async () => {
      const mockResponse = {
        data: {
          jobId: 'job-123',
          status: 'pending',
          progress: 0,
        },
      };

      (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(() => useGenerateEnclosure(), {
        wrapper: createWrapper(),
      });

      const params = {
        layoutId: 'layout-123',
        options: {
          wallThickness: 2,
          bottomThickness: 3,
          topThickness: 2,
          style: 'rounded' as const,
          cornerRadius: 5,
          lidType: 'snap' as const,
          lidClearance: 0.2,
        } as unknown as EnclosureGenerationOptions,
      };

      result.current.mutate(params);

      await waitFor(() => {
        expect(api.post).toHaveBeenCalledWith('/enclosures/generate', expect.objectContaining({
          layout_id: 'layout-123',
          wall_thickness: 2,
          bottom_thickness: 3,
          top_thickness: 2,
          style: 'rounded',
          corner_radius: 5,
        }));
      });
    });

    it('handles mutation error', async () => {
      const error = new Error('Generation failed');
      (api.post as ReturnType<typeof vi.fn>).mockRejectedValueOnce(error);

      const { result } = renderHook(() => useGenerateEnclosure(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        layoutId: 'layout-123',
        options: { wallThickness: 2 } as unknown as EnclosureGenerationOptions,
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });
    });
  });

  describe('useCheckJobStatus', () => {
    it('fetches job status', async () => {
      const mockResponse = {
        data: {
          jobId: 'job-123',
          status: 'completed',
          progress: 100,
          result: {
            id: 'enclosure-123',
            modelUrl: '/models/123.glb',
          },
        },
      };

      (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(() => useCheckJobStatus(), {
        wrapper: createWrapper(),
      });

      result.current.mutate('job-123');

      await waitFor(() => {
        expect(api.get).toHaveBeenCalledWith('/enclosures/jobs/job-123');
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
        expect(result.current.data?.status).toBe('completed');
      });
    });

    it('handles job status error', async () => {
      (api.get as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('Job not found'));

      const { result } = renderHook(() => useCheckJobStatus(), {
        wrapper: createWrapper(),
      });

      result.current.mutate('invalid-job');

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });
    });
  });

  describe('useDownloadEnclosure', () => {
    it('downloads enclosure file', async () => {
      const mockBlob = new Blob(['mock stl data'], { type: 'application/octet-stream' });
      (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockBlob });

      // Mock URL and DOM methods without breaking the render
      const createObjectURL = vi.fn(() => 'blob:mock-url');
      const revokeObjectURL = vi.fn();
      global.URL.createObjectURL = createObjectURL;
      global.URL.revokeObjectURL = revokeObjectURL;

      const { result } = renderHook(() => useDownloadEnclosure(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ enclosureId: 'enc-123', format: 'stl' });

      await waitFor(() => {
        expect(api.get).toHaveBeenCalledWith('/enclosures/enc-123/download', {
          params: { format: 'stl' },
          responseType: 'blob',
        });
      });
    });

    it('handles download error', async () => {
      (api.get as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('Download failed'));

      const { result } = renderHook(() => useDownloadEnclosure(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ enclosureId: 'enc-123', format: 'step' });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });
    });
  });
});
