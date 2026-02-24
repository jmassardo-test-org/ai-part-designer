/**
 * Thread Library type definitions.
 *
 * TypeScript interfaces for the thread generation and specification APIs.
 */

/** Thread standard family identifier. */
export type ThreadFamilyId =
  | 'iso_metric'
  | 'unc'
  | 'unf'
  | 'npt'
  | 'bspp'
  | 'bspt'
  | 'acme'
  | 'trapezoidal';

/** Thread direction (internal or external). */
export type ThreadType = 'internal' | 'external';

/** Thread helix direction. */
export type ThreadHand = 'right' | 'left';

/** Pitch series for metric threads. */
export type PitchSeries = 'coarse' | 'fine' | 'superfine';

/** 3D printing process. */
export type PrintProcess = 'fdm' | 'sla' | 'sls' | 'mjf';

/** Thread tolerance class. */
export type ToleranceClass = 'tight' | 'standard' | 'loose';

/** Print feasibility rating. */
export type PrintFeasibility = 'excellent' | 'good' | 'marginal' | 'not_recommended';

/** Thread family information. */
export interface ThreadFamily {
  family: ThreadFamilyId;
  name: string;
  description: string;
  standard_ref: string;
  size_count: number;
}

/** Thread family list response. */
export interface ThreadFamilyListResponse {
  families: ThreadFamily[];
  total: number;
}

/** Complete thread specification. */
export interface ThreadSpec {
  family: string;
  size: string;
  pitch_mm: number;
  form: string;
  pitch_series: string | null;
  major_diameter: number;
  pitch_diameter_ext: number;
  minor_diameter_ext: number;
  major_diameter_int: number;
  pitch_diameter_int: number;
  minor_diameter_int: number;
  profile_angle_deg: number;
  taper_per_mm: number;
  tap_drill_mm: number;
  clearance_hole_close_mm: number;
  clearance_hole_medium_mm: number;
  clearance_hole_free_mm: number;
  tpi: number | null;
  nominal_size_inch: string | null;
  engagement_length_mm: number;
  standard_ref: string;
  notes: string;
}

/** Thread size list response. */
export interface ThreadSizeListResponse {
  family: string;
  sizes: string[];
  total: number;
  pitch_series: string | null;
}

/** Tap drill info response. */
export interface TapDrillInfo {
  family: string;
  size: string;
  tap_drill_mm: number;
  clearance_hole_close_mm: number;
  clearance_hole_medium_mm: number;
  clearance_hole_free_mm: number;
}

/** Thread generation request. */
export interface ThreadGenerateRequest {
  family: string;
  size: string;
  thread_type?: ThreadType;
  length_mm: number;
  hand?: ThreadHand;
  pitch_series?: PitchSeries | null;
  custom_pitch_mm?: number | null;
  custom_diameter_mm?: number | null;
  add_chamfer?: boolean;
}

/** Thread generation response. */
export interface ThreadGenerateResponse {
  success: boolean;
  metadata: Record<string, unknown>;
  generation_time_ms: number;
  estimated_face_count: number;
  message: string;
}

/** Print recommendation response. */
export interface PrintRecommendation {
  family: string;
  size: string;
  feasibility: PrintFeasibility;
  min_recommended_size: string;
  recommended_tolerance: string;
  clearance_mm: number;
  notes: string[];
  orientation_advice: string;
  estimated_strength_pct: number;
}

/** Print-optimized generation request. */
export interface PrintOptimizedGenerateRequest {
  family: string;
  size: string;
  thread_type?: ThreadType;
  length_mm: number;
  process?: PrintProcess;
  tolerance_class?: ToleranceClass;
  nozzle_diameter_mm?: number;
  layer_height_mm?: number;
  use_flat_bottom?: boolean;
  custom_clearance_mm?: number | null;
  pitch_series?: PitchSeries | null;
  hand?: ThreadHand;
  add_chamfer?: boolean;
}

/** Print-optimized generation response. */
export interface PrintOptimizedGenerateResponse {
  success: boolean;
  feasibility: string;
  adjustments_applied: Record<string, number>;
  recommendation: PrintRecommendation;
  generation_result: ThreadGenerateResponse | null;
  message: string;
}
