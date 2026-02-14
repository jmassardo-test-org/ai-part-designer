/**
 * AlignmentGuides Component
 *
 * Three.js component for rendering visual alignment guides during drag operations.
 * Renders edge, center, and face guides with appropriate colors and styles.
 */

import { Line, Plane } from '@react-three/drei';
import { useMemo } from 'react';
import * as THREE from 'three';
import type { AlignmentGuide } from '../../hooks/useAlignmentGuides';

// =============================================================================
// Types
// =============================================================================

export interface AlignmentGuidesProps {
  /** Array of alignment guides to render. */
  guides: AlignmentGuide[];
  /** Whether guides are visible. */
  visible: boolean;
  /** Optional fade opacity (0-1) for animation. */
  opacity?: number;
}

// =============================================================================
// Constants
// =============================================================================

/** Colors for different guide types. */
const GUIDE_COLORS = {
  edge: '#22c55e', // green-500
  center: '#3b82f6', // blue-500
  face: '#f59e0b', // amber-500
} as const;

/** Default opacity for guides. */
const DEFAULT_OPACITY = 0.8;

/** Line width for guides. */
const LINE_WIDTH = 2;

/** Extension length for edge/center guide lines. */
const LINE_EXTENSION = 20;

// =============================================================================
// Sub-components
// =============================================================================

interface EdgeGuideProps {
  guide: AlignmentGuide;
  opacity: number;
}

/**
 * Renders an edge alignment guide as a dashed line.
 */
function EdgeGuide({ guide, opacity }: EdgeGuideProps): JSX.Element {
  // Extend the line beyond the parts
  const direction = guide.endPoint.clone().sub(guide.startPoint).normalize();
  const extendedStart = guide.startPoint.clone().sub(direction.clone().multiplyScalar(LINE_EXTENSION));
  const extendedEnd = guide.endPoint.clone().add(direction.clone().multiplyScalar(LINE_EXTENSION));

  return (
    <Line
      points={[extendedStart, extendedEnd]}
      color={GUIDE_COLORS.edge}
      lineWidth={LINE_WIDTH}
      dashed
      dashSize={8}
      gapSize={4}
      opacity={opacity * guide.strength}
      transparent
    />
  );
}

interface CenterGuideProps {
  guide: AlignmentGuide;
  opacity: number;
}

/**
 * Renders a center alignment guide as a solid line with endpoint markers.
 */
function CenterGuide({ guide, opacity }: CenterGuideProps): JSX.Element {
  return (
    <group>
      {/* Main line */}
      <Line
        points={[guide.startPoint, guide.endPoint]}
        color={GUIDE_COLORS.center}
        lineWidth={LINE_WIDTH}
        opacity={opacity * guide.strength}
        transparent
      />

      {/* Start point marker */}
      <mesh position={guide.startPoint}>
        <sphereGeometry args={[2, 16, 16]} />
        <meshBasicMaterial
          color={GUIDE_COLORS.center}
          opacity={opacity * guide.strength}
          transparent
        />
      </mesh>

      {/* End point marker */}
      <mesh position={guide.endPoint}>
        <sphereGeometry args={[2, 16, 16]} />
        <meshBasicMaterial
          color={GUIDE_COLORS.center}
          opacity={opacity * guide.strength}
          transparent
        />
      </mesh>
    </group>
  );
}

interface FaceGuideProps {
  guide: AlignmentGuide;
  opacity: number;
}

/**
 * Renders a face alignment guide as a semi-transparent plane.
 */
function FaceGuide({ guide, opacity }: FaceGuideProps): JSX.Element {
  // Calculate rotation from normal
  const rotation = useMemo(() => {
    if (!guide.planeNormal) return new THREE.Euler();

    const up = new THREE.Vector3(0, 0, 1);
    const quaternion = new THREE.Quaternion().setFromUnitVectors(up, guide.planeNormal);
    return new THREE.Euler().setFromQuaternion(quaternion);
  }, [guide.planeNormal]);

  const planeWidth = guide.planeSize?.width ?? 50;
  const planeHeight = guide.planeSize?.height ?? 50;

  return (
    <group position={guide.position} rotation={rotation}>
      {/* Filled plane */}
      <Plane args={[planeWidth, planeHeight]}>
        <meshBasicMaterial
          color={GUIDE_COLORS.face}
          opacity={0.2 * guide.strength * opacity}
          transparent
          side={THREE.DoubleSide}
        />
      </Plane>

      {/* Border */}
      <Line
        points={[
          new THREE.Vector3(-planeWidth / 2, -planeHeight / 2, 0),
          new THREE.Vector3(planeWidth / 2, -planeHeight / 2, 0),
          new THREE.Vector3(planeWidth / 2, planeHeight / 2, 0),
          new THREE.Vector3(-planeWidth / 2, planeHeight / 2, 0),
          new THREE.Vector3(-planeWidth / 2, -planeHeight / 2, 0),
        ]}
        color={GUIDE_COLORS.face}
        lineWidth={LINE_WIDTH}
        opacity={0.6 * guide.strength * opacity}
        transparent
      />
    </group>
  );
}

// =============================================================================
// Main Component
// =============================================================================

/**
 * Renders alignment guides in Triple.js scene.
 *
 * Supports three types of guides:
 * - Edge guides: Dashed green lines showing edge alignment
 * - Center guides: Solid blue lines with sphere markers
 * - Face guides: Semi-transparent amber planes
 *
 * @example
 * ```tsx
 * <AlignmentGuides
 *   guides={alignmentGuides}
 *   visible={alignmentEnabled && isDragging}
 *   opacity={1}
 * />
 * ```
 */
export function AlignmentGuides({
  guides,
  visible,
  opacity = DEFAULT_OPACITY,
}: AlignmentGuidesProps): JSX.Element | null {
  if (!visible || guides.length === 0) {
    return null;
  }

  return (
    <group name="alignment-guides">
      {guides.map((guide) => {
        switch (guide.type) {
          case 'edge':
            return <EdgeGuide key={guide.id} guide={guide} opacity={opacity} />;
          case 'center':
            return <CenterGuide key={guide.id} guide={guide} opacity={opacity} />;
          case 'face':
            return <FaceGuide key={guide.id} guide={guide} opacity={opacity} />;
          default:
            return null;
        }
      })}
    </group>
  );
}

export default AlignmentGuides;
