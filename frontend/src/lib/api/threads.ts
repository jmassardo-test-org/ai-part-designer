/**
 * Thread Library API client.
 *
 * Provides functions for thread specification lookup, generation,
 * and print-optimization endpoints.
 */

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

const BASE_URL = '/api/v2';

/**
 * Build authorization headers for API requests.
 *
 * @param token - Optional bearer token.
 * @returns Header record with Content-Type and optional Authorization.
 */
function authHeaders(token?: string): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

/**
 * Fetch the list of available thread families.
 *
 * @param token - Optional auth token.
 * @returns Thread family list with counts.
 */
export async function fetchThreadFamilies(token?: string): Promise<ThreadFamilyListResponse> {
  const resp = await fetch(`${BASE_URL}/threads/families`, {
    headers: authHeaders(token),
  });
  if (!resp.ok) throw new Error(`Failed to fetch thread families: ${resp.status}`);
  return resp.json();
}

/**
 * Fetch available sizes for a thread family.
 *
 * @param family - Thread family identifier (e.g. 'iso_metric').
 * @param pitchSeries - Optional pitch series filter.
 * @param token - Optional auth token.
 * @returns List of available sizes.
 */
export async function fetchThreadSizes(
  family: string,
  pitchSeries?: string,
  token?: string,
): Promise<ThreadSizeListResponse> {
  const params = new URLSearchParams();
  if (pitchSeries) params.set('pitch_series', pitchSeries);
  const query = params.toString() ? `?${params.toString()}` : '';
  const resp = await fetch(`${BASE_URL}/threads/standards/${family}${query}`, {
    headers: authHeaders(token),
  });
  if (!resp.ok) throw new Error(`Failed to fetch thread sizes: ${resp.status}`);
  return resp.json();
}

/**
 * Fetch the full specification for a given thread family and size.
 *
 * @param family - Thread family identifier.
 * @param size - Thread size designation.
 * @param token - Optional auth token.
 * @returns Complete thread specification.
 */
export async function fetchThreadSpec(
  family: string,
  size: string,
  token?: string,
): Promise<ThreadSpec> {
  const resp = await fetch(`${BASE_URL}/threads/standards/${family}/${encodeURIComponent(size)}`, {
    headers: authHeaders(token),
  });
  if (!resp.ok) throw new Error(`Failed to fetch thread spec: ${resp.status}`);
  return resp.json();
}

/**
 * Fetch tap drill and clearance hole information.
 *
 * @param family - Thread family identifier.
 * @param size - Thread size designation.
 * @param token - Optional auth token.
 * @returns Tap drill and clearance hole data.
 */
export async function fetchTapDrill(
  family: string,
  size: string,
  token?: string,
): Promise<TapDrillInfo> {
  const resp = await fetch(
    `${BASE_URL}/threads/tap-drill/${family}/${encodeURIComponent(size)}`,
    { headers: authHeaders(token) },
  );
  if (!resp.ok) throw new Error(`Failed to fetch tap drill info: ${resp.status}`);
  return resp.json();
}

/**
 * Generate a thread CAD model.
 *
 * @param request - Thread generation parameters.
 * @param token - Optional auth token.
 * @returns Generation result with metadata.
 */
export async function generateThread(
  request: ThreadGenerateRequest,
  token?: string,
): Promise<ThreadGenerateResponse> {
  const resp = await fetch(`${BASE_URL}/threads/generate`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(request),
  });
  if (!resp.ok) throw new Error(`Failed to generate thread: ${resp.status}`);
  return resp.json();
}

/**
 * Generate a print-optimized thread CAD model.
 *
 * @param request - Print-optimized generation parameters.
 * @param token - Optional auth token.
 * @returns Generation result with print recommendations.
 */
export async function generatePrintOptimizedThread(
  request: PrintOptimizedGenerateRequest,
  token?: string,
): Promise<PrintOptimizedGenerateResponse> {
  const resp = await fetch(`${BASE_URL}/threads/generate/print-optimized`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(request),
  });
  if (!resp.ok) throw new Error(`Failed to generate print-optimized thread: ${resp.status}`);
  return resp.json();
}

/**
 * Fetch a print recommendation for a specific thread.
 *
 * @param family - Thread family identifier.
 * @param size - Thread size designation.
 * @param process - Optional printing process (fdm, sla, etc.).
 * @param token - Optional auth token.
 * @returns Print feasibility recommendation.
 */
export async function fetchPrintRecommendation(
  family: string,
  size: string,
  process?: string,
  token?: string,
): Promise<PrintRecommendation> {
  const params = new URLSearchParams();
  if (process) params.set('process', process);
  const query = params.toString() ? `?${params.toString()}` : '';
  const resp = await fetch(
    `${BASE_URL}/threads/print-recommendations/${family}/${encodeURIComponent(size)}${query}`,
    { headers: authHeaders(token) },
  );
  if (!resp.ok) throw new Error(`Failed to fetch print recommendation: ${resp.status}`);
  return resp.json();
}
