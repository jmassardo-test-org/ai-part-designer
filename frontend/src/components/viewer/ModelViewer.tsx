/**
 * 3D Model Viewer component.
 *
 * Uses Three.js via @react-three/fiber to display STL models
 * with orbit controls, lighting, and responsive sizing.
 */

import {
  OrbitControls,
  Center,
  Grid,
  Environment,
  Html,
} from '@react-three/drei';
import { Canvas, useThree } from '@react-three/fiber';
import { Loader2, RotateCcw, ZoomIn, ZoomOut, AlertTriangle } from 'lucide-react';
import { Component, ErrorInfo, ReactNode, Suspense, useRef, useState, useEffect, useMemo, useCallback } from 'react';
import * as THREE from 'three';
import { STLLoader } from 'three-stdlib';

// Module-level flag to track if WebGL creation has ever failed
// Once it fails, we don't try again to avoid repeated errors
let webglHasFailed = false;
let webglFailureMessage = '';

/**
 * Check if WebGL is available in the browser.
 * Returns an object with availability status and any error message.
 * 
 * Note: This is a basic check. Three.js may still fail to create a context
 * due to resource exhaustion or driver issues. We track failures at module
 * level to prevent repeated attempts.
 */
function checkWebGLAvailability(): { available: boolean; message?: string } {
  // If WebGL has already failed, don't try again
  if (webglHasFailed) {
    return { available: false, message: webglFailureMessage };
  }

  if (typeof window === 'undefined') {
    return { available: false, message: 'Window not available (SSR)' };
  }

  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl2') || canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    
    if (!gl) {
      webglHasFailed = true;
      webglFailureMessage = 'WebGL is not supported by your browser or is disabled. Please enable hardware acceleration in your browser settings.';
      return { 
        available: false, 
        message: webglFailureMessage
      };
    }
    
    // Clean up the test context
    const loseContext = (gl as WebGLRenderingContext).getExtension('WEBGL_lose_context');
    if (loseContext) {
      loseContext.loseContext();
    }
    
    return { available: true };
  } catch (e) {
    webglHasFailed = true;
    webglFailureMessage = `WebGL check failed: ${e instanceof Error ? e.message : 'Unknown error'}`;
    return { 
      available: false, 
      message: webglFailureMessage
    };
  }
}

/**
 * Mark WebGL as failed (called when Three.js fails to create context)
 */
function markWebGLFailed(message: string) {
  webglHasFailed = true;
  webglFailureMessage = message;
}

/**
 * Fallback component when WebGL is not available.
 */
