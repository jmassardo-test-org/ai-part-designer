/**
 * Part Transform Controls Component
 * 
 * Provides interactive transform controls (move/rotate) for selected parts
 * with position and rotation snapping.
 */

import { TransformControls } from '@react-three/drei';
import { useThree } from '@react-three/fiber';
import { useEffect, useRef, useCallback } from 'react';
import * as THREE from 'three';
import type { TransformControls as TransformControlsImpl } from 'three-stdlib';

// =============================================================================
// Types
// =============================================================================

export type TransformMode = 'translate' | 'rotate' | 'scale';

export interface PartTransform {
  position: { x: number; y: number; z: number };
  rotation: { rx: number; ry: number; rz: number };
  scale: { sx: number; sy: number; sz: number };
}

export interface PartTransformControlsProps {
  /** The mesh or object to transform */
  object?: THREE.Object3D | null;
  /** Transform mode (translate, rotate, scale) */
  mode?: TransformMode;
  /** Enable position snapping */
  enablePositionSnap?: boolean;
  /** Position snap increment in world units */
  positionSnapIncrement?: number;
  /** Enable rotation snapping */
  enableRotationSnap?: boolean;
  /** Rotation snap increment in degrees */
  rotationSnapIncrement?: number;
  /** Callback when transform changes */
  onTransformChange?: (transform: PartTransform) => void;
  /** Callback when transform ends */
  onTransformEnd?: (transform: PartTransform) => void;
  /** Callback when dragging state changes */
  onDraggingChange?: (isDragging: boolean) => void;
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Snap a value to the nearest increment.
 */
function snapValue(value: number, increment: number): number {
  return Math.round(value / increment) * increment;
}

/**
 * Extract transform data from an object.
 */
function getTransformFromObject(object: THREE.Object3D): PartTransform {
  return {
    position: {
      x: object.position.x,
      y: object.position.y,
      z: object.position.z,
    },
    rotation: {
      rx: THREE.MathUtils.radToDeg(object.rotation.x),
      ry: THREE.MathUtils.radToDeg(object.rotation.y),
      rz: THREE.MathUtils.radToDeg(object.rotation.z),
    },
    scale: {
      sx: object.scale.x,
      sy: object.scale.y,
      sz: object.scale.z,
    },
  };
}

// =============================================================================
// Component
// =============================================================================

export function PartTransformControls({
  object,
  mode = 'translate',
  enablePositionSnap = true,
  positionSnapIncrement = 5,
  enableRotationSnap = true,
  rotationSnapIncrement = 15,
  onTransformChange,
  onTransformEnd,
  onDraggingChange,
}: PartTransformControlsProps) {
  const controlsRef = useRef<TransformControlsImpl>(null);
  const { gl, camera } = useThree();

  // Track last snapped values to avoid redundant snapping
  const lastSnappedValues = useRef<{
    position: THREE.Vector3;
    rotation: THREE.Euler;
  } | null>(null);

  // Handle transform change with snapping
  const handleChange = useCallback(() => {
    if (!object || !controlsRef.current) return;

    // Apply snapping based on mode
    if (mode === 'translate' && enablePositionSnap) {
      const pos = object.position;
      const snappedX = snapValue(pos.x, positionSnapIncrement);
      const snappedY = snapValue(pos.y, positionSnapIncrement);
      const snappedZ = snapValue(pos.z, positionSnapIncrement);

      // Only update if values changed to avoid infinite loops
      const lastPos = lastSnappedValues.current?.position;
      if (
        !lastPos ||
        Math.abs(lastPos.x - snappedX) > 0.001 ||
        Math.abs(lastPos.y - snappedY) > 0.001 ||
        Math.abs(lastPos.z - snappedZ) > 0.001
      ) {
        object.position.set(snappedX, snappedY, snappedZ);
        lastSnappedValues.current = {
          position: object.position.clone(),
          rotation: object.rotation.clone(),
        };
      }
    } else if (mode === 'rotate' && enableRotationSnap) {
      const rot = object.rotation;
      const snapRad = THREE.MathUtils.degToRad(rotationSnapIncrement);
      const snappedX = snapValue(rot.x, snapRad);
      const snappedY = snapValue(rot.y, snapRad);
      const snappedZ = snapValue(rot.z, snapRad);

      // Only update if values changed
      const lastRot = lastSnappedValues.current?.rotation;
      if (
        !lastRot ||
        Math.abs(lastRot.x - snappedX) > 0.001 ||
        Math.abs(lastRot.y - snappedY) > 0.001 ||
        Math.abs(lastRot.z - snappedZ) > 0.001
      ) {
        object.rotation.set(snappedX, snappedY, snappedZ);
        lastSnappedValues.current = {
          position: object.position.clone(),
          rotation: object.rotation.clone(),
        };
      }
    }

    // Notify parent of change
    if (onTransformChange) {
      const transform = getTransformFromObject(object);
      onTransformChange(transform);
    }
  }, [
    object,
    mode,
    enablePositionSnap,
    positionSnapIncrement,
    enableRotationSnap,
    rotationSnapIncrement,
    onTransformChange,
  ]);

  // Handle drag start
  const handleDragStart = useCallback(() => {
    if (object) {
      lastSnappedValues.current = {
        position: object.position.clone(),
        rotation: object.rotation.clone(),
      };
    }
    onDraggingChange?.(true);
  }, [object, onDraggingChange]);

  // Handle drag end
  const handleDragEnd = useCallback(() => {
    onDraggingChange?.(false);
    if (object && onTransformEnd) {
      const transform = getTransformFromObject(object);
      onTransformEnd(transform);
    }
  }, [object, onTransformEnd, onDraggingChange]);

  // Setup event listeners
  useEffect(() => {
    const controls = controlsRef.current;
    if (!controls) return;

    controls.addEventListener('change', handleChange);
    controls.addEventListener('dragging-changed', (event) => {
      const isDragging = (event as unknown as { value: boolean }).value;
      if (isDragging) {
        handleDragStart();
      } else {
        handleDragEnd();
      }
    });

    return () => {
      controls.removeEventListener('change', handleChange);
    };
  }, [handleChange, handleDragStart, handleDragEnd]);

  // Disable orbit controls while dragging
  useEffect(() => {
    const controls = controlsRef.current;
    if (!controls) return;

    const handleDraggingChanged = (event: Event) => {
      const isDragging = (event as unknown as { value: boolean }).value;
      // Find orbit controls in the scene
      gl.domElement.style.cursor = isDragging ? 'move' : 'default';
    };

    // @ts-expect-error - three.js event type compatibility
    controls.addEventListener('dragging-changed', handleDraggingChanged);

    return () => {
      // @ts-expect-error - three.js event type compatibility
      controls.removeEventListener('dragging-changed', handleDraggingChanged);
    };
  }, [gl.domElement]);

  if (!object) return null;

  const transformProps: any = {
    ref: controlsRef,
    object,
    mode,
    camera,
    gl,
    showX: true,
    showY: true,
    showZ: true,
    size: 0.8,
    space: 'world',
  };

  return (
    <TransformControls
      {...transformProps}
    />
  );
}

export default PartTransformControls;
