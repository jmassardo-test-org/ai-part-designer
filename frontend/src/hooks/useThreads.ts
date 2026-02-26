/**
 * React Query hooks for the Thread Library.
 *
 * Provides query and mutation hooks for thread families, sizes,
 * specifications, tap drill info, generation, and print optimization.
 */

import { useMutation, useQuery } from '@tanstack/react-query';
import { useAuth } from '@/contexts/AuthContext';
import {
  fetchThreadFamilies,
  fetchThreadSizes,
  fetchThreadSpec,
  fetchTapDrill,
  generateThread,
  generatePrintOptimizedThread,
  fetchPrintRecommendation,
} from '@/lib/api/threads';
import type {
  ThreadFamilyListResponse,
  ThreadSizeListResponse,
  ThreadSpec,
  TapDrillInfo,
  ThreadGenerateRequest,
  ThreadGenerateResponse,
  PrintOptimizedGenerateRequest,
  PrintOptimizedGenerateResponse,
  PrintRecommendation,
} from '@/types/threads';

// =============================================================================
// Query Keys
// =============================================================================

/** Query key factory for thread library queries. */
export const threadKeys = {
  all: ['threads'] as const,
  families: () => [...threadKeys.all, 'families'] as const,
  sizes: (family: string, pitchSeries?: string) =>
    [...threadKeys.all, 'sizes', family, pitchSeries ?? 'default'] as const,
  spec: (family: string, size: string) =>
    [...threadKeys.all, 'spec', family, size] as const,
  tapDrill: (family: string, size: string) =>
    [...threadKeys.all, 'tap-drill', family, size] as const,
  printRec: (family: string, size: string, process?: string) =>
    [...threadKeys.all, 'print-rec', family, size, process ?? 'default'] as const,
};

// =============================================================================
// Query Hooks
// =============================================================================

/**
 * Hook to fetch all available thread families.
 *
 * @returns Query result with thread family list.
 */
export function useThreadFamilies() {
  const { token } = useAuth();

  return useQuery<ThreadFamilyListResponse, Error>({
    queryKey: threadKeys.families(),
    queryFn: () => fetchThreadFamilies(token ?? undefined),
  });
}

/**
 * Hook to fetch sizes for a given thread family.
 *
 * @param family - Thread family id, or null to disable.
 * @param pitchSeries - Optional pitch series filter.
 * @returns Query result with thread size list.
 */
export function useThreadSizes(family: string | null, pitchSeries?: string) {
  const { token } = useAuth();

  return useQuery<ThreadSizeListResponse, Error>({
    queryKey: threadKeys.sizes(family ?? '', pitchSeries),
    queryFn: () => fetchThreadSizes(family!, pitchSeries, token ?? undefined),
    enabled: !!family,
  });
}

/**
 * Hook to fetch the full specification for a thread.
 *
 * @param family - Thread family id, or null to disable.
 * @param size - Thread size designation, or null to disable.
 * @returns Query result with thread specification.
 */
export function useThreadSpec(family: string | null, size: string | null) {
  const { token } = useAuth();

  return useQuery<ThreadSpec, Error>({
    queryKey: threadKeys.spec(family ?? '', size ?? ''),
    queryFn: () => fetchThreadSpec(family!, size!, token ?? undefined),
    enabled: !!family && !!size,
  });
}

/**
 * Hook to fetch tap drill and clearance hole data.
 *
 * @param family - Thread family id, or null to disable.
 * @param size - Thread size designation, or null to disable.
 * @returns Query result with tap drill info.
 */
export function useTapDrill(family: string | null, size: string | null) {
  const { token } = useAuth();

  return useQuery<TapDrillInfo, Error>({
    queryKey: threadKeys.tapDrill(family ?? '', size ?? ''),
    queryFn: () => fetchTapDrill(family!, size!, token ?? undefined),
    enabled: !!family && !!size,
  });
}

/**
 * Hook to fetch print recommendation for a thread.
 *
 * @param family - Thread family id, or null to disable.
 * @param size - Thread size designation, or null to disable.
 * @param process - Optional printing process filter.
 * @returns Query result with print recommendation.
 */
export function usePrintRecommendation(
  family: string | null,
  size: string | null,
  process?: string,
) {
  const { token } = useAuth();

  return useQuery<PrintRecommendation, Error>({
    queryKey: threadKeys.printRec(family ?? '', size ?? '', process),
    queryFn: () => fetchPrintRecommendation(family!, size!, process, token ?? undefined),
    enabled: !!family && !!size,
  });
}

// =============================================================================
// Mutation Hooks
// =============================================================================

/**
 * Hook to generate a thread CAD model.
 *
 * @returns Mutation for thread generation.
 *
 * @example
 * ```tsx
 * const { mutate, isPending } = useGenerateThread();
 * mutate({ family: 'iso_metric', size: 'M8', length_mm: 20 });
 * ```
 */
export function useGenerateThread() {
  const { token } = useAuth();

  return useMutation<ThreadGenerateResponse, Error, ThreadGenerateRequest>({
    mutationFn: (request) => generateThread(request, token ?? undefined),
  });
}

/**
 * Hook to generate a print-optimized thread CAD model.
 *
 * @returns Mutation for print-optimized thread generation.
 */
export function useGeneratePrintOptimized() {
  const { token } = useAuth();

  return useMutation<PrintOptimizedGenerateResponse, Error, PrintOptimizedGenerateRequest>({
    mutationFn: (request) => generatePrintOptimizedThread(request, token ?? undefined),
  });
}
