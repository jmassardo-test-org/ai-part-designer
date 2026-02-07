/**
 * Assembly Viewer Component
 * 
 * 3D viewer for assemblies with multi-component support,
 * exploded view, and component selection.
 */

import { OrbitControls, PerspectiveCamera, Environment, Html } from '@react-three/drei';
import { Canvas, useThree } from '@react-three/fiber';
import {
  Expand,
  Shrink,
  Eye,
  EyeOff,
  RotateCcw,
  List,
} from 'lucide-react';
import { useRef, useState, useEffect, useCallback, useMemo } from 'react';
import * as THREE from 'three';
import { STLLoader, OrbitControls as OrbitControlsImpl } from 'three-stdlib';

// =============================================================================
// Types
// =============================================================================

interface Position {
  x: number;
  y: number;
  z: number;
}

interface Rotation {
  rx: number;
  ry: number;
  rz: number;
}

interface Scale {
  sx: number;
  sy: number;
  sz: number;
}

interface AssemblyComponent {
  id: string;
  name: string;
  design_id?: string;
  quantity: number;
  position: Position;
  rotation: Rotation;
  scale: Scale;
  is_cots: boolean;
  color?: string;
  file_url?: string;
  thumbnail_url?: string;
}

interface AssemblyViewerProps {
  components: AssemblyComponent[];
  selectedComponentId?: string | null;
  onSelectComponent?: (componentId: string | null) => void;
  explodedView?: boolean;
  explodeFactor?: number;
  hiddenComponents?: Set<string>;
  className?: string;
}

// =============================================================================
// Component Mesh
// =============================================================================

interface ComponentMeshProps {
  component: AssemblyComponent;
  isSelected: boolean;
  isHidden: boolean;
  explodeFactor: number;
  assemblyCenter: THREE.Vector3;
  onClick: () => void;
}

