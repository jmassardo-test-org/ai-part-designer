/**
 * Layout Editor Components
 * 
 * 2D spatial layout editor for arranging components within enclosures.
 */

export { LayoutEditor } from './LayoutEditor';
export { LayoutCanvas } from './LayoutCanvas';
export { ComponentItem } from './ComponentItem';
export { LayoutToolbar } from './LayoutToolbar';
export { LayoutSidebar } from './LayoutSidebar';
export { LayoutPreview3D } from './LayoutPreview3D';

export type { LayoutAlgorithm } from './LayoutToolbar';

export type {
  Position,
  Dimensions,
  LayoutDimensions,
  ComponentPlacement,
  ComponentData,
  ValidationError,
  ValidationWarning,
  ValidationResult,
  LayoutEditorProps,
  CanvasState,
  ToolbarAction,
  LayoutResponse,
  PlacementResponse,
} from './types';

export {
  apiToLayoutDimensions,
  apiToPlacement,
} from './types';
