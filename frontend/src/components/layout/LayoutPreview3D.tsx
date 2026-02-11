/**
 * Layout Preview 3D
 * 
 * Three.js-based 3D visualization of component layout within enclosure.
 */

import { 
  OrbitControls, 
  PerspectiveCamera, 
  Grid, 
  Environment,
  Html,
} from '@react-three/drei';
import { Canvas, useFrame } from '@react-three/fiber';
import { useRef, useState } from 'react';
import * as THREE from 'three';
import type { ComponentPlacement, LayoutDimensions } from './types';
import { cn } from '@/lib/utils';

interface LayoutPreview3DProps {
  dimensions: LayoutDimensions;
  placements: ComponentPlacement[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  showEnclosure?: boolean;
  showGrid?: boolean;
  wireframe?: boolean;
}

export function LayoutPreview3D({
  dimensions,
  placements,
  selectedId,
  onSelect,
  showEnclosure = true,
  showGrid = true,
  wireframe = false,
}: LayoutPreview3DProps) {
  const [viewMode, setViewMode] = useState<'perspective' | 'top' | 'front' | 'side'>('perspective');

  return (
    <div className="relative w-full h-full bg-slate-900">
      <Canvas shadows>
        <Scene
          dimensions={dimensions}
          placements={placements}
          selectedId={selectedId}
          onSelect={onSelect}
          showEnclosure={showEnclosure}
          showGrid={showGrid}
          wireframe={wireframe}
          viewMode={viewMode}
        />
      </Canvas>

      {/* View controls */}
      <div className="absolute top-4 left-4 flex gap-1 bg-slate-800/90 rounded-lg p-1">
        <ViewButton 
          active={viewMode === 'perspective'} 
          onClick={() => setViewMode('perspective')}
          title="Perspective"
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
          </svg>
        </ViewButton>
        <ViewButton 
          active={viewMode === 'top'} 
          onClick={() => setViewMode('top')}
          title="Top"
        >
          T
        </ViewButton>
        <ViewButton 
          active={viewMode === 'front'} 
          onClick={() => setViewMode('front')}
          title="Front"
        >
          F
        </ViewButton>
        <ViewButton 
          active={viewMode === 'side'} 
          onClick={() => setViewMode('side')}
          title="Side"
        >
          S
        </ViewButton>
      </div>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-slate-800/90 rounded-lg p-3 text-xs">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-3 h-3 rounded bg-blue-500" />
          <span className="text-slate-300">Selected</span>
        </div>
        <div className="flex items-center gap-2 mb-1">
          <div className="w-3 h-3 rounded bg-slate-500" />
          <span className="text-slate-300">Component</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded border border-slate-400" />
          <span className="text-slate-300">Enclosure</span>
        </div>
      </div>
    </div>
  );
}

interface ViewButtonProps {
  children: React.ReactNode;
  active: boolean;
  onClick: () => void;
  title: string;
}

function ViewButton({ children, active, onClick, title }: ViewButtonProps) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={cn(
        'w-7 h-7 flex items-center justify-center rounded text-xs font-medium transition-colors',
        active 
          ? 'bg-blue-600 text-white' 
          : 'text-slate-400 hover:text-white hover:bg-slate-700',
      )}
    >
      {children}
    </button>
  );
}

