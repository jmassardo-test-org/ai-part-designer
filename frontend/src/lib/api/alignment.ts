/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Alignment API client.
 *
 * Handles part alignment operations for assembly workflows.
 */

/** Supported alignment modes. */
export type AlignmentMode =
  | 'center'
  | 'CENTER'
  | 'align-x'
  | 'align-y'
  | 'align-z'
  | 'stack'
  | 'distribute'
  | 'mate'
  | 'custom';

/** Transformation information for an aligned part. */
export interface TransformationInfo {
  [key: string]: any;
  translation: [number, number, number];
  rotation: [number, number, number];
  scale: [number, number, number];
  applied_translation?: any;
  final_bounds?: any;
  file_path?: string;
}

/** Response from an alignment operation. */
export interface AlignmentResponse {
  [key: string]: any;
  success: boolean;
  transformations: any;
  preview_url?: string;
  output_path?: string;
  message?: string;
  error?: string;
}

/** Preset alignment configurations. */
export const ALIGNMENT_PRESETS: Record<string, any> = {
  center: { mode: 'center', label: 'Center', description: 'Center all parts on origin' },
  'stack-z': { mode: 'stack', label: 'Stack (Z)', description: 'Stack parts along Z axis' },
  'align-x': { mode: 'align-x', label: 'Align X', description: 'Align parts along X axis' },
  'align-y': { mode: 'align-y', label: 'Align Y', description: 'Align parts along Y axis' },
};

/** Alignment API methods. */
export const alignmentApi: any = {
  async align(
    partIds: string[],
    mode: AlignmentMode,
    options?: Record<string, unknown>,
    token?: string
  ): Promise<AlignmentResponse> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/alignment/align', {
      method: 'POST',
      headers,
      body: JSON.stringify({ part_ids: partIds, mode, ...options }),
    });
    if (!resp.ok) throw new Error(`Alignment failed: ${resp.status}`);
    return resp.json();
  },
  async alignParts(
    partIds: string[],
    mode: AlignmentMode,
    options?: { gap?: number; reference?: string },
    token?: string
  ): Promise<AlignmentResponse> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/alignment/align', {
      method: 'POST',
      headers,
      body: JSON.stringify({ part_ids: partIds, mode, ...options }),
    });
    if (!resp.ok) throw new Error(`Alignment failed: ${resp.status}`);
    return resp.json();
  },
};
