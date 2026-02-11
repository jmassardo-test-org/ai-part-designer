/**
 * Generation and file handling API client.
 * Handles downloading generated files and preview data.
 */

const GENERATE_API = '/api/v1/generate';

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
