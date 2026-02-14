/**
 * Interactive Assembly Viewer Component
 * 
 * Enhanced assembly viewer with interactive transform controls for
 * moving and rotating parts with snapping, alignment guides, exploded view,
 * and undo/redo support.
 */

import { OrbitControls, PerspectiveCamera, Environment, Html } from '@react-three/drei';
import { Canvas, useThree } from '@react-three/fiber';
import {
  Eye,
  EyeOff,
  Focus,
  RotateCcw,
  List,
  Move,
  RotateCw,
  Undo,
  Redo,
  Grid3x3,
} from 'lucide-react';
import { useRef, useState, useEffect, useCallback, useMemo } from 'react';
import * as THREE from 'three';
import { STLLoader, OrbitControls as OrbitControlsImpl } from 'three-stdlib';
import { useComponentVisibility } from '../../hooks/useComponentVisibility';
import { usePartTransforms } from '../../hooks/usePartTransforms';
import { useExplodedView } from '../../hooks/useExplodedView';
import { useAlignmentGuides, DEFAULT_ALIGNMENT_SETTINGS, type AlignmentSettings, type AlignmentPart } from '../../hooks/useAlignmentGuides';
import { PartTransformControls, type TransformMode, type PartTransform } from '../viewer/PartTransformControls';
import { ExplodeToolbar } from './ExplodeToolbar';
import { AlignmentToolbar } from './AlignmentToolbar';
import { AlignmentGuides } from './AlignmentGuides';

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

interface InteractiveAssemblyViewerProps {
  components: AssemblyComponent[];
  selectedComponentId?: string | null;
  onSelectComponent?: (componentId: string | null) => void;
  onComponentTransform?: (componentId: string, transform: PartTransform) => void;
  explodedView?: boolean;
  explodeFactor?: number;
  hiddenComponents?: Set<string>;
  /** Assembly ID for sessionStorage visibility persistence. */
  assemblyId?: string;
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
  distanceMultiplier: number;
  assemblyCenter: THREE.Vector3;
  transform?: PartTransform;
  onClick: () => void;
  onMeshReady?: (mesh: THREE.Mesh) => void;
  onBoundingBoxReady?: (id: string, box: THREE.Box3) => void;
}

