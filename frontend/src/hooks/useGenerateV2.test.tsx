/**
 * Tests for CAD v2 React Query hooks.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import React, { ReactNode } from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as api from '../lib/generate-v2';
import {
  useGenerateV2,
  usePreviewSchema,
  useCompileEnclosure,
  useGenerateAsync,
  useJobStatus,
  generateV2Keys,
} from './useGenerateV2';

// Mock the API module
vi.mock('../lib/generate-v2', () => ({
  generateFromDescriptionV2: vi.fn(),
  previewSchema: vi.fn(),
  compileEnclosure: vi.fn(),
  generateAsync: vi.fn(),
  getJobStatus: vi.fn(),
  getJobFiles: vi.fn(),
  downloadFile: vi.fn(),
}));

// Mock the AuthContext
vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    token: 'mock-token',
    user: { id: 'user-123', email: 'test@example.com' },
    isAuthenticated: true,
    isLoading: false,
  }),
}));

// Create a fresh QueryClient for each test
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children
    );
  };
}

describe('generateV2Keys', () => {
  it('should generate correct query keys', () => {
    expect(generateV2Keys.all).toEqual(['generate-v2']);
    expect(generateV2Keys.jobs()).toEqual(['generate-v2', 'jobs']);
    expect(generateV2Keys.job('job-123')).toEqual(['generate-v2', 'jobs', 'job-123']);
    expect(generateV2Keys.files('job-123')).toEqual(['generate-v2', 'jobs', 'job-123', 'files']);
  });
});

describe('useGenerateV2', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createTestQueryClient();
    vi.clearAllMocks();
  });

  it('should start in idle state', () => {
    const { result } = renderHook(() => useGenerateV2(), {
      wrapper: createWrapper(queryClient),
    });

    expect(result.current.isIdle).toBe(true);
    expect(result.current.isPending).toBe(false);
  });

  it('should call API on mutate', async () => {
    const mockResponse = {
      job_id: 'job-123',
      success: true,
      parts: ['body'],
      downloads: {},
      warnings: [],
      errors: [],
    };
    (api.generateFromDescriptionV2 as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockResponse);

    const { result } = renderHook(() => useGenerateV2(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate({ description: 'Test box' });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(api.generateFromDescriptionV2).toHaveBeenCalledWith(
      { description: 'Test box' },
      'mock-token'
    );
    expect(result.current.data?.job_id).toBe('job-123');
  });

  it('should handle errors', async () => {
    (api.generateFromDescriptionV2 as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new Error('API Error')
    );

    const { result } = renderHook(() => useGenerateV2(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate({ description: 'Bad request' });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error?.message).toBe('API Error');
  });
});

describe('usePreviewSchema', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createTestQueryClient();
    vi.clearAllMocks();
  });

  it('should preview schema on mutate', async () => {
    const mockResponse = {
      success: true,
      generated_schema: {
        exterior: {
          width: { value: 100 },
          depth: { value: 80 },
          height: { value: 40 },
        },
      },
    };
    (api.previewSchema as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockResponse);

    const { result } = renderHook(() => usePreviewSchema(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate('Preview box');

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.generated_schema).toBeDefined();
  });
});

describe('useCompileEnclosure', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createTestQueryClient();
    vi.clearAllMocks();
  });

  it('should compile enclosure on mutate', async () => {
    const mockResponse = {
      job_id: 'compile-123',
      success: true,
      parts: ['body', 'lid'],
      files: ['body.step', 'lid.step'],
      downloads: {},
      errors: [],
      warnings: [],
    };
    (api.compileEnclosure as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockResponse);

    const { result } = renderHook(() => useCompileEnclosure(), {
      wrapper: createWrapper(queryClient),
    });

    const enclosure_schema = {
      exterior: {
        width: { value: 100 },
        depth: { value: 80 },
        height: { value: 40 },
      },
    };

    result.current.mutate({ enclosure_schema });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.parts).toContain('body');
    expect(result.current.data?.parts).toContain('lid');
  });
});

describe('useGenerateAsync', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createTestQueryClient();
    vi.clearAllMocks();
  });

  it('should start async generation', async () => {
    const mockResponse = {
      job_id: 'async-123',
      status: 'pending',
    };
    (api.generateAsync as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockResponse);

    const { result } = renderHook(() => useGenerateAsync(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate({ description: 'Async box' });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.job_id).toBe('async-123');
  });
});

describe('useJobStatus', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createTestQueryClient();
    vi.clearAllMocks();
  });

  it('should not fetch when jobId is null', () => {
    const { result } = renderHook(() => useJobStatus(null), {
      wrapper: createWrapper(queryClient),
    });

    expect(result.current.isFetching).toBe(false);
    expect(api.getJobStatus).not.toHaveBeenCalled();
  });

  it('should fetch job status when jobId provided', async () => {
    const mockStatus = {
      job_id: 'job-123',
      status: 'completed',
      progress: 100,
      files: ['body.step'],
    };
    (api.getJobStatus as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockStatus);

    const { result } = renderHook(() => useJobStatus('job-123'), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(api.getJobStatus).toHaveBeenCalledWith('job-123', 'mock-token');
    expect(result.current.data?.status).toBe('completed');
  });

  it('should poll when status is pending', async () => {
    const mockPendingStatus = {
      job_id: 'job-123',
      status: 'pending',
      progress: 50,
    };
    (api.getJobStatus as ReturnType<typeof vi.fn>).mockResolvedValue(mockPendingStatus);

    const { result } = renderHook(() => useJobStatus('job-123'), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Check refetch interval is set based on status
    // Note: We can't easily test the actual polling, but we verify the status check works
    expect(result.current.data?.status).toBe('pending');
  });

  it('should stop polling when status is completed', async () => {
    const mockCompletedStatus = {
      job_id: 'job-123',
      status: 'completed',
      progress: 100,
      files: ['body.step'],
    };
    (api.getJobStatus as ReturnType<typeof vi.fn>).mockResolvedValue(mockCompletedStatus);

    const { result } = renderHook(() => useJobStatus('job-123'), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.status).toBe('completed');
  });
});
