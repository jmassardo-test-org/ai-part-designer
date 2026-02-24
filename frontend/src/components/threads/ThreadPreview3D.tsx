/**
 * ThreadPreview3D component.
 *
 * Renders a parametric 3D visualization of a thread specification using
 * React Three Fiber. Shows external threads as a cylinder with torus-ring
 * groove indicators at each pitch interval, and internal threads as a
 * hollow tube representing the bore. Dimension annotations are displayed
 * using drei's Html overlay.
 */

import { Center, Grid, Html, OrbitControls } from '@react-three/drei';
import { Canvas } from '@react-three/fiber';
import { Suspense, useMemo } from 'react';
import * as THREE from 'three';
import type { ThreadSpec } from '@/types/threads';
import { isWebGLAvailable } from '@/utils/webgl';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

/** Props for the {@link ThreadPreview3D} component. */
export interface ThreadPreview3DProps {
  /** Thread specification to visualise. `null` shows a placeholder. */
  spec: ThreadSpec | null;
  /** Whether to render an internal or external thread. */
  threadType: 'internal' | 'external';
  /** Axial length of the thread in millimetres. */
  lengthMm: number;
  /** Optional CSS class applied to the outermost container. */
  className?: string;
}

// ---------------------------------------------------------------------------
// Shared material
// ---------------------------------------------------------------------------

/** Re-usable metallic material for the thread body. */
const THREAD_MATERIAL_PROPS = {
  color: '#a8b4c0',
  metalness: 0.85,
  roughness: 0.25,
} as const;

/** Slightly darker variant for groove rings. */
const GROOVE_MATERIAL_PROPS = {
  color: '#8694a2',
  metalness: 0.9,
  roughness: 0.2,
} as const;

// ---------------------------------------------------------------------------
// Scale helper
// ---------------------------------------------------------------------------

/**
 * Compute a uniform scale factor so the preview fills the viewport
 * regardless of the physical thread dimensions.
 *
 * The target visible size is approximately 6 "scene units".
 */
function computeScaleFactor(majorDiameter: number, length: number): number {
  const maxDim = Math.max(majorDiameter, length, 0.001);
  return 6 / maxDim;
}

// ---------------------------------------------------------------------------
// Sub-components rendered inside <Canvas>
// ---------------------------------------------------------------------------

/** Loading indicator shown while the scene suspense resolves. */
function LoadingIndicator() {
  return (
    <Html center>
      <div className="text-xs text-gray-500 select-none">Loading…</div>
    </Html>
  );
}

// ---------------------------------------------------------------------------
// Dimension annotations
// ---------------------------------------------------------------------------

interface AnnotationProps {
  position: [number, number, number];
  label: string;
  value: string;
}

/**
 * A small HTML overlay label anchored to a 3D position.
 */
function DimensionAnnotation({ position, label, value }: AnnotationProps) {
  return (
    <Html position={position} center distanceFactor={12}>
      <div className="pointer-events-none select-none whitespace-nowrap rounded bg-gray-900/80 px-1.5 py-0.5 text-[10px] leading-tight text-white shadow">
        <span className="font-medium">{label}:</span> {value}
      </div>
    </Html>
  );
}

// ---------------------------------------------------------------------------
// External thread mesh
// ---------------------------------------------------------------------------

interface ThreadMeshProps {
  spec: ThreadSpec;
  lengthMm: number;
  scale: number;
}

/**
 * External thread — cylinder body with torus-ring grooves at each pitch.
 */
