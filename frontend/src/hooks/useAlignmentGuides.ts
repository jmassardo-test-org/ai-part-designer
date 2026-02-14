/**
 * useAlignmentGuides Hook
 *
 * Calculates alignment guides between parts during drag operations.
 * Detects edge, center, and face alignments with configurable thresholds.
 */

import { useMemo, useCallback } from 'react';
import * as THREE from 'three';

// =============================================================================
// Types
// =============================================================================

/** Type of alignment guide. */
export type AlignmentGuideType = 'edge' | 'center' | 'face';

/** Axis of alignment. */
export type AlignmentAxis = 'x' | 'y' | 'z';

/** A single alignment guide. */
export interface AlignmentGuide {
  /** Unique ID for this guide. */
  id: string;
  /** Type of alignment (edge, center, or face). */
  type: AlignmentGuideType;
  /** ID of the source part (being dragged). */
  sourcePartId: string;
  /** ID of the target part (aligned to). */
  targetPartId: string;
  /** Axis of alignment. */
  axis: AlignmentAxis;
  /** World position of the alignment. */
  position: THREE.Vector3;
  /** Start point of the guide line (for edge/center guides). */
  startPoint: THREE.Vector3;
  /** End point of the guide line (for edge/center guides). */
  endPoint: THREE.Vector3;
  /** Normal vector of the plane (for face guides). */
  planeNormal?: THREE.Vector3;
  /** Size of the plane (for face guides). */
  planeSize?: { width: number; height: number };
  /** Strength of alignment (0-1, based on distance to threshold). */
  strength: number;
  /** Distance from alignment (in units). */
  distance: number;
}

/** Settings for alignment calculation. */
export interface AlignmentSettings {
  /** Enable edge-to-edge alignment guides. */
  enableEdgeAlignment: boolean;
  /** Enable center-to-center alignment guides. */
  enableCenterAlignment: boolean;
  /** Enable face-to-face alignment guides. */
  enableFaceAlignment: boolean;
  /** Maximum distance for visual guide display (units). */
  snapDistance: number;
  /** Distance at which snap executes on release (units). */
  snapThreshold: number;
  /** Maximum simultaneous guides to display. */
  maxGuides: number;
}

/** Part information for alignment calculations. */
export interface AlignmentPart {
  /** Unique part ID. */
  id: string;
  /** Part name (for display). */
  name: string;
  /** Part position in world space. */
  position: THREE.Vector3;
  /** Part bounding box in world space. */
  boundingBox: THREE.Box3;
}

/** Options for useAlignmentGuides hook. */
export interface UseAlignmentGuidesOptions {
  /** All parts in the assembly (for calculating alignments). */
  parts: AlignmentPart[];
  /** Currently dragged part ID (null if not dragging). */
  draggedPartId: string | null;
  /** Current position of dragged part in world space. */
  dragPosition: THREE.Vector3 | null;
  /** Set of hidden part IDs (excluded from alignment). */
  hiddenParts: Set<string>;
  /** Alignment configuration. */
  settings: AlignmentSettings;
}

/** Return value of useAlignmentGuides hook. */
export interface UseAlignmentGuidesReturn {
  /** Active alignment guides to render. */
  guides: AlignmentGuide[];
  /** Suggested snap position if within threshold (null otherwise). */
  snapPosition: THREE.Vector3 | null;
  /** Whether any alignment is active. */
  hasActiveAlignment: boolean;
  /** Calculate final snap position on release. */
  calculateSnapPosition: (releasePosition: THREE.Vector3) => THREE.Vector3;
}

// =============================================================================
// Constants
// =============================================================================

/** Default alignment settings. */
export const DEFAULT_ALIGNMENT_SETTINGS: AlignmentSettings = {
  enableEdgeAlignment: true,
  enableCenterAlignment: true,
  enableFaceAlignment: true,
  snapDistance: 10,
  snapThreshold: 5,
  maxGuides: 6,
};

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Calculate center alignment between two parts.
 */
