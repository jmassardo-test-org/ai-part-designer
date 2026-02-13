/**
 * Generation and file handling API client.
 * Handles downloading generated files and preview data.
 */

const GENERATE_API = '/api/v1/generate';

/** Response from a generation request. */
export interface GenerateResponse {
  [key: string]: any;
  job_id: string;
  status: string;
  preview_url?: string;
  stl_url?: string;
  error?: string;
}

/**
 * Generate a CAD model from a natural language description.
 */
export async function generateFromDescription(
  descriptionOrRequest: string | Record<string, any>,
  authToken?: string,
  options?: { format?: string; quality?: string }
): Promise<GenerateResponse> {
  const body = typeof descriptionOrRequest === 'string'
    ? { description: descriptionOrRequest, ...options }
    : descriptionOrRequest;
  const token = authToken || '';
  const resp = await fetch(`${GENERATE_API}/from-description`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });

  if (!resp.ok) {
    throw new Error(`Generation failed: ${resp.status}`);
  }

  return resp.json();
}

/**
 * Download a generated CAD file.
 */
export async function downloadGeneratedFile(
  jobId: string,
  fileFormat: string,
  authToken: string
): Promise<Blob> {
  const resp = await fetch(`${GENERATE_API}/${jobId}/download/${fileFormat}`, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${authToken}`,
    },
  });

  if (!resp.ok) {
    throw new Error(`Failed to download file: ${resp.status}`);
  }

  return resp.blob();
}

/**
 * Get preview data (STL) for a generated model.
 */
export async function getPreviewData(
  jobId: string,
  authToken: string
): Promise<ArrayBuffer> {
  const resp = await fetch(`${GENERATE_API}/${jobId}/preview`, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${authToken}`,
    },
  });

  if (!resp.ok) {
    throw new Error(`Failed to fetch preview: ${resp.status}`);
  }

  return resp.arrayBuffer();
}