interface SceneProps {
  dimensions: LayoutDimensions;
  placements: ComponentPlacement[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  showEnclosure: boolean;
  showGrid: boolean;
  wireframe: boolean;
  viewMode: 'perspective' | 'top' | 'front' | 'side';
}

function Scene({
  dimensions,
  placements,
  selectedId,
  onSelect,
  showEnclosure,
  showGrid,
  wireframe,
  viewMode,
}: SceneProps) {
  // Convert mm to scene units (1 unit = 10mm for better scale)
  const scale = 0.01;
  const width = dimensions.width * scale;
  const depth = dimensions.depth * scale;
  const height = dimensions.height * scale;

  // Camera positions for different views
  const getCameraPosition = (): [number, number, number] => {
    const distance = Math.max(width, depth, height) * 2;
    switch (viewMode) {
      case 'top': return [0, distance, 0];
      case 'front': return [0, height / 2, distance];
      case 'side': return [distance, height / 2, 0];
      default: return [distance * 0.7, distance * 0.7, distance * 0.7];
    }
  };

  return (
    <>
      {/* Camera */}
      <PerspectiveCamera makeDefault position={getCameraPosition()} fov={50} />
      <OrbitControls 
        enablePan 
        enableZoom 
        enableRotate={viewMode === 'perspective'}
        target={[0, height / 2, 0]}
      />

      {/* Lighting */}
      <ambientLight intensity={0.5} />
      <directionalLight position={[10, 10, 5]} intensity={1} castShadow />
      <directionalLight position={[-5, 5, -5]} intensity={0.3} />

      {/* Environment */}
      <Environment preset="studio" />

      {/* Grid */}
      {showGrid && (
        <Grid
          args={[width * 2, depth * 2]}
          position={[0, 0, 0]}
          cellSize={dimensions.gridSize * scale}
          cellThickness={0.5}
          cellColor="#4a5568"
          sectionSize={dimensions.gridSize * 5 * scale}
          sectionThickness={1}
          sectionColor="#2d3748"
          fadeDistance={Math.max(width, depth) * 3}
          infiniteGrid
        />
      )}

      {/* Enclosure wireframe */}
      {showEnclosure && (
        <EnclosureBox
          width={width}
          depth={depth}
          height={height}
        />
      )}

      {/* Components */}
      {placements.map((placement) => (
        <ComponentBox3D
          key={placement.id}
          placement={placement}
          scale={scale}
          selected={placement.id === selectedId}
          wireframe={wireframe}
          onClick={() => onSelect(placement.id)}
        />
      ))}

      {/* Click handler for deselection */}
      <mesh
        position={[0, -0.01, 0]}
        rotation={[-Math.PI / 2, 0, 0]}
        onClick={(e) => {
          e.stopPropagation();
          onSelect(null);
        }}
        visible={false}
      >
        <planeGeometry args={[width * 10, depth * 10]} />
        <meshBasicMaterial transparent opacity={0} />
      </mesh>
    </>
  );
}

interface EnclosureBoxProps {
  width: number;
  depth: number;
  height: number;
}

function EnclosureBox({ width, depth, height }: EnclosureBoxProps) {
  const wallThickness = 0.02; // 2mm walls

  return (
    <group position={[0, height / 2, 0]}>
      {/* Wireframe edges */}
      <lineSegments>
        <edgesGeometry args={[new THREE.BoxGeometry(width, height, depth)]} />
        <lineBasicMaterial color="#64748b" />
      </lineSegments>

      {/* Transparent walls */}
      <mesh>
        <boxGeometry args={[width, height, depth]} />
        <meshPhysicalMaterial
          color="#1e293b"
          transparent
          opacity={0.1}
          side={THREE.BackSide}
          depthWrite={false}
        />
      </mesh>

      {/* Base plate */}
      <mesh position={[0, -height / 2 + wallThickness / 2, 0]} receiveShadow>
        <boxGeometry args={[width - wallThickness * 2, wallThickness, depth - wallThickness * 2]} />
        <meshStandardMaterial color="#334155" />
      </mesh>
    </group>
  );
}

interface ComponentBox3DProps {
  placement: ComponentPlacement;
  scale: number;
  selected: boolean;
  wireframe: boolean;
  onClick: () => void;
}

function ComponentBox3D({ placement, scale, selected, wireframe, onClick }: ComponentBox3DProps) {
  const meshRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);

  // Convert placement dimensions and position
  const width = placement.width * scale;
  const depth = placement.depth * scale;
  const height = placement.height * scale;

  // Center the component and offset by its own dimensions
  const x = (placement.x - (placement.width / 2)) * scale + width / 2;
  const y = placement.z * scale + height / 2;
  const z = (placement.y - (placement.depth / 2)) * scale + depth / 2;

  // Rotation (convert to radians)
  const rotation = (placement.rotation * Math.PI) / 180;

  // Color based on state
  const getColor = () => {
    if (placement.hasError) return '#ef4444';
    if (selected) return '#3b82f6';
    if (hovered) return '#60a5fa';
    if (placement.locked) return '#6b7280';
    return '#64748b';
  };

  // Highlight animation
  useFrame(({ clock }) => {
    if (meshRef.current && selected) {
      const pulse = Math.sin(clock.elapsedTime * 3) * 0.05 + 1;
      meshRef.current.scale.setScalar(pulse);
    } else if (meshRef.current) {
      meshRef.current.scale.setScalar(1);
    }
  });

  return (
    <group position={[x, y, z]} rotation={[0, rotation, 0]}>
      <mesh
        ref={meshRef}
        castShadow
        receiveShadow
        onClick={(e) => {
          e.stopPropagation();
          onClick();
        }}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
      >
        <boxGeometry args={[width, height, depth]} />
        <meshStandardMaterial
          color={getColor()}
          wireframe={wireframe}
          metalness={0.3}
          roughness={0.7}
        />
      </mesh>

      {/* Selection outline */}
      {selected && (
        <lineSegments>
          <edgesGeometry args={[new THREE.BoxGeometry(width * 1.02, height * 1.02, depth * 1.02)]} />
          <lineBasicMaterial color="#3b82f6" linewidth={2} />
        </lineSegments>
      )}

      {/* Lock indicator */}
      {placement.locked && (
        <Html position={[0, height / 2 + 0.05, 0]} center>
          <div className="w-4 h-4 bg-slate-800 rounded-full flex items-center justify-center">
            <svg className="w-2.5 h-2.5 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
        </Html>
      )}

      {/* Component label */}
      {(selected || hovered) && (
        <Html position={[0, height / 2 + 0.1, 0]} center>
          <div className="px-2 py-1 bg-slate-800 rounded text-xs text-white whitespace-nowrap shadow-lg">
            {placement.name}
            <div className="text-slate-400 text-[10px]">
              {placement.width}×{placement.depth}×{placement.height} mm
            </div>
          </div>
        </Html>
      )}
    </group>
  );
}