function ComponentMesh({
  component,
  isSelected,
  isHidden,
  explodeFactor,
  assemblyCenter,
  onClick,
}: ComponentMeshProps) {
  const meshRef = useRef<THREE.Mesh>(null);
  const [geometry, setGeometry] = useState<THREE.BufferGeometry | null>(null);
  const [, setIsLoading] = useState(false);
  const [, setError] = useState<string | null>(null);

  // Load STL if file_url provided
  useEffect(() => {
    if (!component.file_url) {
      // Create placeholder geometry
      const placeholder = new THREE.BoxGeometry(20, 20, 20);
      setGeometry(placeholder);
      return;
    }

    setIsLoading(true);
    setError(null);

    const loader = new STLLoader();
    loader.load(
      component.file_url,
      (geo: THREE.BufferGeometry) => {
        geo.computeVertexNormals();
        geo.center();
        setGeometry(geo);
        setIsLoading(false);
      },
      undefined,
      (err: unknown) => {
        console.error('Failed to load STL:', err);
        setError('Failed to load model');
        setIsLoading(false);
        // Use placeholder
        const placeholder = new THREE.BoxGeometry(20, 20, 20);
        setGeometry(placeholder);
      }
    );

    return () => {
      geometry?.dispose();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [component.file_url]);

  // Calculate exploded position
  const explodedPosition = useMemo(() => {
    const basePos = new THREE.Vector3(
      component.position.x,
      component.position.y,
      component.position.z
    );

    if (explodeFactor > 0) {
      const direction = basePos.clone().sub(assemblyCenter).normalize();
      const explodeDistance = explodeFactor * 50; // Adjust multiplier as needed
      return basePos.add(direction.multiplyScalar(explodeDistance));
    }

    return basePos;
  }, [component.position, explodeFactor, assemblyCenter]);

  // Rotation in radians
  const rotationEuler = useMemo(
    () =>
      new THREE.Euler(
        THREE.MathUtils.degToRad(component.rotation.rx),
        THREE.MathUtils.degToRad(component.rotation.ry),
        THREE.MathUtils.degToRad(component.rotation.rz)
      ),
    [component.rotation]
  );

  // Material color
  const materialColor = useMemo(() => {
    if (isSelected) return '#3b82f6'; // Blue for selected
    if (component.color) return component.color;
    if (component.is_cots) return '#9ca3af'; // Gray for COTS
    return '#6b7280'; // Default gray
  }, [isSelected, component.color, component.is_cots]);

  if (isHidden || !geometry) return null;

  return (
    <mesh
      ref={meshRef}
      geometry={geometry}
      position={explodedPosition}
      rotation={rotationEuler}
      scale={[component.scale.sx, component.scale.sy, component.scale.sz]}
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      onPointerOver={() => {
        document.body.style.cursor = 'pointer';
      }}
      onPointerOut={() => {
        document.body.style.cursor = 'default';
      }}
    >
      <meshStandardMaterial
        color={materialColor}
        metalness={0.3}
        roughness={0.7}
        transparent={isSelected}
        opacity={isSelected ? 0.9 : 1}
      />
      
      {/* Selection outline */}
      {isSelected && (
        <lineSegments>
          <edgesGeometry args={[geometry]} />
          <lineBasicMaterial color="#1d4ed8" linewidth={2} />
        </lineSegments>
      )}

      {/* Component label on hover */}
      {isSelected && (
        <Html
          position={[0, 15, 0]}
          center
          style={{ pointerEvents: 'none' }}
        >
          <div className="bg-gray-900 text-white text-xs px-2 py-1 rounded shadow-lg whitespace-nowrap">
            {component.name}
            {component.quantity > 1 && ` (×${component.quantity})`}
          </div>
        </Html>
      )}
    </mesh>
  );
}

// =============================================================================
// Scene Component
// =============================================================================

interface AssemblySceneProps {
  components: AssemblyComponent[];
  selectedComponentId: string | null;
  onSelectComponent: (componentId: string | null) => void;
  explodeFactor: number;
  hiddenComponents: Set<string>;
}

function AssemblyScene({
  components,
  selectedComponentId,
  onSelectComponent,
  explodeFactor,
  hiddenComponents,
}: AssemblySceneProps) {
  useThree();

  // Calculate assembly center
  const assemblyCenter = useMemo(() => {
    if (components.length === 0) return new THREE.Vector3();

    const center = new THREE.Vector3();
    components.forEach((c) => {
      center.add(new THREE.Vector3(c.position.x, c.position.y, c.position.z));
    });
    center.divideScalar(components.length);
    return center;
  }, [components]);

  // Click on empty space deselects
  const handleBackgroundClick = useCallback(() => {
    onSelectComponent(null);
  }, [onSelectComponent]);

  return (
    <>
      {/* Lighting */}
      <ambientLight intensity={0.4} />
      <directionalLight position={[10, 10, 5]} intensity={0.8} castShadow />
      <directionalLight position={[-10, -10, -5]} intensity={0.3} />

      {/* Environment */}
      <Environment preset="studio" />

      {/* Ground plane (click to deselect) */}
      <mesh
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, -50, 0]}
        onClick={handleBackgroundClick}
        visible={false}
      >
        <planeGeometry args={[1000, 1000]} />
        <meshBasicMaterial transparent opacity={0} />
      </mesh>

      {/* Grid helper */}
      <gridHelper args={[200, 20, '#d1d5db', '#e5e7eb']} position={[0, -50, 0]} />

      {/* Components */}
      {components.map((component) => (
        <ComponentMesh
          key={component.id}
          component={component}
          isSelected={selectedComponentId === component.id}
          isHidden={hiddenComponents.has(component.id)}
          explodeFactor={explodeFactor}
          assemblyCenter={assemblyCenter}
          onClick={() => onSelectComponent(component.id)}
        />
      ))}
    </>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function AssemblyViewer({
  components,
  selectedComponentId = null,
  onSelectComponent,
  explodedView: _explodedView = false,
  explodeFactor: externalExplodeFactor,
  hiddenComponents: externalHiddenComponents,
  className = '',
}: AssemblyViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const controlsRef = useRef<OrbitControlsImpl>(null);

  // Local state (can be overridden by props)
  const [localExplodeFactor, setLocalExplodeFactor] = useState(0);
  const [localHiddenComponents, setLocalHiddenComponents] = useState<Set<string>>(new Set());
  const [showComponentList, setShowComponentList] = useState(false);

  // Use external or local state
  const explodeFactor = externalExplodeFactor ?? localExplodeFactor;
  const hiddenComponents = externalHiddenComponents ?? localHiddenComponents;

  // Handle selection
  const handleSelectComponent = useCallback(
    (componentId: string | null) => {
      onSelectComponent?.(componentId);
    },
    [onSelectComponent]
  );

  // Toggle component visibility
  const toggleComponentVisibility = useCallback((componentId: string) => {
    setLocalHiddenComponents((prev) => {
      const next = new Set(prev);
      if (next.has(componentId)) {
        next.delete(componentId);
      } else {
        next.add(componentId);
      }
      return next;
    });
  }, []);

  // Reset camera
  const resetCamera = useCallback(() => {
    if (controlsRef.current) {
      controlsRef.current.reset();
    }
  }, []);

  // Toggle exploded view
  const toggleExplodedView = useCallback(() => {
    setLocalExplodeFactor((prev) => (prev > 0 ? 0 : 1));
  }, []);

  return (
    <div ref={containerRef} className={`relative bg-gray-100 dark:bg-gray-900 rounded-lg overflow-hidden ${className}`}>
      {/* Three.js Canvas */}
      <Canvas shadows dpr={[1, 2]}>
        <PerspectiveCamera makeDefault position={[150, 100, 150]} fov={45} />
        <OrbitControls
          ref={controlsRef}
          enableDamping
          dampingFactor={0.1}
          minDistance={50}
          maxDistance={500}
        />
        <AssemblyScene
          components={components}
          selectedComponentId={selectedComponentId}
          onSelectComponent={handleSelectComponent}
          explodeFactor={explodeFactor}
          hiddenComponents={hiddenComponents}
        />
      </Canvas>

      {/* Toolbar */}
      <div className="absolute top-4 left-4 flex flex-col gap-2">
        {/* Exploded view toggle */}
        <button
          onClick={toggleExplodedView}
          className={`p-2 rounded-lg shadow-md transition-colors ${
            explodeFactor > 0
              ? 'bg-primary-600 text-white'
              : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
          }`}
          title={explodeFactor > 0 ? 'Collapse view' : 'Exploded view'}
        >
          {explodeFactor > 0 ? <Shrink className="w-5 h-5" /> : <Expand className="w-5 h-5" />}
        </button>

        {/* Reset camera */}
        <button
          onClick={resetCamera}
          className="p-2 bg-white dark:bg-gray-800 rounded-lg shadow-md text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          title="Reset camera"
        >
          <RotateCcw className="w-5 h-5" />
        </button>

        {/* Component list toggle */}
        <button
          onClick={() => setShowComponentList(!showComponentList)}
          className={`p-2 rounded-lg shadow-md transition-colors ${
            showComponentList
              ? 'bg-primary-600 text-white'
              : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
          }`}
          title="Component list"
        >
          <List className="w-5 h-5" />
        </button>
      </div>

      {/* Component count */}
      <div className="absolute bottom-4 left-4 bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm rounded-lg px-3 py-2 shadow-md">
        <span className="text-sm text-gray-600 dark:text-gray-300">
          {components.length} component{components.length !== 1 ? 's' : ''}
          {hiddenComponents.size > 0 && ` (${hiddenComponents.size} hidden)`}
        </span>
      </div>

      {/* Component list panel */}
      {showComponentList && (
        <div className="absolute top-4 right-4 w-64 max-h-96 bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden">
          <div className="px-4 py-3 border-b dark:border-gray-700 bg-gray-50 dark:bg-gray-700">
            <h3 className="font-medium text-gray-900 dark:text-gray-100">Components</h3>
          </div>
          <div className="overflow-y-auto max-h-80">
            {components.map((component) => (
              <div
                key={component.id}
                className={`flex items-center justify-between px-4 py-2 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 ${
                  selectedComponentId === component.id ? 'bg-primary-50 dark:bg-primary-900/30' : ''
                }`}
                onClick={() => handleSelectComponent(component.id)}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <div
                    className="w-3 h-3 rounded-full flex-shrink-0"
                    style={{ backgroundColor: component.color || '#6b7280' }}
                  />
                  <span className="text-sm truncate dark:text-gray-100">{component.name}</span>
                  {component.quantity > 1 && (
                    <span className="text-xs text-gray-500 dark:text-gray-400">×{component.quantity}</span>
                  )}
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleComponentVisibility(component.id);
                  }}
                  className="p-1 text-gray-400 hover:text-gray-600"
                >
                  {hiddenComponents.has(component.id) ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Selected component info */}
      {selectedComponentId && (
        <div className="absolute bottom-4 right-4 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-4 max-w-xs">
          {(() => {
            const selected = components.find((c) => c.id === selectedComponentId);
            if (!selected) return null;
            return (
              <>
                <h4 className="font-medium text-gray-900 dark:text-gray-100">{selected.name}</h4>
                <div className="mt-2 space-y-1 text-sm text-gray-600 dark:text-gray-300">
                  <p>Quantity: {selected.quantity}</p>
                  {selected.is_cots && (
                    <span className="inline-block px-2 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs">
                      COTS Part
                    </span>
                  )}
                </div>
              </>
            );
          })()}
        </div>
      )}
    </div>
  );
}

export default AssemblyViewer;
