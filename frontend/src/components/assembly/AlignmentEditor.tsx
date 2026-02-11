/**
 * AlignmentEditor Component
 *
 * Interactive editor for aligning multiple CAD parts.
 * Features preset alignment modes, gap controls, and 3D preview.
 */

import { OrbitControls, Environment, Grid, Html } from '@react-three/drei';
import { Canvas } from '@react-three/fiber';
import {
  Target,
  Crosshair,
  Layers,
  ArrowRight,
  ArrowUp,
  Square,
  AlignLeft,
  Loader2,
  Check,
  AlertCircle,
  Download,
  RotateCcw,
  Settings2,
} from 'lucide-react';
import { useState, useCallback, useMemo } from 'react';
import * as THREE from 'three';
import { STLLoader } from 'three-stdlib';
import { cn } from '@/lib/utils';
import {
  alignmentApi,
  AlignmentMode,
  AlignmentResponse,
  ALIGNMENT_PRESETS,
  TransformationInfo,
} from '@/lib/api/alignment';

// =============================================================================
// Types
// =============================================================================

interface AlignedPart {
  id: string;
  name: string;
  filePath: string;
  fileUrl?: string;
  color: string;
  transformation?: TransformationInfo;
}

interface AlignmentEditorProps {
  parts: AlignedPart[];
  onAlignmentComplete?: (response: AlignmentResponse) => void;
  onClose?: () => void;
  className?: string;
}

// =============================================================================
// Icon Map
// =============================================================================

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  target: Target,
  crosshair: Crosshair,
  layers: Layers,
  'arrow-right': ArrowRight,
  'arrow-up': ArrowUp,
  square: Square,
  'align-left': AlignLeft,
};

// =============================================================================
// AlignedPartMesh Component
// =============================================================================

interface AlignedPartMeshProps {
  part: AlignedPart;
  transformation?: TransformationInfo;
  showBounds: boolean;
}

function AlignedPartMesh({ part, transformation, showBounds }: AlignedPartMeshProps) {
  const [geometry, setGeometry] = useState<THREE.BufferGeometry | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load STL geometry
  useState(() => {
    if (!part.fileUrl) return;

    setIsLoading(true);
    const loader = new STLLoader();

    loader.load(
      part.fileUrl,
      (geo: THREE.BufferGeometry) => {
        geo.computeVertexNormals();
        geo.center();
        setGeometry(geo);
        setIsLoading(false);
      },
      undefined,
      () => {
        setError('Failed to load model');
        setIsLoading(false);
      }
    );
  });

  // Calculate position from transformation
  const position = useMemo(() => {
    if (transformation) {
      return new THREE.Vector3(
        transformation.applied_translation.x,
        transformation.applied_translation.y,
        transformation.applied_translation.z
      );
    }
    return new THREE.Vector3(0, 0, 0);
  }, [transformation]);

  // Create bounds box helper
  const boundsBox = useMemo(() => {
    if (!showBounds || !transformation) return null;

    const { final_bounds } = transformation;
    const size = new THREE.Vector3(
      final_bounds.max_x - final_bounds.min_x,
      final_bounds.max_y - final_bounds.min_y,
      final_bounds.max_z - final_bounds.min_z
    );
    const center = new THREE.Vector3(
      final_bounds.center_x,
      final_bounds.center_y,
      final_bounds.center_z
    );

    return { size, center };
  }, [showBounds, transformation]);

  if (isLoading) {
    return (
      <Html center position={position}>
        <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
      </Html>
    );
  }

  if (error || !geometry) {
    // Render placeholder cube
    return (
      <mesh position={position}>
        <boxGeometry args={[20, 20, 20]} />
        <meshStandardMaterial color={part.color} opacity={0.5} transparent />
      </mesh>
    );
  }

  return (
    <group position={position}>
      <mesh geometry={geometry} castShadow receiveShadow>
        <meshStandardMaterial
          color={part.color}
          metalness={0.3}
          roughness={0.5}
        />
      </mesh>
      {boundsBox && (
        <mesh position={boundsBox.center}>
          <boxGeometry args={[boundsBox.size.x, boundsBox.size.y, boundsBox.size.z]} />
          <meshBasicMaterial color={part.color} wireframe opacity={0.3} transparent />
        </mesh>
      )}
    </group>
  );
}

// =============================================================================
// AlignmentPreview3D Component
// =============================================================================

interface AlignmentPreview3DProps {
  parts: AlignedPart[];
  transformations: TransformationInfo[];
  showBounds: boolean;
  showGrid: boolean;
}

