/**
 * Layout Editor Types
 */

export interface Position {
  x: number;
  y: number;
}

export interface Dimensions {
  width: number;
  depth: number;
  height: number;
}

export interface LayoutDimensions {
  width: number;
  depth: number;
  height: number;
  gridSize: number;
  clearance: number;
  autoDimensions: boolean;
}

export interface ComponentPlacement {
  id: string;
  componentId: string;
  name: string;
  x: number;
  y: number;
  z: number;
  rotation: number;
  width: number;
  depth: number;
  height: number;
  faceDirection?: 'front' | 'back' | 'left' | 'right' | 'top' | 'bottom' | 'none';
  locked: boolean;
  colorOverride?: string;
  hasError?: boolean;
}

export interface ComponentData {
  id: string;
  name: string;
  width: number;
  depth: number;
  height: number;
  thumbnailUrl?: string;
  connectorFaces?: string[];
  isThermalSource?: boolean;
}

export interface ValidationError {
  type: 'collision' | 'boundary' | 'clearance';
  message: string;
  placementIds: string[];
}

export interface ValidationWarning {
  type: 'thermal' | 'connector' | 'clearance';
  message: string;
  placementIds: string[];
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
}

export interface LayoutEditorProps {
  layoutId?: string;
  projectId: string;
  dimensions: LayoutDimensions;
  placements: ComponentPlacement[];
  availableComponents: ComponentData[];
  onPlacementChange?: (placement: ComponentPlacement) => void;
  onPlacementAdd?: (componentId: string, position: Position) => void;
  onPlacementRemove?: (placementId: string) => void;
  onDimensionsChange?: (dimensions: LayoutDimensions) => void;
  onAutoLayout?: () => void;
  onSave?: () => void;
  readOnly?: boolean;
}

export interface CanvasState {
  zoom: number;
  panX: number;
  panY: number;
  selectedId: string | null;
  isDragging: boolean;
  dragOffset: Position;
}

export interface ToolbarAction {
  id: string;
  label: string;
  icon: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  active?: boolean;
}

// API response types
export interface LayoutResponse {
  id: string;
  projectId: string;
  name: string;
  internalWidth: number;
  internalDepth: number;
  internalHeight: number;
  autoDimensions: boolean;
  gridSize: number;
  clearanceMargin: number;
  status: string;
  placements: PlacementResponse[];
  createdAt: string;
  updatedAt: string;
}

export interface PlacementResponse {
  id: string;
  layoutId: string;
  componentId: string;
  componentName?: string;
  xPosition: number;
  yPosition: number;
  zPosition: number;
  rotationZ: number;
  width: number;
  depth: number;
  height: number;
  faceDirection?: string;
  locked: boolean;
}

// Helper to convert API response to internal format
export function apiToLayoutDimensions(response: LayoutResponse): LayoutDimensions {
  return {
    width: response.internalWidth,
    depth: response.internalDepth,
    height: response.internalHeight,
    gridSize: response.gridSize,
    clearance: response.clearanceMargin,
    autoDimensions: response.autoDimensions,
  };
}

export function apiToPlacement(p: PlacementResponse): ComponentPlacement {
  return {
    id: p.id,
    componentId: p.componentId,
    name: p.componentName || 'Component',
    x: p.xPosition,
    y: p.yPosition,
    z: p.zPosition,
    rotation: p.rotationZ,
    width: p.width,
    depth: p.depth,
    height: p.height,
    faceDirection: p.faceDirection as ComponentPlacement['faceDirection'],
    locked: p.locked,
  };
}
