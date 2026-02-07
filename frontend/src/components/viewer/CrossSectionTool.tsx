/**
 * Cross-Section Tool for 3D viewer.
 *
 * Provides clipping planes to view internal geometry.
 */

import { useThree } from '@react-three/fiber';
import { Scissors, X, Eye, EyeOff } from 'lucide-react';
import { useState, useCallback, useRef, useEffect } from 'react';
import * as THREE from 'three';

export type ClipAxis = 'x' | 'y' | 'z';

export interface ClipPlane {
  id: string;
  axis: ClipAxis;
  position: number;
  enabled: boolean;
  inverted: boolean;
}

interface CrossSectionToolProps {
  /** Clipping planes to apply */
  clipPlanes: ClipPlane[];
  /** Whether to show plane helpers */
  showPlaneHelpers?: boolean;
  /** Color for the cross-section fill */
  sectionColor?: string;
}

interface ClipPlaneHelperProps {
  plane: ClipPlane;
  size: number;
  color: string;
}

/**
 * Generate a unique ID for clip planes.
 */
function generateId(): string {
  return `clip-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Visual helper for a clipping plane.
 */
function ClipPlaneHelper({ plane, size, color }: ClipPlaneHelperProps) {
  const meshRef = useRef<THREE.Mesh>(null);

  // Calculate rotation based on axis
  const rotation: [number, number, number] = 
    plane.axis === 'x' ? [0, Math.PI / 2, 0] :
    plane.axis === 'y' ? [Math.PI / 2, 0, 0] :
    [0, 0, 0];

  // Calculate position based on axis
  const position: [number, number, number] =
    plane.axis === 'x' ? [plane.position, 0, 0] :
    plane.axis === 'y' ? [0, plane.position, 0] :
    [0, 0, plane.position];

  if (!plane.enabled) return null;

  return (
    <mesh
      ref={meshRef}
      position={position}
      rotation={rotation}
    >
      <planeGeometry args={[size, size]} />
      <meshBasicMaterial
        color={color}
        transparent
        opacity={0.2}
        side={THREE.DoubleSide}
        depthWrite={false}
      />
    </mesh>
  );
}

/**
 * Component that applies clipping planes to the scene.
 */
function ClipPlaneApplicator({ clipPlanes }: { clipPlanes: ClipPlane[] }) {
  const { scene, gl } = useThree();
  const clippingPlanesRef = useRef<THREE.Plane[]>([]);

  useEffect(() => {
    // Enable local clipping
    gl.localClippingEnabled = true;

    // Create Three.js clipping planes
    const planes = clipPlanes
      .filter((cp) => cp.enabled)
      .map((cp) => {
        const normal = new THREE.Vector3(
          cp.axis === 'x' ? (cp.inverted ? -1 : 1) : 0,
          cp.axis === 'y' ? (cp.inverted ? -1 : 1) : 0,
          cp.axis === 'z' ? (cp.inverted ? -1 : 1) : 0
        );
        return new THREE.Plane(normal, -cp.position * (cp.inverted ? -1 : 1));
      });

    clippingPlanesRef.current = planes;

    // Apply clipping planes to all meshes in scene
    scene.traverse((object) => {
      if (object instanceof THREE.Mesh && object.material) {
        const materials = Array.isArray(object.material) 
          ? object.material 
          : [object.material];
        
        materials.forEach((material) => {
          if (material instanceof THREE.Material) {
            material.clippingPlanes = planes.length > 0 ? planes : null;
            material.clipShadows = true;
            material.needsUpdate = true;
          }
        });
      }
    });

    return () => {
      // Cleanup: remove clipping planes
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh && object.material) {
          const materials = Array.isArray(object.material) 
            ? object.material 
            : [object.material];
          
          materials.forEach((material) => {
            if (material instanceof THREE.Material) {
              material.clippingPlanes = null;
              material.needsUpdate = true;
            }
          });
        }
      });
    };
  }, [clipPlanes, scene, gl]);

  return null;
}

interface CrossSectionToolbarProps {
  enabled: boolean;
  onToggle: () => void;
  clipPlanes: ClipPlane[];
  onAddPlane: (axis: ClipAxis) => void;
  onRemovePlane: (id: string) => void;
  onUpdatePlane: (id: string, updates: Partial<ClipPlane>) => void;
  showHelpers: boolean;
  onToggleHelpers: () => void;
  bounds: { min: THREE.Vector3; max: THREE.Vector3 } | null;
}

/**
 * UI toolbar for cross-section controls.
 */
export function CrossSectionToolbar({
  enabled,
  onToggle,
  clipPlanes,
  onAddPlane,
  onRemovePlane,
  onUpdatePlane,
  showHelpers,
  onToggleHelpers,
  bounds,
}: CrossSectionToolbarProps) {
  const getRange = (axis: ClipAxis): { min: number; max: number } => {
    if (!bounds) return { min: -100, max: 100 };
    return {
      min: bounds.min[axis],
      max: bounds.max[axis],
    };
  };

  return (
    <div className="flex flex-col gap-2 p-2 bg-white rounded-lg shadow-lg min-w-[180px]">
      {/* Toggle button */}
      <div className="flex items-center justify-between">
        <button
          onClick={onToggle}
          className={`p-2 rounded-lg transition-colors ${
            enabled
              ? 'bg-blue-500 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
          title={enabled ? 'Disable cross-section' : 'Enable cross-section'}
        >
          <Scissors className="h-5 w-5" />
        </button>
        {enabled && (
          <button
            onClick={onToggleHelpers}
            className={`p-2 rounded-lg transition-colors ${
              showHelpers
                ? 'bg-blue-100 text-blue-600'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
            title={showHelpers ? 'Hide plane helpers' : 'Show plane helpers'}
          >
            {showHelpers ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
          </button>
        )}
      </div>

      {enabled && (
        <>
          {/* Add plane buttons */}
          <div className="flex gap-1 border-t pt-2">
            <button
              onClick={() => onAddPlane('x')}
              className="flex-1 px-2 py-1 text-xs bg-red-50 text-red-600 hover:bg-red-100 rounded"
              title="Add X plane"
            >
              X
            </button>
            <button
              onClick={() => onAddPlane('y')}
              className="flex-1 px-2 py-1 text-xs bg-green-50 text-green-600 hover:bg-green-100 rounded"
              title="Add Y plane"
            >
              Y
            </button>
            <button
              onClick={() => onAddPlane('z')}
              className="flex-1 px-2 py-1 text-xs bg-blue-50 text-blue-600 hover:bg-blue-100 rounded"
              title="Add Z plane"
            >
              Z
            </button>
          </div>

          {/* Clip planes list */}
          {clipPlanes.length > 0 && (
            <div className="border-t pt-2 space-y-2">
              {clipPlanes.map((plane) => {
                const range = getRange(plane.axis);
                const color =
                  plane.axis === 'x' ? 'text-red-600' :
                  plane.axis === 'y' ? 'text-green-600' :
                  'text-blue-600';

                return (
                  <div key={plane.id} className="space-y-1">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => onUpdatePlane(plane.id, { enabled: !plane.enabled })}
                          className={`p-1 rounded ${
                            plane.enabled ? 'bg-gray-100' : 'bg-gray-50 opacity-50'
                          }`}
                        >
                          {plane.enabled ? (
                            <Eye className="h-3 w-3 text-gray-600" />
                          ) : (
                            <EyeOff className="h-3 w-3 text-gray-400" />
                          )}
                        </button>
                        <span className={`text-xs font-medium ${color}`}>
                          {plane.axis.toUpperCase()} Plane
                        </span>
                      </div>
                      <button
                        onClick={() => onRemovePlane(plane.id)}
                        className="p-1 text-gray-400 hover:text-red-500 rounded"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                    
                    {plane.enabled && (
                      <div className="space-y-1">
                        <input
                          type="range"
                          min={range.min}
                          max={range.max}
                          step={(range.max - range.min) / 100}
                          value={plane.position}
                          onChange={(e) =>
                            onUpdatePlane(plane.id, { position: parseFloat(e.target.value) })
                          }
                          className="w-full h-1"
                        />
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] text-gray-400">
                            {plane.position.toFixed(1)}
                          </span>
                          <button
                            onClick={() =>
                              onUpdatePlane(plane.id, { inverted: !plane.inverted })
                            }
                            className={`text-[10px] px-1.5 py-0.5 rounded ${
                              plane.inverted
                                ? 'bg-orange-100 text-orange-600'
                                : 'bg-gray-100 text-gray-500'
                            }`}
                          >
                            {plane.inverted ? 'Inverted' : 'Normal'}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {clipPlanes.length === 0 && (
            <div className="text-xs text-gray-400 text-center py-2">
              Click X, Y, or Z to add a clipping plane
            </div>
          )}
        </>
      )}
    </div>
  );
}

/**
 * Hook to manage cross-section state.
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useCrossSection() {
  const [crossSectionEnabled, setCrossSectionEnabled] = useState(false);
  const [clipPlanes, setClipPlanes] = useState<ClipPlane[]>([]);
  const [showHelpers, setShowHelpers] = useState(true);
  const [bounds, setBounds] = useState<{ min: THREE.Vector3; max: THREE.Vector3 } | null>(null);

  const toggleCrossSection = useCallback(() => {
    setCrossSectionEnabled((prev) => !prev);
  }, []);

  const addClipPlane = useCallback((axis: ClipAxis) => {
    const defaultPosition = bounds ? (bounds.min[axis] + bounds.max[axis]) / 2 : 0;
    const newPlane: ClipPlane = {
      id: generateId(),
      axis,
      position: defaultPosition,
      enabled: true,
      inverted: false,
    };
    setClipPlanes((prev) => [...prev, newPlane]);
  }, [bounds]);

  const removeClipPlane = useCallback((id: string) => {
    setClipPlanes((prev) => prev.filter((p) => p.id !== id));
  }, []);

  const updateClipPlane = useCallback((id: string, updates: Partial<ClipPlane>) => {
    setClipPlanes((prev) =>
      prev.map((p) => (p.id === id ? { ...p, ...updates } : p))
    );
  }, []);

  const toggleHelpers = useCallback(() => {
    setShowHelpers((prev) => !prev);
  }, []);

  const updateBounds = useCallback((min: THREE.Vector3, max: THREE.Vector3) => {
    setBounds({ min, max });
  }, []);

  return {
    crossSectionEnabled,
    clipPlanes,
    showHelpers,
    bounds,
    toggleCrossSection,
    addClipPlane,
    removeClipPlane,
    updateClipPlane,
    toggleHelpers,
    updateBounds,
  };
}

/**
 * Cross-section overlay component for the 3D scene.
 */
export function CrossSectionOverlay({
  clipPlanes,
  showPlaneHelpers = true,
  // sectionColor reserved for future use with stencil rendering
}: CrossSectionToolProps) {
  const { scene } = useThree();
  const [size, setSize] = useState(200);

  // Calculate size based on scene bounds
  useEffect(() => {
    const box = new THREE.Box3().setFromObject(scene);
    const sceneSize = new THREE.Vector3();
    box.getSize(sceneSize);
    setSize(Math.max(sceneSize.x, sceneSize.y, sceneSize.z) * 1.5);
  }, [scene]);

  return (
    <group>
      {/* Apply clipping planes */}
      <ClipPlaneApplicator clipPlanes={clipPlanes} />

      {/* Plane helpers */}
      {showPlaneHelpers &&
        clipPlanes.map((plane) => (
          <ClipPlaneHelper
            key={plane.id}
            plane={plane}
            size={size}
            color={
              plane.axis === 'x' ? '#ef4444' :
              plane.axis === 'y' ? '#22c55e' :
              '#3b82f6'
            }
          />
        ))}
    </group>
  );
}

export default CrossSectionToolbar;