function WebGLFallback({ message, className }: { message: string; className?: string }) {
  return (
    <div className={`flex items-center justify-center bg-gray-100 dark:bg-gray-800 ${className || ''}`}>
      <div className="text-center p-6 max-w-md">
        <AlertTriangle className="h-12 w-12 text-amber-500 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-2">
          3D Viewer Unavailable
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
          {message}
        </p>
        <div className="text-xs text-gray-400 dark:text-gray-500 space-y-1">
          <p>Try these solutions:</p>
          <ul className="list-disc list-inside text-left">
            <li>Enable hardware acceleration in browser settings</li>
            <li>Update your graphics drivers</li>
            <li>Try a different browser (Chrome, Firefox, Edge)</li>
            <li>Close other tabs using 3D graphics</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

/**
 * Error boundary specifically for catching WebGL/Canvas errors.
 * When an error occurs, it marks WebGL as failed to prevent retries.
 */
class WebGLErrorBoundary extends Component<
  { children: ReactNode; fallback: ReactNode; onError?: (error: Error) => void },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: ReactNode; fallback: ReactNode; onError?: (error: Error) => void }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    // Mark WebGL as failed at module level to prevent future attempts
    markWebGLFailed(error.message || 'WebGL context creation failed');
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('WebGL Error:', error, errorInfo);
    this.props.onError?.(error);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}

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
  /** Background color (or 'dark' for dark mode, 'light' for light mode) */
  backgroundColor?: string;
  /** Enable dark mode styling */
  darkMode?: boolean;
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
      <div className="flex flex-col items-center gap-2 text-gray-500 dark:text-gray-400">
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
  controlsRef: React.RefObject<unknown>;
}) {
  const { camera } = useThree();

  const resetCamera = () => {
    const current = controlsRef.current as { reset?: () => void } | null;
    if (current?.reset) {
      current.reset();
    }
    camera.position.set(100, 100, 100);
    camera.lookAt(0, 0, 0);
  };

  // Expose reset function via ref
  useEffect(() => {
    const current = controlsRef.current as { resetCamera?: () => void };
    if (current) {
      current.resetCamera = resetCamera;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
  showAxes = true,
  backgroundColor,
  darkMode,
  onLoad,
  onError,
  className = '',
}: ModelViewerProps) {
  const controlsRef = useRef<typeof OrbitControls | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [webglFailed, setWebglFailed] = useState(false);
  
  // Check WebGL availability - includes module-level failure tracking
  const webglCheck = useMemo(() => checkWebGLAvailability(), []);
  
  // Handle WebGL errors from the error boundary
  const handleWebGLError = useCallback((err: Error) => {
    console.error('WebGL creation failed:', err.message);
    setWebglFailed(true);
    onError?.(err);
  }, [onError]);
  
  // Auto-detect dark mode from system/document if not explicitly set
  const isDarkMode = darkMode ?? (typeof document !== 'undefined' && document.documentElement.classList.contains('dark'));
  
  // Compute actual background color
  const actualBackgroundColor = backgroundColor || (isDarkMode ? '#1e293b' : '#f8fafc');
  
  // Grid colors based on theme
  const gridColors = isDarkMode
    ? { cellColor: '#475569', sectionColor: '#64748b' }
    : { cellColor: '#e5e7eb', sectionColor: '#9ca3af' };

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
    const controls = controlsRef.current as unknown as { reset?: () => void };
    if (controls?.reset) {
      controls.reset();
    }
  };

  const zoomIn = () => {
    const controls = controlsRef.current as unknown as { object?: THREE.Camera };
    if (controls?.object) {
      controls.object.position.multiplyScalar(0.8);
    }
  };

  const zoomOut = () => {
    const controls = controlsRef.current as unknown as { object?: THREE.Camera };
    if (controls?.object) {
      controls.object.position.multiplyScalar(1.25);
    }
  };

  // Handle WebGL context creation success
  const handleCanvasCreated = useCallback(() => {
    // Canvas created successfully - nothing to do
  }, []);

  // Check WebGL availability first (includes module-level and component-level failure tracking)
  if (!webglCheck.available || webglFailed) {
    return (
      <WebGLFallback 
        message={webglCheck.message || 'Unable to initialize 3D graphics. Your browser may not support WebGL or hardware acceleration may be disabled.'} 
        className={className} 
      />
    );
  }

  if (error) {
    return (
      <div className={`flex items-center justify-center bg-gray-100 dark:bg-gray-800 ${className}`}>
        <div className="text-center text-gray-500 dark:text-gray-400">
          <p className="text-sm">Failed to load model</p>
          <p className="text-xs mt-1">{error.message}</p>
        </div>
      </div>
    );
  }

  const webglFallbackElement = (
    <WebGLFallback 
      message="An error occurred while initializing the 3D viewer. This may be due to graphics driver issues or resource limitations." 
      className={className} 
    />
  );

  return (
    <WebGLErrorBoundary fallback={webglFallbackElement} onError={handleWebGLError}>
      <div className={`relative h-full w-full ${className}`}>
        <Canvas
          shadows
          dpr={[1, 2]}
          style={{ background: actualBackgroundColor, width: '100%', height: '100%' }}
          camera={{ position: [100, 100, 100], fov: 50 }}
          onCreated={handleCanvasCreated}
          gl={{ 
            antialias: true,
            alpha: false,
            powerPreference: 'default',
            failIfMajorPerformanceCaveat: false,
          }}
        >
          <Suspense fallback={<LoadingIndicator />}>
            {/* Lighting - adjusted for dark mode */}
            <ambientLight intensity={isDarkMode ? 0.5 : 0.4} />
            <directionalLight
              position={[50, 50, 25]}
              intensity={isDarkMode ? 1.2 : 1}
              castShadow
              shadow-mapSize={[1024, 1024]}
          />
          <directionalLight position={[-50, 50, -25]} intensity={isDarkMode ? 0.6 : 0.5} />

          {/* Environment for reflections */}
          <Environment preset={isDarkMode ? 'night' : 'city'} />

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
              cellColor={gridColors.cellColor}
              sectionSize={50}
              sectionThickness={1}
              sectionColor={gridColors.sectionColor}
              fadeDistance={400}
              fadeStrength={1}
              followCamera={false}
              infiniteGrid
            />
          )}

          {/* Axes Helper with Origin Indicator */}
          {showAxes && (
            <group>
              {/* Standard axes helper */}
              <axesHelper args={[60]} />
              {/* Origin sphere */}
              <mesh position={[0, 0, 0]}>
                <sphereGeometry args={[1.5, 16, 16]} />
                <meshBasicMaterial color="#ffffff" opacity={0.8} transparent />
              </mesh>
              {/* Axis labels using Html */}
              <Html position={[65, 0, 0]} center style={{ pointerEvents: 'none' }}>
                <span className="text-red-500 font-bold text-sm bg-white/80 dark:bg-gray-800/80 px-1 rounded">X</span>
              </Html>
              <Html position={[0, 65, 0]} center style={{ pointerEvents: 'none' }}>
                <span className="text-green-500 font-bold text-sm bg-white/80 dark:bg-gray-800/80 px-1 rounded">Y</span>
              </Html>
              <Html position={[0, 0, 65]} center style={{ pointerEvents: 'none' }}>
                <span className="text-blue-500 font-bold text-sm bg-white/80 dark:bg-gray-800/80 px-1 rounded">Z</span>
              </Html>
            </group>
          )}

          {/* Controls */}
          <OrbitControls
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            ref={controlsRef as any}
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
          className="p-2 bg-white dark:bg-gray-800 rounded-lg shadow-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          title="Reset view"
        >
          <RotateCcw className="h-4 w-4 text-gray-600 dark:text-gray-400" />
        </button>
        <button
          onClick={zoomIn}
          className="p-2 bg-white dark:bg-gray-800 rounded-lg shadow-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          title="Zoom in"
        >
          <ZoomIn className="h-4 w-4 text-gray-600 dark:text-gray-400" />
        </button>
        <button
          onClick={zoomOut}
          className="p-2 bg-white dark:bg-gray-800 rounded-lg shadow-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          title="Zoom out"
        >
          <ZoomOut className="h-4 w-4 text-gray-600 dark:text-gray-400" />
        </button>
      </div>

      {/* Loading overlay */}
      {isLoading && (stlUrl || stlData) && (
        <div className="absolute inset-0 flex items-center justify-center bg-white/50 dark:bg-gray-800/50">
          <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span>Loading model...</span>
          </div>
        </div>
      )}
      </div>
    </WebGLErrorBoundary>
  );
}

export default ModelViewer;