function calculateCenterAlignments(
  sourceId: string,
  sourcePos: THREE.Vector3,
  targetPart: AlignmentPart,
  settings: AlignmentSettings
): AlignmentGuide[] {
  const guides: AlignmentGuide[] = [];
  const targetCenter = new THREE.Vector3();
  targetPart.boundingBox.getCenter(targetCenter);

  // Check each axis
  const axes: AlignmentAxis[] = ['x', 'y', 'z'];
  for (const axis of axes) {
    const distance = Math.abs(sourcePos[axis] - targetCenter[axis]);

    if (distance <= settings.snapDistance) {
      const strength = 1 - distance / settings.snapDistance;

      // Create line from source to target center
      const startPoint = sourcePos.clone();
      const endPoint = targetCenter.clone();

      // Set the aligned axis value to match
      startPoint[axis] = sourcePos[axis];
      endPoint[axis] = targetCenter[axis];

      guides.push({
        id: `center-${sourceId}-${targetPart.id}-${axis}`,
        type: 'center',
        sourcePartId: sourceId,
        targetPartId: targetPart.id,
        axis,
        position: new THREE.Vector3().lerpVectors(startPoint, endPoint, 0.5),
        startPoint,
        endPoint,
        strength,
        distance,
      });
    }
  }

  return guides;
}

/**
 * Calculate edge alignment between two parts.
 */
function calculateEdgeAlignments(
  sourceId: string,
  sourceBox: THREE.Box3,
  targetPart: AlignmentPart,
  settings: AlignmentSettings
): AlignmentGuide[] {
  const guides: AlignmentGuide[] = [];
  const targetBox = targetPart.boundingBox;

  // Check min/max edges on each axis
  const axes: AlignmentAxis[] = ['x', 'y', 'z'];
  for (const axis of axes) {
    const sourceMin = sourceBox.min[axis];
    const sourceMax = sourceBox.max[axis];
    const targetMin = targetBox.min[axis];
    const targetMax = targetBox.max[axis];

    // Check source min vs target min
    const minMinDist = Math.abs(sourceMin - targetMin);
    if (minMinDist <= settings.snapDistance) {
      const strength = 1 - minMinDist / settings.snapDistance;
      guides.push(createEdgeGuide(sourceId, targetPart.id, axis, 'min-min', sourceMin, targetMin, strength, minMinDist, sourceBox, targetBox));
    }

    // Check source min vs target max
    const minMaxDist = Math.abs(sourceMin - targetMax);
    if (minMaxDist <= settings.snapDistance) {
      const strength = 1 - minMaxDist / settings.snapDistance;
      guides.push(createEdgeGuide(sourceId, targetPart.id, axis, 'min-max', sourceMin, targetMax, strength, minMaxDist, sourceBox, targetBox));
    }

    // Check source max vs target min
    const maxMinDist = Math.abs(sourceMax - targetMin);
    if (maxMinDist <= settings.snapDistance) {
      const strength = 1 - maxMinDist / settings.snapDistance;
      guides.push(createEdgeGuide(sourceId, targetPart.id, axis, 'max-min', sourceMax, targetMin, strength, maxMinDist, sourceBox, targetBox));
    }

    // Check source max vs target max
    const maxMaxDist = Math.abs(sourceMax - targetMax);
    if (maxMaxDist <= settings.snapDistance) {
      const strength = 1 - maxMaxDist / settings.snapDistance;
      guides.push(createEdgeGuide(sourceId, targetPart.id, axis, 'max-max', sourceMax, targetMax, strength, maxMaxDist, sourceBox, targetBox));
    }
  }

  return guides;
}

/**
 * Create an edge alignment guide.
 */
function createEdgeGuide(
  sourceId: string,
  targetId: string,
  axis: AlignmentAxis,
  edgeType: string,
  _sourceValue: number,
  targetValue: number,
  strength: number,
  distance: number,
  sourceBox: THREE.Box3,
  targetBox: THREE.Box3
): AlignmentGuide {
  // Create a line along the aligned edge
  const startPoint = new THREE.Vector3();
  const endPoint = new THREE.Vector3();

  // Get centers of both boxes
  sourceBox.getCenter(startPoint);
  targetBox.getCenter(endPoint);

  // Set the aligned axis to the target value
  startPoint[axis] = targetValue;
  endPoint[axis] = targetValue;

  return {
    id: `edge-${sourceId}-${targetId}-${axis}-${edgeType}`,
    type: 'edge',
    sourcePartId: sourceId,
    targetPartId: targetId,
    axis,
    position: new THREE.Vector3().lerpVectors(startPoint, endPoint, 0.5),
    startPoint,
    endPoint,
    strength,
    distance,
  };
}

