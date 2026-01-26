/**
 * 3D Model Viewer component.
 *
 * Uses Three.js via @react-three/fiber to display STL models
 * with orbit controls, lighting, and responsive sizing.
 */

import { Suspense, useRef, useState, useEffect } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import {
  OrbitControls,
  Center,
  Grid,
  Environment,
  Html,
} from '@react-three/drei';
import * as THREE from 'three';
import { STLLoader } from 'three-stdlib';
import { Loader2, RotateCcw, ZoomIn, ZoomOut } from 'lucide-react';

interface ModelViewerProps {
  /** URL to the STL file */
  stlUrl?: string;
  /** Raw STL data as ArrayBuffer */
  stlData?: ArrayBuffer;
  /** Model color */
  color?: string;
  /** Show grid */
  showGrid?: boolean;
  /** Show axes helper */
  showAxes?: boolean;
  /** Background color */
  backgroundColor?: string;
  /** Callback when model loads */
  onLoad?: () => void;
  /** Callback on load error */
  onError?: (error: Error) => void;
  /** CSS class for container */
  className?: string;
}

/**
 * STL Model component that loads and displays an STL file.
 */
function STLModel({
  url,
  data,
  color = '#3b82f6',
  onLoad,
  onError,
}: {
  url?: string;
  data?: ArrayBuffer;
  color?: string;
  onLoad?: () => void;
  onError?: (error: Error) => void;
}) {
  const [geometry, setGeometry] = useState<THREE.BufferGeometry | null>(null);
  const meshRef = useRef<THREE.Mesh>(null);

  useEffect(() => {
    const loader = new STLLoader();

    const handleGeometry = (geo: THREE.BufferGeometry) => {
      // Center and normalize the geometry
      geo.center();
      geo.computeBoundingBox();
      geo.computeVertexNormals();

      // Scale to fit within a reasonable size
      const bbox = geo.boundingBox!;
      const size = new THREE.Vector3();
      bbox.getSize(size);
      const maxDim = Math.max(size.x, size.y, size.z);
      const scale = 100 / maxDim; // Normalize to 100 units
      geo.scale(scale, scale, scale);

      setGeometry(geo);
      onLoad?.();
    };

    const handleError = (error: unknown) => {
      console.error('Failed to load STL:', error);
      onError?.(error instanceof Error ? error : new Error('Failed to load STL'));
    };

    if (data) {
      try {
        const geo = loader.parse(data);
        handleGeometry(geo);
      } catch (e) {
        handleError(e);
      }
    } else if (url) {
      loader.load(url, handleGeometry, undefined, handleError);
    }

    return () => {
      geometry?.dispose();
    };
  }, [url, data]);

  if (!geometry) return null;

  return (
    <mesh ref={meshRef} geometry={geometry} castShadow receiveShadow>
      <meshStandardMaterial
        color={color}
        metalness={0.3}
        roughness={0.5}
        flatShading={false}
      />
    </mesh>
  );
}

/**
 * Loading indicator shown while model loads.
 */
function LoadingIndicator() {
  return (
    <Html center>
      <div className="flex flex-col items-center gap-2 text-gray-500">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="text-sm">Loading model...</span>
      </div>
    </Html>
  );
}

/**
 * Camera controller for programmatic camera control.
 */
function CameraController({
  controlsRef,
}: {
  controlsRef: React.RefObject<any>;
}) {
  const { camera } = useThree();

  const resetCamera = () => {
    if (controlsRef.current) {
      controlsRef.current.reset();
    }
    camera.position.set(100, 100, 100);
    camera.lookAt(0, 0, 0);
  };

  // Expose reset function via ref
  useEffect(() => {
    if (controlsRef.current) {
      controlsRef.current.resetCamera = resetCamera;
    }
  }, [controlsRef.current]);

  return null;
}

/**
 * Main 3D Model Viewer component.
 */