function AlignmentPreview3D({
  parts,
  transformations,
  showBounds,
  showGrid,
}: AlignmentPreview3DProps) {
  const transformationMap = useMemo(() => {
    const map = new Map<string, TransformationInfo>();
    transformations.forEach((t) => {
      map.set(t.file_path, t);
    });
    return map;
  }, [transformations]);

  return (
    <Canvas shadows camera={{ position: [150, 150, 150], fov: 45 }}>
      <ambientLight intensity={0.5} />
      <directionalLight
        position={[100, 100, 100]}
        intensity={1}
        castShadow
        shadow-mapSize={[2048, 2048]}
      />
      <directionalLight position={[-50, 50, -50]} intensity={0.3} />

      {showGrid && (
        <Grid
          position={[0, -0.1, 0]}
          args={[200, 200]}
          cellSize={10}
          cellThickness={0.5}
          cellColor="#6b7280"
          sectionSize={50}
          sectionThickness={1}
          sectionColor="#374151"
          fadeDistance={400}
          fadeStrength={1}
        />
      )}

      {parts.map((part) => (
        <AlignedPartMesh
          key={part.id}
          part={part}
          transformation={transformationMap.get(part.filePath)}
          showBounds={showBounds}
        />
      ))}

      <OrbitControls
        enablePan
        enableZoom
        enableRotate
        minDistance={50}
        maxDistance={500}
      />
      <Environment preset="studio" />
    </Canvas>
  );
}

// =============================================================================
// AlignmentEditor Component
// =============================================================================

