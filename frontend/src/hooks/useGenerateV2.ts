/**
 * React Query hooks for CAD v2 generation.
 *
 * Provides useMutation hooks for generation and useQuery for job status.
 */

import { useMutation, useQuery, useQueryClient, type Query } from '@tanstack/react-query';
import { useAuth } from '@/contexts/AuthContext';
import {
  compileEnclosure,
  downloadFile,
  generateAsync,
  generateFromDescriptionV2,
  getJobStatus,
  listJobFiles,
  previewSchema,
} from '@/lib/generate-v2';
import type {
  CompileRequest,
  CompileResponse,
  EnclosureSpec,
  GenerateV2Request,
  GenerateV2Response,
  JobStatusResponse,
  SchemaPreviewResponse,
} from '@/types/cad-v2';

// =============================================================================
// Query Keys
// =============================================================================

export const generateV2Keys = {
  all: ['generate-v2'] as const,
  jobs: () => [...generateV2Keys.all, 'jobs'] as const,
  job: (jobId: string) => [...generateV2Keys.jobs(), jobId] as const,
  files: (jobId: string) => [...generateV2Keys.job(jobId), 'files'] as const,
};

// =============================================================================
// Generation Hooks
// =============================================================================

/**
 * Hook for generating CAD from natural language.
 *
 * @example
 * ```tsx
 * const { mutate, isPending, data } = useGenerateV2();
 *
 * const handleGenerate = () => {
 *   mutate({ description: 'Box for Raspberry Pi 4' });
 * };
 * ```
 */
export function useGenerateV2() {
  const { token } = useAuth();
  const queryClient = useQueryClient();

  return useMutation<GenerateV2Response, Error, GenerateV2Request>({
    mutationFn: (request) => generateFromDescriptionV2(request, token ?? undefined),
    onSuccess: (data) => {
      // Invalidate job queries to refresh status
      if (data.job_id) {
        queryClient.invalidateQueries({ queryKey: generateV2Keys.job(data.job_id) });
      }
    },
  });
}

/**
 * Hook for previewing schema without compiling.
 *
 * Useful for showing the user what will be generated.
 */
export function usePreviewSchema() {
  const { token } = useAuth();

  return useMutation<SchemaPreviewResponse, Error, string>({
    mutationFn: (description) => previewSchema({ description }, token ?? undefined),
  });
}

/**
 * Hook for compiling an enclosure spec directly.
 *
 * Use when you have a complete EnclosureSpec.
 */
export function useCompileEnclosure() {
  const { token } = useAuth();
  const queryClient = useQueryClient();

  return useMutation<CompileResponse, Error, CompileRequest>({
    mutationFn: (request) => compileEnclosure(request, token ?? undefined),
    onSuccess: (data) => {
      if (data.job_id) {
        queryClient.invalidateQueries({ queryKey: generateV2Keys.job(data.job_id) });
      }
    },
  });
}

/**
 * Hook for async generation with background processing.
 *
 * Returns immediately, use useJobStatus to poll for completion.
 */
export function useGenerateAsync() {
  const { token } = useAuth();

  return useMutation<GenerateV2Response, Error, GenerateV2Request>({
    mutationFn: (request) => generateAsync(request, token ?? undefined),
  });
}

// =============================================================================
// Job Status Hooks
// =============================================================================

/**
 * Hook for polling job status.
 *
 * Automatically refetches while job is pending/running.
 *
 * @example
 * ```tsx
 * const { data: status } = useJobStatus(jobId, {
 *   enabled: !!jobId,
 *   refetchInterval: (data) =>
 *     data?.status === 'completed' || data?.status === 'failed' ? false : 1000,
 * });
 * ```
 */