/**
 * Calculate face alignment between two parts.
 */
function calculateFaceAlignments(
  sourceId: string,
  sourceBox: THREE.Box3,
  targetPart: AlignmentPart,
  settings: AlignmentSettings
): AlignmentGuide[] {
  const guides: AlignmentGuide[] = [];
  const targetBox = targetPart.boundingBox;

  // For face alignment, we check if faces are coplanar
  const axes: AlignmentAxis[] = ['x', 'y', 'z'];
  for (const axis of axes) {
    const sourceMin = sourceBox.min[axis];
    const sourceMax = sourceBox.max[axis];
    const targetMin = targetBox.min[axis];
    const targetMax = targetBox.max[axis];

    // Check if source min face aligns with target max face (abutting)
    const minMaxDist = Math.abs(sourceMin - targetMax);
    if (minMaxDist <= settings.snapDistance) {
      const strength = 1 - minMaxDist / settings.snapDistance;
      guides.push(createFaceGuide(sourceId, targetPart.id, axis, targetMax, strength, minMaxDist, sourceBox, targetBox));
    }

    // Check if source max face aligns with target min face (abutting)
    const maxMinDist = Math.abs(sourceMax - targetMin);
    if (maxMinDist <= settings.snapDistance) {
      const strength = 1 - maxMinDist / settings.snapDistance;
      guides.push(createFaceGuide(sourceId, targetPart.id, axis, targetMin, strength, maxMinDist, sourceBox, targetBox));
    }
  }

  return guides;
}

/**
 * Create a face alignment guide.
 */
function createFaceGuide(
  sourceId: string,
  targetId: string,
  axis: AlignmentAxis,
  planeValue: number,
  strength: number,
  distance: number,
  sourceBox: THREE.Box3,
  targetBox: THREE.Box3
): AlignmentGuide {
  // Calculate face position and size
  const sourceSize = new THREE.Vector3();
  const targetSize = new THREE.Vector3();
  sourceBox.getSize(sourceSize);
  targetBox.getSize(targetSize);

  const position = new THREE.Vector3();
  position[axis] = planeValue;

  // Set other axes to center between boxes
  const otherAxes = (['x', 'y', 'z'] as AlignmentAxis[]).filter((a) => a !== axis);
  for (const otherAxis of otherAxes) {
    position[otherAxis] = (sourceBox.min[otherAxis] + sourceBox.max[otherAxis] + targetBox.min[otherAxis] + targetBox.max[otherAxis]) / 4;
  }

  // Plane normal points along the aligned axis
  const planeNormal = new THREE.Vector3();
  planeNormal[axis] = 1;

  // Plane size based on the larger of the two parts
  const widthAxis = otherAxes[0];
  const heightAxis = otherAxes[1];
  const planeSize = {
    width: Math.max(sourceSize[widthAxis], targetSize[widthAxis]) * 1.2,
    height: Math.max(sourceSize[heightAxis], targetSize[heightAxis]) * 1.2,
  };

  return {
    id: `face-${sourceId}-${targetId}-${axis}`,
    type: 'face',
    sourcePartId: sourceId,
    targetPartId: targetId,
    axis,
    position,
    startPoint: position.clone(),
    endPoint: position.clone(),
    planeNormal,
    planeSize,
    strength,
    distance,
  };
}

/**
 * Calculate snap position based on active guides.
 */