export function AlignmentEditor({
  parts,
  onAlignmentComplete,
  onClose,
  className,
}: AlignmentEditorProps) {
  // State
  const [selectedMode, setSelectedMode] = useState<AlignmentMode>('CENTER');
  const [gap, setGap] = useState(0);
  const [referenceIndex, setReferenceIndex] = useState(0);
  const [isAligning, setIsAligning] = useState(false);
  const [alignmentResult, setAlignmentResult] = useState<AlignmentResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showBounds, setShowBounds] = useState(false);
  const [showGrid, setShowGrid] = useState(true);

  // File paths for API
  const filePaths = useMemo(() => parts.map((p) => p.filePath), [parts]);

  // Handle alignment
  const handleAlign = useCallback(async () => {
    if (filePaths.length < 2) {
      setError('At least 2 parts are required for alignment');
      return;
    }

    setIsAligning(true);
    setError(null);

    try {
      const response = await alignmentApi.align({
        file_paths: filePaths,
        mode: selectedMode,
        reference_index: referenceIndex,
        gap: gap,
      });

      setAlignmentResult(response);
      onAlignmentComplete?.(response);
    } catch (err) {
      console.error('Alignment failed:', err);
      setError(err instanceof Error ? err.message : 'Alignment failed');
    } finally {
      setIsAligning(false);
    }
  }, [filePaths, selectedMode, referenceIndex, gap, onAlignmentComplete]);

  // Reset alignment
  const handleReset = useCallback(() => {
    setAlignmentResult(null);
    setError(null);
  }, []);

  // Download result
  const handleDownload = useCallback(() => {
    if (!alignmentResult?.output_path) return;

    // Create download link
    const link = document.createElement('a');
    link.href = alignmentResult.output_path;
    link.download = 'aligned_assembly.step';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [alignmentResult]);

  return (
    <div className={cn('flex h-full flex-col bg-gray-900', className)}>
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-700 px-4 py-3">
        <h2 className="text-lg font-semibold text-white">Alignment Editor</h2>
        <div className="flex items-center gap-2">
          {alignmentResult && (
            <button
              onClick={handleDownload}
              className="flex items-center gap-2 rounded bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700"
            >
              <Download className="h-4 w-4" />
              Download
            </button>
          )}
          {onClose && (
            <button
              onClick={onClose}
              className="rounded px-3 py-1.5 text-sm text-gray-400 hover:bg-gray-800 hover:text-white"
            >
              Close
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar Controls */}
        <div className="w-72 flex-shrink-0 overflow-y-auto border-r border-gray-700 bg-gray-800 p-4">
          {/* Parts List */}
          <div className="mb-6">
            <h3 className="mb-3 text-sm font-medium text-gray-300">
              Parts ({parts.length})
            </h3>
            <div className="space-y-2">
              {parts.map((part, index) => (
                <div
                  key={part.id}
                  className={cn(
                    'flex items-center gap-2 rounded border px-3 py-2',
                    referenceIndex === index
                      ? 'border-blue-500 bg-blue-500/10'
                      : 'border-gray-600 bg-gray-700'
                  )}
                >
                  <div
                    className="h-3 w-3 rounded-full"
                    style={{ backgroundColor: part.color }}
                  />
                  <span className="flex-1 truncate text-sm text-white">
                    {part.name}
                  </span>
                  {referenceIndex === index && (
                    <span className="text-xs text-blue-400">Reference</span>
                  )}
                  <button
                    onClick={() => setReferenceIndex(index)}
                    className="text-xs text-gray-400 hover:text-white"
                    title="Set as reference"
                  >
                    <Target className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Alignment Mode */}
          <div className="mb-6">
            <h3 className="mb-3 text-sm font-medium text-gray-300">
              Alignment Mode
            </h3>
            <div className="grid grid-cols-2 gap-2">
              {ALIGNMENT_PRESETS.map((preset) => {
                const Icon = iconMap[preset.icon] || Target;
                return (
                  <button
                    key={preset.mode}
                    onClick={() => setSelectedMode(preset.mode)}
                    className={cn(
                      'flex flex-col items-center gap-1 rounded border p-3 text-center transition-colors',
                      selectedMode === preset.mode
                        ? 'border-blue-500 bg-blue-500/20 text-blue-400'
                        : 'border-gray-600 bg-gray-700 text-gray-300 hover:border-gray-500'
                    )}
                    title={preset.description}
                  >
                    <Icon className="h-5 w-5" />
                    <span className="text-xs">{preset.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Gap Control (for stacking modes) */}
          {selectedMode.startsWith('STACK') && (
            <div className="mb-6">
              <h3 className="mb-3 text-sm font-medium text-gray-300">
                Gap Between Parts
              </h3>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min="0"
                  max="50"
                  value={gap}
                  onChange={(e) => setGap(Number(e.target.value))}
                  className="flex-1"
                />
                <input
                  type="number"
                  value={gap}
                  onChange={(e) => setGap(Number(e.target.value))}
                  className="w-16 rounded border border-gray-600 bg-gray-700 px-2 py-1 text-sm text-white"
                  min="0"
                />
                <span className="text-xs text-gray-400">mm</span>
              </div>
            </div>
          )}

          {/* View Options */}
          <div className="mb-6">
            <h3 className="mb-3 flex items-center gap-2 text-sm font-medium text-gray-300">
              <Settings2 className="h-4 w-4" />
              View Options
            </h3>
            <div className="space-y-2">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={showGrid}
                  onChange={(e) => setShowGrid(e.target.checked)}
                  className="rounded border-gray-600"
                />
                <span className="text-sm text-gray-300">Show Grid</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={showBounds}
                  onChange={(e) => setShowBounds(e.target.checked)}
                  className="rounded border-gray-600"
                />
                <span className="text-sm text-gray-300">Show Bounding Boxes</span>
              </label>
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="mb-4 flex items-center gap-2 rounded bg-red-500/20 px-3 py-2 text-sm text-red-400">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              {error}
            </div>
          )}

          {/* Success Display */}
          {alignmentResult?.success && (
            <div className="mb-4 flex items-center gap-2 rounded bg-green-500/20 px-3 py-2 text-sm text-green-400">
              <Check className="h-4 w-4 flex-shrink-0" />
              {alignmentResult.message}
            </div>
          )}

          {/* Action Buttons */}
          <div className="space-y-2">
            <button
              onClick={handleAlign}
              disabled={isAligning || parts.length < 2}
              className={cn(
                'flex w-full items-center justify-center gap-2 rounded py-2.5 font-medium transition-colors',
                isAligning || parts.length < 2
                  ? 'cursor-not-allowed bg-gray-600 text-gray-400'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              )}
            >
              {isAligning ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Aligning...
                </>
              ) : (
                <>
                  <Layers className="h-4 w-4" />
                  Apply Alignment
                </>
              )}
            </button>

            {alignmentResult && (
              <button
                onClick={handleReset}
                className="flex w-full items-center justify-center gap-2 rounded border border-gray-600 py-2 text-sm text-gray-300 hover:bg-gray-700"
              >
                <RotateCcw className="h-4 w-4" />
                Reset
              </button>
            )}
          </div>
        </div>

        {/* 3D Preview */}
        <div className="flex-1 bg-gray-950">
          <AlignmentPreview3D
            parts={parts}
            transformations={alignmentResult?.transformations || []}
            showBounds={showBounds}
            showGrid={showGrid}
          />
        </div>
      </div>
    </div>
  );
}

export default AlignmentEditor;
