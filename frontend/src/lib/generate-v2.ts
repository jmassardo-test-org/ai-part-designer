/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * CAD v2 generation API client.
 *
 * Handles v2 generation workflows, enclosure specs, and file operations.
 */

import type {
  CompileRequest,
  CompileResponse,
  EnclosureSpec,
  GenerateV2Request,
  GenerateV2Response,
  JobStatusResponse,
  SchemaPreviewResponse,
} from '@/types/cad-v2';

/** Response from async compile. */
export interface AsyncCompileResponse {
  [key: string]: any;
  job_id: string;
  status: string;
}

/** Response from saving a v2 design. */
export interface SaveDesignV2Response {
  [key: string]: any;
  design_id: string;
  name: string;
}

/** Request to save a v2 design. */
export interface SaveDesignV2Request {
  [key: string]: any;
  name: string;
  description?: string;
  project_id?: string;
  job_id: string;
}

/** Response from listing v2 designs. */
export interface ListDesignsV2Response {
  [key: string]: any;
  items: any[];
  total: number;
}

// Re-export types used by consumers
export type {
  CompileRequest,
  CompileResponse,
  EnclosureSpec,
  GenerateV2Request,
  GenerateV2Response,
  JobStatusResponse,
  SchemaPreviewResponse,
};

const API_BASE = '/api/v2/generate';

/**
 * Generate a CAD model from a natural language description (v2).
 */
export async function generateFromDescriptionV2(
  request: GenerateV2Request,
  token?: string
): Promise<GenerateV2Response> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE}/from-description`, {
    method: 'POST',
    headers,
    body: JSON.stringify(request),
  });
  if (!resp.ok) throw new Error(`Generation failed: ${resp.status}`);
  return resp.json();
}

/**
 * Generate asynchronously and return a job ID.
 */
export async function generateAsync(
  request: GenerateV2Request,
  token?: string
): Promise<GenerateV2Response> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE}/async`, {
    method: 'POST',
    headers,
    body: JSON.stringify(request),
  });
  if (!resp.ok) throw new Error(`Async generation failed: ${resp.status}`);
  return resp.json();
}

/**
 * Get status of a generation job.
 */
export async function getJobStatus(jobId: string, token?: string): Promise<JobStatusResponse> {
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE}/jobs/${jobId}`, { headers });
  if (!resp.ok) throw new Error(`Failed to get job status: ${resp.status}`);
  return resp.json();
}

/**
 * List files for a completed job.
 */
export async function listJobFiles(jobId: string, token?: string): Promise<string[]> {
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE}/jobs/${jobId}/files`, { headers });
  if (!resp.ok) throw new Error(`Failed to list job files: ${resp.status}`);
  return resp.json();
}

/**
 * Download a file from a completed job.
 */
export async function downloadFile(jobId: string, filename: string, token?: string): Promise<Blob> {
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE}/jobs/${jobId}/files/${filename}`, { headers });
  if (!resp.ok) throw new Error(`Download failed: ${resp.status}`);
  return resp.blob();
}

/**
 * Compile an enclosure from a spec.
 */
export async function compileEnclosure(
  request: CompileRequest,
  token?: string
): Promise<CompileResponse> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE}/compile`, {
    method: 'POST',
    headers,
    body: JSON.stringify(request),
  });
  if (!resp.ok) throw new Error(`Compilation failed: ${resp.status}`);
  return resp.json();
}

/**
 * Preview a schema before compilation.
 */
export async function previewSchema(
  spec: any,
  token?: string
): Promise<SchemaPreviewResponse> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE}/preview`, {
    method: 'POST',
    headers,
    body: JSON.stringify(spec),
  });
  if (!resp.ok) throw new Error(`Preview failed: ${resp.status}`);
  return resp.json();
}

/**
 * Create a basic enclosure spec with dimensions.
 */
export function createEnclosureSpec(
  width: number,
  height: number,
  depth: number,
  optionsOrWallThickness?: number | Record<string, any>
): EnclosureSpec {
  const wallThickness = typeof optionsOrWallThickness === 'number' ? optionsOrWallThickness : 2;
  return {
    dimensions: { width, height, depth },
    wall_thickness: wallThickness,
    ...(typeof optionsOrWallThickness === 'object' ? optionsOrWallThickness : {}),
  } as unknown as EnclosureSpec;
}

/**
 * Add ventilation to an enclosure spec.
 */
export function addVentilation(
  spec: EnclosureSpec,
  typeOrOptions?: any,
  sides: string[] = ['left', 'right']
): EnclosureSpec {
  const ventConfig = typeof typeOrOptions === 'object'
    ? typeOrOptions
    : { type: typeOrOptions || 'slots', sides };
  return {
    ...spec,
    ventilation: ventConfig,
  } as unknown as EnclosureSpec;
}

/**
 * Add a lid to an enclosure spec.
 */
export function addLid(
  spec: EnclosureSpec,
  type?: any
): EnclosureSpec {
  return {
    ...spec,
    lid: { type: type || 'snap' },
  } as unknown as EnclosureSpec;
}

/**
 * Get a download URL for a generated file.
 */
export function getDownloadUrl(jobId: string, filename: string): string {
  return `${API_BASE}/jobs/${jobId}/files/${filename}`;
}

/**
 * Compile enclosure asynchronously.
 */
export async function compileEnclosureAsync(
  requestOrSchema: CompileRequest | EnclosureSpec,
  formatOrToken?: string,
  token?: string
): Promise<AsyncCompileResponse> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  const authToken = token || (formatOrToken && !['step', 'stl', 'both'].includes(formatOrToken) ? formatOrToken : undefined);
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
  const resp = await fetch(`${API_BASE}/compile/async`, {
    method: 'POST',
    headers,
    body: JSON.stringify(requestOrSchema),
  });
  if (!resp.ok) throw new Error(`Async compilation failed: ${resp.status}`);
  return resp.json();
}

/**
 * Save a v2 design.
 */
export async function saveDesignV2(
  request: SaveDesignV2Request,
  token?: string
): Promise<SaveDesignV2Response> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE}/designs`, {
    method: 'POST',
    headers,
    body: JSON.stringify(request),
  });
  if (!resp.ok) throw new Error(`Failed to save design: ${resp.status}`);
  return resp.json();
}

/**
 * Get a v2 design by ID.
 */
export async function getDesignV2(
  designId: string,
  token?: string
): Promise<SaveDesignV2Response> {
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE}/designs/${designId}`, { headers });
  if (!resp.ok) throw new Error(`Failed to get design: ${resp.status}`);
  return resp.json();
}

/**
 * List v2 designs.
 */
export async function listDesignsV2(
  params?: any,
  token?: string
): Promise<ListDesignsV2Response> {
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const query = params ? '?' + new URLSearchParams(params).toString() : '';
  const resp = await fetch(`${API_BASE}/designs${query}`, { headers });
  if (!resp.ok) throw new Error(`Failed to list designs: ${resp.status}`);
  return resp.json();
}