function ComponentMesh({
  component,
  isSelected,
  isHidden,
  explodeFactor,
  distanceMultiplier,
  assemblyCenter,
  transform,
  onClick,
  onMeshReady,
  onBoundingBoxReady,
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

  // Notify parent when mesh is ready
  useEffect(() => {
    if (meshRef.current && geometry && onMeshReady) {
      onMeshReady(meshRef.current);
    }
  }, [geometry, onMeshReady]);

  // Apply transform if provided (from undo/redo or external update)
  useEffect(() => {
    if (meshRef.current && transform) {
      meshRef.current.position.set(
        transform.position.x,
        transform.position.y,
        transform.position.z
      );
      meshRef.current.rotation.set(
        THREE.MathUtils.degToRad(transform.rotation.rx),
        THREE.MathUtils.degToRad(transform.rotation.ry),
        THREE.MathUtils.degToRad(transform.rotation.rz)
      );
      meshRef.current.scale.set(
        transform.scale.sx,
        transform.scale.sy,
        transform.scale.sz
      );
    }
  }, [transform]);

  // Report bounding box when geometry is ready
  useEffect(() => {
    if (geometry && onBoundingBoxReady) {
      const pos = transform?.position || component.position;
      const box = new THREE.Box3().setFromBufferAttribute(
        geometry.getAttribute('position') as THREE.BufferAttribute
      );
      // Translate box to world position
      const offset = new THREE.Vector3(pos.x, pos.y, pos.z);
      box.translate(offset);
      onBoundingBoxReady(component.id, box);
    }
  }, [geometry, component.id, component.position, transform?.position, onBoundingBoxReady]);

  // Calculate exploded position
  const explodedPosition = useMemo(() => {
    // Use transform position if available, otherwise use component position
    const pos = transform?.position || component.position;
    const basePos = new THREE.Vector3(pos.x, pos.y, pos.z);

    if (explodeFactor > 0) {
      let direction = basePos.clone().sub(assemblyCenter);
      // Handle parts at center - use default direction
      if (direction.length() < 0.001) {
        direction = new THREE.Vector3(0, 1, 0);
      } else {
        direction.normalize();
      }
      const explodeDistance = explodeFactor * distanceMultiplier * 50;
      return basePos.clone().add(direction.multiplyScalar(explodeDistance));
    }

    return basePos;
  }, [component.position, transform?.position, explodeFactor, distanceMultiplier, assemblyCenter]);

  // Rotation in radians
  const rotationEuler = useMemo(() => {
    const rot = transform?.rotation || component.rotation;
    return new THREE.Euler(
      THREE.MathUtils.degToRad(rot.rx),
      THREE.MathUtils.degToRad(rot.ry),
      THREE.MathUtils.degToRad(rot.rz)
    );
  }, [component.rotation, transform?.rotation]);

  // Scale
  const scale = useMemo(() => {
    const s = transform?.scale || component.scale;
    return [s.sx, s.sy, s.sz] as [number, number, number];
  }, [component.scale, transform?.scale]);

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
      scale={scale}
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
  distanceMultiplier: number;
  hiddenComponents: Set<string>;
  transforms: { [key: string]: PartTransform };
  transformMode: TransformMode;
  enableSnapping: boolean;
  positionSnapIncrement: number;
  rotationSnapIncrement: number;
  onTransformChange: (partId: string, transform: PartTransform) => void;
  onTransformEnd: (partId: string, transform: PartTransform) => void;
  onDraggingChange: (isDragging: boolean) => void;
  onDragPositionChange: (partId: string, position: THREE.Vector3) => void;
  alignmentEnabled: boolean;
  alignmentGuides: ReturnType<typeof useAlignmentGuides>['guides'];
  isDragging: boolean;
  partBoundingBoxes: Map<string, THREE.Box3>;
  onBoundingBoxReady: (id: string, box: THREE.Box3) => void;
}

function AssemblyScene({
  components,
  selectedComponentId,
  onSelectComponent,
  explodeFactor,
  distanceMultiplier,
  hiddenComponents,
  transforms,
  transformMode,
  enableSnapping,
  positionSnapIncrement,
  rotationSnapIncrement,
  onTransformChange,
  onTransformEnd,
  onDraggingChange,
  onDragPositionChange,
  alignmentEnabled,
  alignmentGuides,
  isDragging,
  onBoundingBoxReady,
}: AssemblySceneProps) {
  useThree();
  const [selectedMesh, setSelectedMesh] = useState<THREE.Mesh | null>(null);

  // Calculate assembly center
  const assemblyCenter = useMemo(() => {
    if (components.length === 0) return new THREE.Vector3();

    const center = new THREE.Vector3();
    components.forEach((c) => {
      const transform = transforms[c.id];
      const pos = transform?.position || c.position;
      center.add(new THREE.Vector3(pos.x, pos.y, pos.z));
    });
    center.divideScalar(components.length);
    return center;
  }, [components, transforms]);

  // Click on empty space deselects
  const handleBackgroundClick = useCallback(() => {
    onSelectComponent(null);
    setSelectedMesh(null);
  }, [onSelectComponent]);

  // Handle mesh ready
  const handleMeshReady = useCallback(
    (componentId: string) => (mesh: THREE.Mesh) => {
      if (componentId === selectedComponentId) {
        setSelectedMesh(mesh);
      }
    },
    [selectedComponentId]
  );

  // Update selected mesh when selection changes
  useEffect(() => {
    if (!selectedComponentId) {
      setSelectedMesh(null);
    }
  }, [selectedComponentId]);

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
          distanceMultiplier={distanceMultiplier}
          assemblyCenter={assemblyCenter}
          transform={transforms[component.id]}
          onClick={() => {
            onSelectComponent(component.id);
          }}
          onMeshReady={handleMeshReady(component.id)}
          onBoundingBoxReady={onBoundingBoxReady}
        />
      ))}

      {/* Alignment Guides */}
      <AlignmentGuides
        guides={alignmentGuides}
        visible={alignmentEnabled && isDragging}
      />

      {/* Transform Controls */}
      {selectedComponentId && selectedMesh && (
        <PartTransformControls
          object={selectedMesh}
          mode={transformMode}
          enablePositionSnap={enableSnapping && transformMode === 'translate'}
          positionSnapIncrement={positionSnapIncrement}
          enableRotationSnap={enableSnapping && transformMode === 'rotate'}
          rotationSnapIncrement={rotationSnapIncrement}
          onTransformChange={(transform) => {
            onTransformChange(selectedComponentId, transform);
            // Report position for alignment guides
            if (transformMode === 'translate') {
              onDragPositionChange(selectedComponentId, new THREE.Vector3(
                transform.position.x,
                transform.position.y,
                transform.position.z
              ));
            }
          }}
          onTransformEnd={(transform) => {
            onTransformEnd(selectedComponentId, transform);
          }}
          onDraggingChange={onDraggingChange}
        />
      )}
    </>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function InteractiveAssemblyViewer({
  components,
  selectedComponentId = null,
  onSelectComponent,
  onComponentTransform,
  explodedView: _explodedView = false,
  explodeFactor: externalExplodeFactor,
  hiddenComponents: externalHiddenComponents,
  assemblyId,
  className = '',
}: InteractiveAssemblyViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const controlsRef = useRef<OrbitControlsImpl>(null);

  // Local state
  const [showComponentList, setShowComponentList] = useState(false);
  const [transformMode, setTransformMode] = useState<TransformMode>('translate');
  const [enableSnapping, setEnableSnapping] = useState(true);
  const [positionSnapIncrement] = useState(5);
  const [rotationSnapIncrement] = useState(15);
  const [isDragging, setIsDragging] = useState(false);
  const [dragPosition, setDragPosition] = useState<THREE.Vector3 | null>(null);
  const [partBoundingBoxes, setPartBoundingBoxes] = useState<Map<string, THREE.Box3>>(new Map());

  // Alignment state
  const [alignmentEnabled, setAlignmentEnabled] = useState(true);
  const [alignmentSettings, setAlignmentSettings] = useState<AlignmentSettings>(DEFAULT_ALIGNMENT_SETTINGS);

  // Exploded view with animation
  const explodedView = useExplodedView();
  
  // Use external explodeFactor if provided, otherwise use animated value
  const effectiveExplodeFactor = externalExplodeFactor ?? explodedView.explodeFactor;

  // Component visibility (hide/show/isolate)
  const {
    hiddenComponents,
    isolateState,
    toggleVisibility,
    isolateComponent,
    showAll,
    hiddenCount,
  } = useComponentVisibility({
    componentIds: components.map((c) => c.id),
    assemblyId,
    externalHiddenComponents,
  });

  // Transform management with undo/redo
  const partTransforms = usePartTransforms({
    onTransformUpdate: onComponentTransform,
  });

  // Convert components to AlignmentPart format for alignment hook
  const alignmentParts = useMemo((): AlignmentPart[] => {
    return components.map((c) => {
      const transform = partTransforms.transforms[c.id];
      const pos = transform?.position || c.position;
      const position = new THREE.Vector3(pos.x, pos.y, pos.z);
      
      // Use stored bounding box or create default
      const storedBox = partBoundingBoxes.get(c.id);
      const boundingBox = storedBox ?? new THREE.Box3(
        position.clone().sub(new THREE.Vector3(10, 10, 10)),
        position.clone().add(new THREE.Vector3(10, 10, 10))
      );

      return {
        id: c.id,
        name: c.name,
        position,
        boundingBox,
      };
    });
  }, [components, partTransforms.transforms, partBoundingBoxes]);

  // Alignment guides calculation
  const alignmentGuidesResult = useAlignmentGuides({
    parts: alignmentParts,
    draggedPartId: isDragging ? selectedComponentId : null,
    dragPosition,
    hiddenParts: hiddenComponents,
    settings: alignmentSettings,
  });

  // Handle bounding box updates from ComponentMesh
  const handleBoundingBoxReady = useCallback((id: string, box: THREE.Box3) => {
    setPartBoundingBoxes((prev) => {
      const next = new Map(prev);
      next.set(id, box);
      return next;
    });
  }, []);

  // Handle selection
  const handleSelectComponent = useCallback(
    (componentId: string | null) => {
      onSelectComponent?.(componentId);
    },
    [onSelectComponent]
  );

  // Handle transform change (during drag)
  const handleTransformChange = useCallback(
    (_partId: string, _transform: PartTransform) => {
      // We don't push to history during dragging, only on end
    },
    []
  );

  // Handle drag position change for alignment guides
  const handleDragPositionChange = useCallback(
    (_partId: string, position: THREE.Vector3) => {
      setDragPosition(position);
    },
    []
  );

  // Handle dragging state change
  const handleDraggingChange = useCallback(
    (dragging: boolean) => {
      setIsDragging(dragging);
      if (!dragging) {
        setDragPosition(null);
      }
    },
    []
  );

  // Handle transform end (when drag completes)
  const handleTransformEnd = useCallback(
    (partId: string, transform: PartTransform) => {
      partTransforms.updateTransform(
        partId,
        transform,
        `${transformMode === 'translate' ? 'Move' : 'Rotate'} ${components.find(c => c.id === partId)?.name || partId}`
      );
    },
    [partTransforms, transformMode, components]
  );

  // Reset camera
  const resetCamera = useCallback(() => {
    if (controlsRef.current) {
      controlsRef.current.reset();
    }
  }, []);

  // Handle alignment settings change
  const handleAlignmentSettingsChange = useCallback(
    (changes: Partial<AlignmentSettings>) => {
      setAlignmentSettings((prev) => ({ ...prev, ...changes }));
    },
    []
  );

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger shortcuts if typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      // Undo/Redo
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        partTransforms.undo();
      } else if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
        e.preventDefault();
        partTransforms.redo();
      }
      // Transform mode shortcuts
      else if (e.key === 'g' || e.key === 'G') {
        e.preventDefault();
        setTransformMode('translate');
      } else if (e.key === 'r' || e.key === 'R') {
        e.preventDefault();
        setTransformMode('rotate');
      }
      // Toggle snapping
      else if (e.key === 's' || e.key === 'S') {
        e.preventDefault();
        setEnableSnapping((prev) => !prev);
      }
      // Toggle alignment guides
      else if (e.key === 'a' || e.key === 'A') {
        e.preventDefault();
        setAlignmentEnabled((prev) => !prev);
      }
      // Toggle exploded view
      else if (e.key === 'e' || e.key === 'E') {
        e.preventDefault();
        explodedView.toggle();
      }
      // Hide selected component
      else if (e.key === 'h' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
        if (selectedComponentId) {
          e.preventDefault();
          toggleVisibility(selectedComponentId);
        }
      }
      // Show all components
      else if (e.key === 'H' && e.shiftKey && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        showAll();
      }
      // Isolate selected component
      else if ((e.key === 'i' || e.key === 'I') && !e.ctrlKey && !e.metaKey) {
        if (selectedComponentId) {
          e.preventDefault();
          isolateComponent(selectedComponentId);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [partTransforms, selectedComponentId, toggleVisibility, showAll, isolateComponent, explodedView]);

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
          enabled={!isDragging}
        />
        <AssemblyScene
          components={components}
          selectedComponentId={selectedComponentId}
          onSelectComponent={handleSelectComponent}
          explodeFactor={effectiveExplodeFactor}
          distanceMultiplier={explodedView.distanceMultiplier}
          hiddenComponents={hiddenComponents}
          transforms={partTransforms.transforms}
          transformMode={transformMode}
          enableSnapping={enableSnapping}
          positionSnapIncrement={positionSnapIncrement}
          rotationSnapIncrement={rotationSnapIncrement}
          onTransformChange={handleTransformChange}
          onTransformEnd={handleTransformEnd}
          onDraggingChange={handleDraggingChange}
          onDragPositionChange={handleDragPositionChange}
          alignmentEnabled={alignmentEnabled}
          alignmentGuides={alignmentGuidesResult.guides}
          isDragging={isDragging}
          partBoundingBoxes={partBoundingBoxes}
          onBoundingBoxReady={handleBoundingBoxReady}
        />
      </Canvas>

      {/* Main Toolbar */}
      <div className="absolute top-4 left-4 flex flex-col gap-2">
        {/* Transform mode buttons */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-1 flex flex-col gap-1">
          <button
            onClick={() => setTransformMode('translate')}
            className={`p-2 rounded transition-colors ${
              transformMode === 'translate'
                ? 'bg-primary-600 text-white'
                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
            title="Move (G)"
          >
            <Move className="w-5 h-5" />
          </button>
          <button
            onClick={() => setTransformMode('rotate')}
            className={`p-2 rounded transition-colors ${
              transformMode === 'rotate'
                ? 'bg-primary-600 text-white'
                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
            title="Rotate (R)"
          >
            <RotateCw className="w-5 h-5" />
          </button>
        </div>

        {/* Undo/Redo buttons */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-1 flex flex-col gap-1">
          <button
            onClick={partTransforms.undo}
            disabled={!partTransforms.canUndo}
            className={`p-2 rounded transition-colors ${
              partTransforms.canUndo
                ? 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                : 'text-gray-400 dark:text-gray-600 cursor-not-allowed'
            }`}
            title={`Undo ${partTransforms.undoDescription ? `(${partTransforms.undoDescription})` : '(Ctrl+Z)'}`}
          >
            <Undo className="w-5 h-5" />
          </button>
          <button
            onClick={partTransforms.redo}
            disabled={!partTransforms.canRedo}
            className={`p-2 rounded transition-colors ${
              partTransforms.canRedo
                ? 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                : 'text-gray-400 dark:text-gray-600 cursor-not-allowed'
            }`}
            title={`Redo ${partTransforms.redoDescription ? `(${partTransforms.redoDescription})` : '(Ctrl+Y)'}`}
          >
            <Redo className="w-5 h-5" />
          </button>
        </div>

        {/* View controls */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-1 flex flex-col gap-1">
          <button
            onClick={() => setEnableSnapping(!enableSnapping)}
            className={`p-2 rounded transition-colors ${
              enableSnapping
                ? 'bg-primary-600 text-white'
                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
            title={`Snapping ${enableSnapping ? 'On' : 'Off'} (S)`}
          >
            <Grid3x3 className="w-5 h-5" />
          </button>
          
          {/* Alignment Toolbar */}
          <AlignmentToolbar
            enabled={alignmentEnabled}
            onToggle={() => setAlignmentEnabled(!alignmentEnabled)}
            settings={alignmentSettings}
            onSettingsChange={handleAlignmentSettingsChange}
          />
          
          {/* Explode Toolbar */}
          <ExplodeToolbar
            state={explodedView.explodeState}
            isAnimating={explodedView.isAnimating}
            distanceMultiplier={explodedView.distanceMultiplier}
            onToggle={explodedView.toggle}
            onDistanceChange={explodedView.setDistanceMultiplier}
          />
          
          <button
            onClick={resetCamera}
            className="p-2 rounded text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            title="Reset camera"
          >
            <RotateCcw className="w-5 h-5" />
          </button>
          <button
            onClick={() => setShowComponentList(!showComponentList)}
            className={`p-2 rounded transition-colors ${
              showComponentList
                ? 'bg-primary-600 text-white'
                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
            title="Component list"
          >
            <List className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Component count */}
      <div className="absolute bottom-4 left-4 bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm rounded-lg px-3 py-2 shadow-md">
        <span className="text-sm text-gray-600 dark:text-gray-300">
          {components.length} component{components.length !== 1 ? 's' : ''}
          {hiddenCount > 0 && ` (${hiddenCount} hidden)`}
          {isolateState.isActive && ' \u2022 Isolated'}
        </span>
      </div>

      {/* Component list panel */}
      {showComponentList && (
        <div className="absolute top-4 right-4 w-64 max-h-96 bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden">
          <div className="px-4 py-3 border-b dark:border-gray-700 bg-gray-50 dark:bg-gray-700">
            <div className="flex items-center justify-between">
              <h3 className="font-medium text-gray-900 dark:text-gray-100">
                Components
                {isolateState.isActive && (
                  <span className="ml-2 text-xs bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300 px-2 py-0.5 rounded-full">
                    Isolated
                  </span>
                )}
              </h3>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => {
                    if (selectedComponentId) {
                      isolateComponent(selectedComponentId);
                    }
                  }}
                  disabled={!selectedComponentId}
                  className={`p-1.5 rounded transition-colors ${
                    isolateState.isActive
                      ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
                      : selectedComponentId
                      ? 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'
                      : 'text-gray-300 dark:text-gray-600 cursor-not-allowed'
                  }`}
                  title={`Isolate selected (I)${!selectedComponentId ? ' - select a component first' : ''}`}
                  aria-label="Isolate selected component"
                >
                  <Focus className="w-4 h-4" />
                </button>
                <button
                  onClick={showAll}
                  disabled={hiddenCount === 0 && !isolateState.isActive}
                  className={`p-1.5 rounded transition-colors ${
                    hiddenCount > 0 || isolateState.isActive
                      ? 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'
                      : 'text-gray-300 dark:text-gray-600 cursor-not-allowed'
                  }`}
                  title="Show all (Shift+H)"
                  aria-label="Show all components"
                >
                  <Eye className="w-4 h-4" />
                </button>
              </div>
            </div>
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
                    toggleVisibility(component.id);
                  }}
                  className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  aria-label={`${hiddenComponents.has(component.id) ? 'Show' : 'Hide'} ${component.name}`}
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
                  <div className="mt-2 pt-2 border-t dark:border-gray-700">
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {transformMode === 'translate' ? 'Move (G)' : 'Rotate (R)'} • 
                      {enableSnapping ? ` Snap: ${transformMode === 'translate' ? positionSnapIncrement : rotationSnapIncrement}${transformMode === 'translate' ? 'u' : '°'}` : ' No snap'}
                    </p>
                  </div>
                </div>
              </>
            );
          })()}
        </div>
      )}
    </div>
  );
}

export default InteractiveAssemblyViewer;
