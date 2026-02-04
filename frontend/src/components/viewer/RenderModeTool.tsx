/**
 * Render Modes for 3D viewer.
 *
 * Provides different visualization modes: shaded, wireframe,
 * transparent, hidden line, etc.
 */

import { useThree } from '@react-three/fiber';
import { 
  Eye, 
  Grid3X3, 
  Box, 
  Layers, 
  Square, 
  Palette 
} from 'lucide-react';
import { useState, useCallback, useEffect } from 'react';
import * as THREE from 'three';

export type RenderMode = 
  | 'shaded' 
  | 'wireframe' 
  | 'shaded-edges' 
  | 'transparent' 
  | 'hidden-line'
  | 'material';

export interface RenderModeConfig {
  mode: RenderMode;
  edgeColor: string;
  opacity: number;
  materialColor: string;
}

const RENDER_MODE_INFO: Record<RenderMode, { label: string; icon: typeof Eye; description: string }> = {
  shaded: {
    label: 'Shaded',
    icon: Box,
    description: 'Standard shaded view with lighting',
  },
  wireframe: {
    label: 'Wireframe',
    icon: Grid3X3,
    description: 'Show only edges as wireframe',
  },
  'shaded-edges': {
    label: 'Shaded + Edges',
    icon: Layers,
    description: 'Shaded view with visible edges',
  },
  transparent: {
    label: 'Transparent',
    icon: Square,
    description: 'Semi-transparent X-ray view',
  },
  'hidden-line': {
    label: 'Hidden Line',
    icon: Eye,
    description: 'White faces with black edges',
  },
  material: {
    label: 'Material',
    icon: Palette,
    description: 'Show material colors',
  },
};

interface RenderModeApplicatorProps {
  config: RenderModeConfig;
  originalMaterials: React.MutableRefObject<Map<THREE.Mesh, THREE.Material | THREE.Material[]>>;
}

/**
 * Component that applies render mode to the scene.
 */
export function RenderModeApplicator({ config, originalMaterials }: RenderModeApplicatorProps) {
  const { scene } = useThree();

  useEffect(() => {
    // Store original materials on first render
    if (originalMaterials.current.size === 0) {
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh && object.material) {
          originalMaterials.current.set(object, object.material);
        }
      });
    }

    // Apply render mode
    scene.traverse((object) => {
      if (object instanceof THREE.Mesh) {
        const originalMaterial = originalMaterials.current.get(object);
        if (!originalMaterial) return;

        // Remove existing edge lines
        const existingEdges = object.children.filter(
          (child) => child.userData.isEdgeLine
        );
        existingEdges.forEach((edge) => object.remove(edge));

        switch (config.mode) {
          case 'shaded': {
            // Restore original material
            if (Array.isArray(originalMaterial)) {
              object.material = originalMaterial.map((m) => m.clone());
            } else {
              object.material = originalMaterial.clone();
            }
            break;
          }

          case 'wireframe': {
            const wireMaterial = new THREE.MeshBasicMaterial({
              color: config.edgeColor,
              wireframe: true,
            });
            object.material = wireMaterial;
            break;
          }

          case 'shaded-edges': {
            // Restore original material
            if (Array.isArray(originalMaterial)) {
              object.material = originalMaterial.map((m) => m.clone());
            } else {
              object.material = originalMaterial.clone();
            }

            // Add edge lines
            if (object.geometry) {
              const edges = new THREE.EdgesGeometry(object.geometry, 15);
              const line = new THREE.LineSegments(
                edges,
                new THREE.LineBasicMaterial({ color: config.edgeColor })
              );
              line.userData.isEdgeLine = true;
              object.add(line);
            }
            break;
          }

          case 'transparent': {
            const transparentMaterial = new THREE.MeshStandardMaterial({
              color: config.materialColor,
              transparent: true,
              opacity: config.opacity,
              side: THREE.DoubleSide,
              depthWrite: false,
            });
            object.material = transparentMaterial;

            // Add subtle edges
            if (object.geometry) {
              const edges = new THREE.EdgesGeometry(object.geometry, 15);
              const line = new THREE.LineSegments(
                edges,
                new THREE.LineBasicMaterial({ 
                  color: config.edgeColor,
                  transparent: true,
                  opacity: 0.5,
                })
              );
              line.userData.isEdgeLine = true;
              object.add(line);
            }
            break;
          }

          case 'hidden-line': {
            const whiteMaterial = new THREE.MeshBasicMaterial({
              color: '#ffffff',
              side: THREE.FrontSide,
            });
            object.material = whiteMaterial;

            // Add black edges
            if (object.geometry) {
              const edges = new THREE.EdgesGeometry(object.geometry, 15);
              const line = new THREE.LineSegments(
                edges,
                new THREE.LineBasicMaterial({ color: '#000000' })
              );
              line.userData.isEdgeLine = true;
              object.add(line);
            }
            break;
          }

          case 'material': {
            // Use the configured material color
            const colorMaterial = new THREE.MeshStandardMaterial({
              color: config.materialColor,
              metalness: 0.3,
              roughness: 0.5,
            });
            object.material = colorMaterial;
            break;
          }
        }
      }
    });

    return () => {
      // Cleanup: restore original materials when component unmounts
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh) {
          const originalMaterial = originalMaterials.current.get(object);
          if (originalMaterial) {
            object.material = originalMaterial;
          }

          // Remove edge lines
          const existingEdges = object.children.filter(
            (child) => child.userData.isEdgeLine
          );
          existingEdges.forEach((edge) => object.remove(edge));
        }
      });
    };
  }, [config, scene, originalMaterials]);

  return null;
}