export function useJobStatus(
  jobId: string | null,
  options?: {
    enabled?: boolean;
    refetchInterval?: number | false | ((query: Query<JobStatusResponse, Error>) => number | false);
  }
) {
  const { token } = useAuth();

  return useQuery<JobStatusResponse, Error>({
    queryKey: generateV2Keys.job(jobId ?? ''),
    queryFn: () => getJobStatus(jobId!, token ?? undefined),
    enabled: options?.enabled !== false && !!jobId,
    refetchInterval: options?.refetchInterval ?? ((query: Query<JobStatusResponse, Error>) => {
      // Auto-poll while job is in progress
      const data = query.state.data;
      if (!data) return 2000;
      if (data.status === 'pending' || data.status === 'running') return 1000;
      return false; // Stop polling when complete or failed
    }),
  });
}

/**
 * Hook for listing files from a completed job.
 */
export function useJobFiles(jobId: string | null) {
  const { token } = useAuth();

  return useQuery<string[], Error>({
    queryKey: generateV2Keys.files(jobId ?? ''),
    queryFn: () => listJobFiles(jobId!, token ?? undefined),
    enabled: !!jobId,
  });
}

// =============================================================================
// Download Hooks
// =============================================================================

/**
 * Hook for downloading a file.
 *
 * Triggers browser download when called.
 */
