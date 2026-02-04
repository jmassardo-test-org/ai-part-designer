/**
 * TypeScript types for CAD v2 API.
 *
 * These types match the backend Pydantic schemas in app/cad_v2/schemas/
 */

// =============================================================================
// Base Types
// =============================================================================

export interface Dimension {
  value: number;
  unit?: 'mm' | 'in';
}

export interface Point2D {
  x: number;
  y: number;
}

export interface Point3D {
  x: number;
  y: number;
  z: number;
}

export interface BoundingBox {
  width: Dimension;
  depth: Dimension;
  height: Dimension;
}

// =============================================================================
// Enclosure Types
// =============================================================================

export type LidType = 'snap_fit' | 'screw_on' | 'slide_on' | 'friction' | 'hinge' | 'none';
export type WallSide = 'front' | 'back' | 'left' | 'right' | 'top' | 'bottom';

export interface SnapFitSpec {
  lip_height?: Dimension;
  lip_thickness?: Dimension;
  clearance?: Dimension;
}

export interface ScrewSpec {
  hole_diameter?: Dimension;
  head_diameter?: Dimension;
  head_depth?: Dimension;
  boss_diameter?: Dimension;
  positions?: Point3D[];
}

export interface LidSpec {
  type: LidType;
  side?: WallSide;
  snap_fit?: SnapFitSpec;
  screws?: ScrewSpec;
  separate_part?: boolean;
  lip_inside?: boolean;
}

export interface WallSpec {
  thickness?: Dimension;
  front?: Dimension;
  back?: Dimension;
  left?: Dimension;
  right?: Dimension;
  top?: Dimension;
  bottom?: Dimension;
}

export interface VentilationSpec {
  enabled: boolean;
  sides?: WallSide[];
  pattern?: 'slots' | 'holes' | 'honeycomb';
  slot_width?: Dimension;
  slot_length?: Dimension;
  slot_spacing?: Dimension;
  margin?: Dimension;
}

export interface MountingTabSpec {
  enabled: boolean;
  sides?: WallSide[];
  width?: Dimension;
  depth?: Dimension;
  hole_diameter?: Dimension;
  count_per_side?: number;
}

// =============================================================================
// Component Types
// =============================================================================

export type MountingType = 'standoff' | 'surface' | 'clip' | 'press_fit' | 'bracket';
export type StandoffType = 'cylindrical' | 'hexagonal' | 'square';

export interface StandoffSpec {
  height?: Dimension;
  outer_diameter?: Dimension;
  hole_diameter?: Dimension;
  type?: StandoffType;
}

export interface ComponentRef {
  component_id: string;
  alias?: string;
}

export interface PortExposure {
  port_name: string;
  side: WallSide;
  clearance?: Dimension;
  label?: string;
}

export interface ComponentMount {
  component: ComponentRef;
  position?: Point3D;
  rotation?: { x: number; y: number; z: number };
  mount_side?: WallSide;
  mounting_type?: MountingType;
  standoffs?: StandoffSpec;
  expose_ports?: PortExposure[];
  label?: string;
}

// =============================================================================
// Feature Types
// =============================================================================

export interface RectangleCutout {
  type: 'rectangle';
  side: WallSide;
  position: Point2D;
  width: Dimension;
  height: Dimension;
  corner_radius?: Dimension;
}

export interface CircleCutout {
  type: 'circle';
  side: WallSide;
  position: Point2D;
  diameter: Dimension;
}

export interface PortCutout {
  type: 'port';
  side: WallSide;
  position: Point2D;
  port_type: string; // 'usb-c', 'hdmi', 'ethernet', etc.
  clearance?: Dimension;
}

export interface ButtonCutout {
  type: 'button';
  side: WallSide;
  position: Point2D;
  diameter: Dimension;
  travel?: Dimension;
}

export interface DisplayCutout {
  type: 'display';
  side: WallSide;
  position: Point2D;
  viewing_width: Dimension;
  viewing_height: Dimension;
  bezel_width?: Dimension;
}

export interface TextFeature {
  type: 'text';
  side: WallSide;
  position: Point2D;
  text: string;
  font_size?: Dimension;
  depth?: Dimension;
  emboss?: boolean;
  font?: string;
}

export type Feature =
  | RectangleCutout
  | CircleCutout
  | PortCutout
  | ButtonCutout
  | DisplayCutout
  | TextFeature;

// =============================================================================
// Enclosure Spec (Main Schema)
// =============================================================================

export interface EnclosureSpec {
  exterior: BoundingBox;
  walls?: WallSpec;
  corner_radius?: Dimension;
  lid?: LidSpec;
  components?: ComponentMount[];
  features?: Feature[];
  ventilation?: VentilationSpec;
  mounting_tabs?: MountingTabSpec;
  name?: string;
  description?: string;
}

// =============================================================================
// API Request/Response Types
// =============================================================================

export interface GenerateV2Request {
  description: string;
  export_format?: 'step' | 'stl';
}

export interface GenerateV2Response {
  job_id: string;
  success: boolean;
  generated_schema?: EnclosureSpec;
  parts: string[];
  downloads: Record<string, string>;
  warnings: string[];
  errors: string[];
  clarification_needed?: string;
}

export interface CompileRequest {
  enclosure_schema: EnclosureSpec;
  export_format?: 'step' | 'stl';
  async_mode?: boolean;
}

export interface CompileResponse {
  job_id: string;
  success: boolean;
  parts: string[];
  files: string[];
  downloads: Record<string, string>;
  errors: string[];
  warnings: string[];
  metadata?: {
    exterior: [number, number, number];
    interior: [number, number, number];
    wall_thickness: number;
    part_count: number;
  };
}

export interface SchemaPreviewRequest {
  description: string;
}

export interface SchemaPreviewResponse {
  success: boolean;
  generated_schema?: EnclosureSpec;
  validation_errors?: string[];
  clarification_needed?: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress?: number;
  message?: string;
  files?: string[];
  error?: string;
}