interface RenderModeToolbarProps {
  mode: RenderMode;
  onModeChange: (mode: RenderMode) => void;
  config: RenderModeConfig;
  onConfigChange: (updates: Partial<RenderModeConfig>) => void;
}

/**
 * UI toolbar for render mode controls.
 */
export function RenderModeToolbar({
  mode,
  onModeChange,
  config,
  onConfigChange,
}: RenderModeToolbarProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  return (
    <div className="flex flex-col gap-2 p-2 bg-white rounded-lg shadow-lg min-w-[160px]">
      <div className="text-xs font-medium text-gray-600 mb-1">Render Mode</div>
      
      {/* Mode buttons */}
      <div className="grid grid-cols-2 gap-1">
        {(Object.keys(RENDER_MODE_INFO) as RenderMode[]).map((m) => {
          const info = RENDER_MODE_INFO[m];
          const Icon = info.icon;
          const isActive = mode === m;

          return (
            <button
              key={m}
              onClick={() => onModeChange(m)}
              className={`flex items-center gap-1.5 px-2 py-1.5 text-xs rounded transition-colors ${
                isActive
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
              }`}
              title={info.description}
            >
              <Icon className="h-3 w-3" />
              <span className="truncate">{info.label}</span>
            </button>
          );
        })}
      </div>

      {/* Advanced settings toggle */}
      <button
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="text-xs text-gray-500 hover:text-gray-700 border-t pt-2"
      >
        {showAdvanced ? 'Hide' : 'Show'} advanced options
      </button>

      {/* Advanced settings */}
      {showAdvanced && (
        <div className="space-y-3 border-t pt-2">
          {/* Edge color */}
          <div className="space-y-1">
            <label className="text-[10px] text-gray-500 uppercase tracking-wide">
              Edge Color
            </label>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={config.edgeColor}
                onChange={(e) => onConfigChange({ edgeColor: e.target.value })}
                className="w-6 h-6 rounded cursor-pointer border"
              />
              <span className="text-xs text-gray-600">{config.edgeColor}</span>
            </div>
          </div>

          {/* Material color */}
          <div className="space-y-1">
            <label className="text-[10px] text-gray-500 uppercase tracking-wide">
              Material Color
            </label>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={config.materialColor}
                onChange={(e) => onConfigChange({ materialColor: e.target.value })}
                className="w-6 h-6 rounded cursor-pointer border"
              />
              <span className="text-xs text-gray-600">{config.materialColor}</span>
            </div>
          </div>

          {/* Opacity (for transparent mode) */}
          {mode === 'transparent' && (
            <div className="space-y-1">
              <label className="text-[10px] text-gray-500 uppercase tracking-wide">
                Opacity: {(config.opacity * 100).toFixed(0)}%
              </label>
              <input
                type="range"
                min="0.1"
                max="0.9"
                step="0.05"
                value={config.opacity}
                onChange={(e) => onConfigChange({ opacity: parseFloat(e.target.value) })}
                className="w-full h-1"
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Hook to manage render mode state.
 */
export function useRenderMode() {
  const [config, setConfig] = useState<RenderModeConfig>({
    mode: 'shaded',
    edgeColor: '#000000',
    opacity: 0.4,
    materialColor: '#3b82f6',
  });

  const setMode = useCallback((mode: RenderMode) => {
    setConfig((prev) => ({ ...prev, mode }));
  }, []);

  const updateConfig = useCallback((updates: Partial<RenderModeConfig>) => {
    setConfig((prev) => ({ ...prev, ...updates }));
  }, []);

  return {
    config,
    mode: config.mode,
    setMode,
    updateConfig,
  };
}

export default RenderModeToolbar;
