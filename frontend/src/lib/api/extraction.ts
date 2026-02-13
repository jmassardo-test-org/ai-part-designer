/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Dimension extraction API client.
 *
 * Handles extracting dimensions and features from uploaded files.
 */

/** Mounting hole extracted from a drawing/image. */
export interface MountingHole {
  [key: string]: any;
  x: number;
  y: number;
  diameter: number;
  depth?: number;
  type?: string;
}

/** Cutout extracted from a drawing/image. */
export interface Cutout {
  [key: string]: any;
  x: number;
  y: number;
  width: number;
  height: number;
  type?: string;
  label?: string;
}

/** Connector extracted from a drawing/image. */
export interface Connector {
  [key: string]: any;
  x: number;
  y: number;
  type: string;
  label?: string;
  width?: number;
  height?: number;
}

/** Response from dimension extraction. */
export interface DimensionResponse {
  [key: string]: any;
  width?: number;
  height?: number;
  depth?: number;
  unit: string;
  mounting_holes: MountingHole[];
  cutouts: Cutout[];
  connectors: Connector[];
  notes?: string[];
  confidence: number;
}

/** Extraction API methods. */
export const extractionApi: any = {
  async extractDimensions(file: File, token?: string): Promise<DimensionResponse> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const formData = new FormData();
    formData.append('file', file);
    const resp = await fetch('/api/v1/extraction/dimensions', {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!resp.ok) throw new Error(`Extraction failed: ${resp.status}`);
    return resp.json();
  },
};
