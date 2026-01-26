/**
 * Job-related type definitions.
 */

export type JobStatus = 
  | 'pending'
  | 'queued'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type JobType = 
  | 'generate'
  | 'ai_generation'
  | 'convert'
  | 'modify'
  | 'export'
  | 'validate'
  | 'thumbnail';

export interface JobProgress {
  current: number;
  total: number;
  percentage: number;
  stage?: string;
}

export interface JobResult {
  file_id?: string;
  file_url?: string;
  thumbnail_url?: string;
  geometry_info?: GeometryInfo;
  error_code?: string;
  error_detail?: string;
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

export interface Job {
  id: string;
  type: JobType;
  status: JobStatus;
  priority: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  progress?: JobProgress;
  result?: JobResult;
  error_message?: string;
  retry_count: number;
  max_retries: number;
  metadata?: Record<string, unknown>;
  // Input parameters used for the job
  input_params?: {
    prompt?: string;
    style?: string;
    [key: string]: unknown;
  };
  // If saved as a design, the design ID
  design_id?: string;
}

export interface JobListResponse {
  jobs: Job[];
  total: number;
  page: number;
  page_size: number;
}