function ExternalThreadMesh({ spec, lengthMm, scale }: ThreadMeshProps) {
  const radius = (spec.major_diameter / 2) * scale;
  const height = lengthMm * scale;
  const pitch = spec.pitch_mm * scale;
  const grooveRadius = radius * 0.06; // visual size of the groove ring

  const grooves = useMemo(() => {
    const items: number[] = [];
    if (pitch <= 0) return items;
    // Place a torus at every pitch interval along the length
    const count = Math.floor(height / pitch);
    for (let i = 1; i <= count; i++) {
      items.push(-height / 2 + i * pitch);
    }
    return items;
  }, [height, pitch]);

  return (
    <group>
      {/* Main cylinder body */}
      <mesh castShadow receiveShadow>
        <cylinderGeometry args={[radius, radius, height, 48]} />
        <meshStandardMaterial {...THREAD_MATERIAL_PROPS} />
      </mesh>

      {/* Groove rings */}
      {grooves.map((y, idx) => (
        <mesh key={idx} rotation={[Math.PI / 2, 0, 0]} position={[0, y, 0]}>
          <torusGeometry args={[radius, grooveRadius, 12, 64]} />
          <meshStandardMaterial {...GROOVE_MATERIAL_PROPS} />
        </mesh>
      ))}

      {/* Annotations */}
      <DimensionAnnotation
        position={[radius + 0.8, 0, 0]}
        label="⌀ Major"
        value={`${spec.major_diameter.toFixed(2)} mm`}
      />
      <DimensionAnnotation
        position={[0, height / 2 + 0.6, 0]}
        label="Length"
        value={`${lengthMm.toFixed(1)} mm`}
      />
      <DimensionAnnotation
        position={[-(radius + 0.8), -height / 2 + pitch, 0]}
        label="Pitch"
        value={`${spec.pitch_mm.toFixed(2)} mm`}
      />
    </group>
  );
}

// ---------------------------------------------------------------------------
// Internal thread mesh
// ---------------------------------------------------------------------------

/**
 * Internal thread — hollow cylinder (tube) representing the bore.
 */
function InternalThreadMesh({ spec, lengthMm, scale }: ThreadMeshProps) {
  const outerRadius = (spec.major_diameter / 2) * scale;
  const innerRadius = (spec.minor_diameter_ext / 2) * scale;
  const height = lengthMm * scale;
  const wallThickness = outerRadius - innerRadius;

  // Use a lathe-style geometry via a tube for the hollow cylinder
  const tubeShape = useMemo(() => {
    const shape = new THREE.Shape();
    shape.moveTo(innerRadius, -height / 2);
    shape.lineTo(outerRadius, -height / 2);
    shape.lineTo(outerRadius, height / 2);
    shape.lineTo(innerRadius, height / 2);
    shape.lineTo(innerRadius, -height / 2);
    return shape;
  }, [innerRadius, outerRadius, height]);

  return (
    <group>
      {/* Hollow cylinder via lathe of a rectangular cross-section */}
      <mesh castShadow receiveShadow>
        <latheGeometry args={[tubeShape.getPoints(1), 64]} />
        <meshStandardMaterial
          {...THREAD_MATERIAL_PROPS}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Visual chamfer ring at each end */}
      {[-height / 2, height / 2].map((y, idx) => (
        <mesh key={idx} rotation={[Math.PI / 2, 0, 0]} position={[0, y, 0]}>
          <ringGeometry args={[innerRadius - 0.02, innerRadius + wallThickness * 0.15, 64]} />
          <meshStandardMaterial color="#6b7a88" metalness={0.8} roughness={0.3} side={THREE.DoubleSide} />
        </mesh>
      ))}

      {/* Annotations */}
      <DimensionAnnotation
        position={[outerRadius + 0.8, 0, 0]}
        label="⌀ Major"
        value={`${spec.major_diameter.toFixed(2)} mm`}
      />
      <DimensionAnnotation
        position={[-(outerRadius + 0.8), 0, 0]}
        label="⌀ Minor"
        value={`${spec.minor_diameter_ext.toFixed(2)} mm`}
      />
      <DimensionAnnotation
        position={[0, height / 2 + 0.6, 0]}
        label="Length"
        value={`${lengthMm.toFixed(1)} mm`}
      />
      <DimensionAnnotation
        position={[0, -(height / 2 + 0.6), 0]}
        label="Pitch"
        value={`${spec.pitch_mm.toFixed(2)} mm`}
      />
    </group>
  );
}

// ---------------------------------------------------------------------------
// Scene wrapper
// ---------------------------------------------------------------------------

interface ThreadSceneProps {
  spec: ThreadSpec;
  threadType: 'internal' | 'external';
  lengthMm: number;
}