function calculateSnapFromGuides(
  currentPosition: THREE.Vector3,
  guides: AlignmentGuide[],
  snapThreshold: number
): THREE.Vector3 | null {
  // Only snap if within hard threshold
  const validGuides = guides.filter((g) => g.distance <= snapThreshold);
  if (validGuides.length === 0) return null;

  const snappedPosition = currentPosition.clone();

  // Apply snaps per axis (use the closest guide per axis)
  const guidesByAxis: Record<AlignmentAxis, AlignmentGuide | null> = {
    x: null,
    y: null,
    z: null,
  };

  for (const guide of validGuides) {
    const current = guidesByAxis[guide.axis];
    if (!current || guide.distance < current.distance) {
      guidesByAxis[guide.axis] = guide;
    }
  }

  // Apply snaps
  for (const axis of ['x', 'y', 'z'] as AlignmentAxis[]) {
    const guide = guidesByAxis[axis]!;
    if (guide) {
      if (guide.type === 'center') {
        // Snap to target center
        const targetPart = guide.endPoint;
        snappedPosition[axis] = targetPart[axis];
      } else if (guide.type === 'edge') {
        // Calculate offset to align edges
        const delta = guide.distance;
        // This is simplified - actual edge snapping needs the original bounding box
        snappedPosition[axis] = currentPosition[axis] + (guide.startPoint[axis] < guide.endPoint[axis] ? delta : -delta);
      } else if (guide.type === 'face') {
        // Snap face to face
        snappedPosition[axis] = guide.position[axis];
      }
    }
  }

  return snappedPosition;
}

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook for calculating alignment guides between parts during drag.
 *
 * @param options - Configuration and state for alignment calculations.
 * @returns Alignment guides, snap position, and utility functions.
 *
 * @example
 * ```tsx
 * const { guides, snapPosition, hasActiveAlignment } = useAlignmentGuides({
 *   parts: assemblyParts,
 *   draggedPartId: selectedId,
 *   dragPosition: currentDragPos,
 *   hiddenParts: hiddenSet,
 *   settings: alignmentSettings,
 * });
 * ```
 */
export function useAlignmentGuides({
  parts,
  draggedPartId,
  dragPosition,
  hiddenParts,
  settings,
}: UseAlignmentGuidesOptions): UseAlignmentGuidesReturn {
  // Calculate guides based on current drag state
  const guides = useMemo(() => {
    // No guides if not dragging
    if (!draggedPartId || !dragPosition) return [];

    // Find the dragged part
    const sourcePart = parts.find((p) => p.id === draggedPartId);
    if (!sourcePart) return [];

    // Calculate source bounding box at drag position
    const sourceBox = sourcePart.boundingBox.clone();
    const offset = dragPosition.clone().sub(sourcePart.position);
    sourceBox.translate(offset);

    const allGuides: AlignmentGuide[] = [];

    // Calculate alignments with each visible part
    for (const targetPart of parts) {
      // Skip self and hidden parts
      if (targetPart.id === draggedPartId || hiddenParts.has(targetPart.id)) {
        continue;
      }

      // Center alignments
      if (settings.enableCenterAlignment) {
        allGuides.push(...calculateCenterAlignments(draggedPartId, dragPosition, targetPart, settings));
      }

      // Edge alignments
      if (settings.enableEdgeAlignment) {
        allGuides.push(...calculateEdgeAlignments(draggedPartId, sourceBox, targetPart, settings));
      }

      // Face alignments
      if (settings.enableFaceAlignment) {
        allGuides.push(...calculateFaceAlignments(draggedPartId, sourceBox, targetPart, settings));
      }
    }

    // Sort by distance and limit to maxGuides
    allGuides.sort((a, b) => a.distance - b.distance);
    return allGuides.slice(0, settings.maxGuides);
  }, [parts, draggedPartId, dragPosition, hiddenParts, settings]);

  // Calculate snap position
  const snapPosition = useMemo(() => {
    if (!dragPosition || guides.length === 0) return null;
    return calculateSnapFromGuides(dragPosition, guides, settings.snapThreshold);
  }, [dragPosition, guides, settings.snapThreshold]);

  // Whether any alignment is active
  const hasActiveAlignment = guides.length > 0;

  // Calculate final snap position on release
  const calculateSnapPosition = useCallback(
    (releasePosition: THREE.Vector3): THREE.Vector3 => {
      if (guides.length === 0) return releasePosition;
      const snapped = calculateSnapFromGuides(releasePosition, guides, settings.snapThreshold);
      return snapped ?? releasePosition;
    },
    [guides, settings.snapThreshold]
  );

  return {
    guides,
    snapPosition,
    hasActiveAlignment,
    calculateSnapPosition,
  };
}

export default useAlignmentGuides;