export function useDownloadFile() {
  const { token } = useAuth();

  return useMutation<void, Error, { jobId: string; filename: string }>({
    mutationFn: async ({ jobId, filename }) => {
      const blob = await downloadFile(jobId, filename, token ?? undefined);

      // Trigger browser download
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
  });
}

// =============================================================================
// Compound Hooks
// =============================================================================

/**
 * Combined hook for the full generation flow.
 *
 * Provides generation, status polling, and download in one hook.
 *
 * @example
 * ```tsx
 * const {
 *   generate,
 *   isGenerating,
 *   result,
 *   status,
 *   download,
 *   reset,
 * } = useGenerationFlow();
 *
 * // Start generation
 * generate({ description: 'Box for Arduino Uno' });
 *
 * // When complete, download files
 * if (status === 'completed') {
 *   download('body.step');
 * }
 * ```
 */
export function useGenerationFlow() {
  const generateMutation = useGenerateV2();
  const downloadMutation = useDownloadFile();
  const queryClient = useQueryClient();

  const jobId = generateMutation.data?.job_id ?? null;
  const jobStatus = useJobStatus(jobId, {
    enabled: generateMutation.isSuccess && !!jobId,
  });

  return {
    // Generation
    generate: generateMutation.mutate,
    generateAsync: generateMutation.mutateAsync,
    isGenerating: generateMutation.isPending,
    generationError: generateMutation.error,

    // Result
    result: generateMutation.data,
    jobId,

    // Status (for async jobs)
    status: jobStatus.data?.status,
    progress: jobStatus.data?.progress,
    statusMessage: jobStatus.data?.message,
    isPolling: jobStatus.isFetching,

    // Downloads
    downloads: generateMutation.data?.downloads ?? {},
    download: (filename: string) => {
      if (jobId) {
        downloadMutation.mutate({ jobId, filename });
      }
    },
    isDownloading: downloadMutation.isPending,

    // Reset
    reset: () => {
      generateMutation.reset();
      if (jobId) {
        queryClient.removeQueries({ queryKey: generateV2Keys.job(jobId) });
      }
    },

    // Clarification handling
    clarificationNeeded: generateMutation.data?.clarification_needed,
    warnings: generateMutation.data?.warnings ?? [],
    errors: generateMutation.data?.errors ?? [],
  };
}

// =============================================================================
// Async Compile Hook
// =============================================================================

/**
 * Hook for async compilation with job status polling.
 *
 * Queues compilation as a background job and automatically polls for completion.
 *
 * @example
 * ```tsx
 * const {
 *   compile,
 *   isCompiling,
 *   jobId,
 *   status,
 *   progress,
 *   result,
 * } = useCompileEnclosureAsync();
 *
 * // Start async compilation
 * compile(enclosureSpec);
 *
 * // status will automatically update as job progresses
 * ```
 */
export function useCompileEnclosureAsync() {
  const { token } = useAuth();
  const queryClient = useQueryClient();

  const compileMutation = useMutation<
    import('@/lib/generate-v2').AsyncCompileResponse,
    Error,
    { schema: EnclosureSpec; exportFormat?: string }
  >({
    mutationFn: async ({ schema, exportFormat }) => {
      const { compileEnclosureAsync } = await import('@/lib/generate-v2');
      return compileEnclosureAsync(schema, exportFormat ?? 'step', token ?? undefined);
    },
  });

  const jobId = compileMutation.data?.job_id ?? null;
  const jobStatus = useJobStatus(jobId, {
    enabled: compileMutation.isSuccess && !!jobId,
  });

  return {
    // Compile action
    compile: (schema: EnclosureSpec, exportFormat?: string) =>
      compileMutation.mutate({ schema, exportFormat }),
    compileAsync: (schema: EnclosureSpec, exportFormat?: string) =>
      compileMutation.mutateAsync({ schema, exportFormat }),

    // State
    isCompiling: compileMutation.isPending || (jobStatus.data?.status === 'running'),
    isQueued: jobStatus.data?.status === 'pending',
    jobId,

    // Progress
    status: jobStatus.data?.status ?? (compileMutation.isPending ? 'starting' : undefined),
    progress: jobStatus.data?.progress ?? 0,
    progressMessage: jobStatus.data?.message,

    // Result
    result: jobStatus.data?.files,
    error: compileMutation.error?.message ?? jobStatus.data?.error,
    isComplete: jobStatus.data?.status === 'completed',
    isFailed: jobStatus.data?.status === 'failed',

    // Reset
    reset: () => {
      compileMutation.reset();
      if (jobId) {
        queryClient.removeQueries({ queryKey: generateV2Keys.job(jobId) });
      }
    },
  };
}

// =============================================================================
// Design Save Hooks
// =============================================================================

/**
 * Hook for saving a generated design to a project.
 *
 * @example
 * ```tsx
 * const { mutate: saveDesign, isPending } = useSaveDesignV2();
 *
 * saveDesign({
 *   job_id: 'job-123',
 *   name: 'My Arduino Case',
 *   project_id: 'project-456',
 * });
 * ```
 */
export function useSaveDesignV2() {
  const { token } = useAuth();
  const queryClient = useQueryClient();

  return useMutation<
    import('@/lib/generate-v2').SaveDesignV2Response,
    Error,
    import('@/lib/generate-v2').SaveDesignV2Request
  >({
    mutationFn: async (request) => {
      const { saveDesignV2 } = await import('@/lib/generate-v2');
      return saveDesignV2(request, token ?? undefined);
    },
    onSuccess: () => {
      // Invalidate designs list
      queryClient.invalidateQueries({ queryKey: ['designs-v2'] });
    },
  });
}

/**
 * Hook for fetching a single v2 design.
 */
export function useDesignV2(designId: string | null) {
  const { token } = useAuth();

  return useQuery<import('@/lib/generate-v2').SaveDesignV2Response, Error>({
    queryKey: ['designs-v2', 'detail', designId],
    queryFn: async () => {
      const { getDesignV2 } = await import('@/lib/generate-v2');
      return getDesignV2(designId!, token ?? undefined);
    },
    enabled: !!designId,
  });
}

/**
 * Hook for listing v2 designs.
 */
export function useDesignsV2(options?: {
  projectId?: string;
  page?: number;
  perPage?: number;
}) {
  const { token } = useAuth();

  return useQuery<import('@/lib/generate-v2').ListDesignsV2Response, Error>({
    queryKey: ['designs-v2', 'list', options?.projectId, options?.page],
    queryFn: async () => {
      const { listDesignsV2 } = await import('@/lib/generate-v2');
      return listDesignsV2(options, token ?? undefined);
    },
  });
}