export function ModelViewer({
  stlUrl,
  stlData,
  color = '#3b82f6',
  showGrid = true,
  showAxes = false,
  backgroundColor = '#f8fafc',
  onLoad,
  onError,
  className = '',
}: ModelViewerProps) {
  const controlsRef = useRef<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const handleLoad = () => {
    setIsLoading(false);
    onLoad?.();
  };

  const handleError = (err: Error) => {
    setIsLoading(false);
    setError(err);
    onError?.(err);
  };

  const resetView = () => {
    if (controlsRef.current?.resetCamera) {
      controlsRef.current.resetCamera();
    }
  };

  const zoomIn = () => {
    if (controlsRef.current) {
      const camera = controlsRef.current.object;
      camera.position.multiplyScalar(0.8);
    }
  };

  const zoomOut = () => {
    if (controlsRef.current) {
      const camera = controlsRef.current.object;
      camera.position.multiplyScalar(1.25);
    }
  };

  if (error) {
    return (
      <div className={`flex items-center justify-center bg-gray-100 ${className}`}>
        <div className="text-center text-gray-500">
          <p className="text-sm">Failed to load model</p>
          <p className="text-xs mt-1">{error.message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`relative h-full w-full ${className}`}>
      <Canvas
        shadows
        dpr={[1, 2]}
        style={{ background: backgroundColor, width: '100%', height: '100%' }}
        camera={{ position: [100, 100, 100], fov: 50 }}
      >
        <Suspense fallback={<LoadingIndicator />}>
          {/* Lighting */}
          <ambientLight intensity={0.4} />
          <directionalLight
            position={[50, 50, 25]}
            intensity={1}
            castShadow
            shadow-mapSize={[1024, 1024]}
          />
          <directionalLight position={[-50, 50, -25]} intensity={0.5} />

          {/* Environment for reflections */}
          <Environment preset="city" />

          {/* Model */}
          <Center>
            {(stlUrl || stlData) && (
              <STLModel
                url={stlUrl}
                data={stlData}
                color={color}
                onLoad={handleLoad}
                onError={handleError}
              />
            )}
          </Center>

          {/* Grid */}
          {showGrid && (
            <Grid
              args={[200, 200]}
              cellSize={10}
              cellThickness={0.5}
              cellColor="#e5e7eb"
              sectionSize={50}
              sectionThickness={1}
              sectionColor="#9ca3af"
              fadeDistance={400}
              fadeStrength={1}
              followCamera={false}
              infiniteGrid
            />
          )}

          {/* Axes Helper */}
          {showAxes && <axesHelper args={[50]} />}

          {/* Controls */}
          <OrbitControls
            ref={controlsRef}
            makeDefault
            enableDamping
            dampingFactor={0.05}
            minDistance={10}
            maxDistance={500}
            enablePan
            panSpeed={0.5}
            rotateSpeed={0.5}
            zoomSpeed={0.5}
          />

          <CameraController controlsRef={controlsRef} />
        </Suspense>
      </Canvas>

      {/* Control buttons */}
      <div className="absolute bottom-4 right-4 flex gap-2">
        <button
          onClick={resetView}
          className="p-2 bg-white rounded-lg shadow-md hover:bg-gray-50 transition-colors"
          title="Reset view"
        >
          <RotateCcw className="h-4 w-4 text-gray-600" />
        </button>
        <button
          onClick={zoomIn}
          className="p-2 bg-white rounded-lg shadow-md hover:bg-gray-50 transition-colors"
          title="Zoom in"
        >
          <ZoomIn className="h-4 w-4 text-gray-600" />
        </button>
        <button
          onClick={zoomOut}
          className="p-2 bg-white rounded-lg shadow-md hover:bg-gray-50 transition-colors"
          title="Zoom out"
        >
          <ZoomOut className="h-4 w-4 text-gray-600" />
        </button>
      </div>

      {/* Loading overlay */}
      {isLoading && (stlUrl || stlData) && (
        <div className="absolute inset-0 flex items-center justify-center bg-white/50">
          <div className="flex items-center gap-2 text-gray-600">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span>Loading model...</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default ModelViewer;