/**
 * The full 3D scene containing lights, controls, grid, and the thread mesh.
 */
function ThreadScene({ spec, threadType, lengthMm }: ThreadSceneProps) {
  const scale = computeScaleFactor(spec.major_diameter, lengthMm);

  return (
    <>
      {/* Lighting */}
      <ambientLight intensity={0.4} />
      <directionalLight
        position={[10, 10, 5]}
        intensity={0.6}
        castShadow
        shadow-mapSize={[512, 512]}
      />
      <directionalLight position={[-8, 6, -4]} intensity={0.3} />

      {/* Controls */}
      <OrbitControls makeDefault enableDamping dampingFactor={0.12} />

      {/* Thread mesh */}
      <Center>
        {threadType === 'external' ? (
          <ExternalThreadMesh spec={spec} lengthMm={lengthMm} scale={scale} />
        ) : (
          <InternalThreadMesh spec={spec} lengthMm={lengthMm} scale={scale} />
        )}
      </Center>

      {/* Reference grid */}
      <Grid
        args={[20, 20]}
        cellSize={1}
        cellThickness={0.4}
        cellColor="#e5e7eb"
        sectionSize={5}
        sectionThickness={0.8}
        sectionColor="#9ca3af"
        fadeDistance={30}
        fadeStrength={1}
        followCamera={false}
        infiniteGrid
      />
    </>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

/**
 * Parametric 3D preview of a thread specification.
 *
 * Renders an external thread as a cylinder with torus-ring grooves or an
 * internal thread as a hollow bore, sized from the provided `ThreadSpec`.
 * Includes interactive orbit controls, a reference grid, and dimension
 * annotations.
 *
 * Falls back to a static message when WebGL is unavailable or when no spec
 * is provided.
 *
 * @example
 * ```tsx
 * <ThreadPreview3D
 *   spec={selectedSpec}
 *   threadType="external"
 *   lengthMm={20}
 *   className="h-64"
 * />
 * ```
 */
export function ThreadPreview3D({
  spec,
  threadType,
  lengthMm,
  className,
}: ThreadPreview3DProps) {
  // --- WebGL guard --------------------------------------------------------
  if (!isWebGLAvailable()) {
    return (
      <div
        data-testid="thread-preview-no-webgl"
        className={`flex items-center justify-center rounded-lg border border-gray-200 bg-gray-50 p-6 text-center text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400 ${className ?? ''}`}
      >
        3D preview requires WebGL support. Please use a modern browser.
      </div>
    );
  }

  // --- Placeholder when no spec -------------------------------------------
  if (!spec) {
    return (
      <div
        data-testid="thread-preview-3d"
        className={`flex items-center justify-center rounded-lg border border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800 ${className ?? ''}`}
      >
        <p
          data-testid="thread-preview-placeholder"
          className="text-sm text-gray-400 dark:text-gray-500"
        >
          Select a thread to preview
        </p>
      </div>
    );
  }

  // --- 3D canvas ----------------------------------------------------------
  return (
    <div
      data-testid="thread-preview-3d"
      className={`relative overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700 ${className ?? ''}`}
    >
      <Canvas
        data-testid="thread-preview-canvas"
        shadows
        dpr={[1, 2]}
        camera={{ position: [8, 8, 8], fov: 50 }}
        style={{ width: '100%', height: '100%', background: '#f8fafc' }}
      >
        <Suspense fallback={<LoadingIndicator />}>
          <ThreadScene spec={spec} threadType={threadType} lengthMm={lengthMm} />
        </Suspense>
      </Canvas>

      {/* Info badge */}
      <div className="pointer-events-none absolute bottom-2 left-2 flex items-center gap-1.5 rounded bg-gray-900/70 px-2 py-1 text-[10px] text-white">
        <span className="font-medium">{spec.family.toUpperCase()}</span>
        <span className="opacity-70">|</span>
        <span>{spec.size}</span>
        <span className="opacity-70">|</span>
        <span className="capitalize">{threadType}</span>
      </div>
    </div>
  );
}

export default ThreadPreview3D;
