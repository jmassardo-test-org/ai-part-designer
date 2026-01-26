/**
 * File and Version-related type definitions.
 */

export type FileStatus = 
  | 'uploading'
  | 'processing'
  | 'ready'
  | 'error'
  | 'deleted';

export type CadFormat = 
  | 'step'
  | 'stp'
  | 'stl'
  | 'iges'
  | 'igs'
  | 'obj'
  | '3mf'
  | 'brep';

export interface FileInfo {
  id: string;
  filename: string;
  original_filename: string;
  size_bytes: number;
  file_type: string;
  cad_format: CadFormat | null;
  status: FileStatus;
  download_url: string;
  thumbnail_url?: string;
  created_at: string;
  updated_at: string;
  geometry_info?: GeometryInfo;
}

export interface GeometryInfo {
  volume?: number;
  surface_area?: number;
  bounding_box?: {
    x: number;
    y: number;
    z: number;
  };
  center_of_mass?: {
    x: number;
    y: number;
    z: number;
  };
  is_manifold?: boolean;
  triangle_count?: number;
}

export interface DesignFile {
  id: string;
  name: string;
  description?: string;
  project_id: string;
  current_version_id?: string;
  source_type: 'template' | 'ai_generated' | 'imported' | 'modified';
  status: FileStatus;
  thumbnail_url?: string;
  tags: string[];
  is_public: boolean;
  view_count: number;
  created_at: string;
  updated_at: string;
  versions_count: number;
}

export interface DesignVersion {
  id: string;
  design_id: string;
  version_number: number;
  file_url: string;
  thumbnail_url?: string;
  file_formats: Record<string, string>;
  parameters: Record<string, unknown>;
  geometry_info: GeometryInfo;
  change_description?: string;
  created_at: string;
  created_by_name?: string;
}

export interface VersionListResponse {
  versions: DesignVersion[];
  total: number;
  page: number;
  page_size: number;
}

export interface VersionComparison {
  version_a: DesignVersion;
  version_b: DesignVersion;
  parameter_diff: Record<string, { version_a: unknown; version_b: unknown }>;
  geometry_diff: Record<string, { version_a: unknown; version_b: unknown }>;
}

export interface VersionDiffItem {
  field: string;
  old_value: unknown;
  new_value: unknown;
  change_type: 'added' | 'removed' | 'modified';
}

export interface VersionDiff {
  from_version: number;
  to_version: number;
  parameter_changes: VersionDiffItem[];
  geometry_changes: VersionDiffItem[];
  summary: string;
}
