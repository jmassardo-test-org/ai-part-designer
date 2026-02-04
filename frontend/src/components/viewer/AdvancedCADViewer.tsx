/**
 * Advanced CAD Viewer component.
 *
 * Enhanced 3D viewer with measurement, cross-section, render modes,
 * annotations, and screenshot capabilities.
 */

import {
  OrbitControls,
  Center,
  Grid,
  Environment,
  Html,
} from '@react-three/drei';
import { Canvas } from '@react-three/fiber';
import { 
  Loader2, 
  RotateCcw, 
  ZoomIn, 
  ZoomOut,
  Maximize2,
  Minimize2,
} from 'lucide-react';
import { Suspense, useRef, useState, useEffect, useCallback } from 'react';
import * as THREE from 'three';
import { STLLoader } from 'three-stdlib';

// Import tools
import {
  AnnotationListPanel,
  AnnotationMarkers,
  AnnotationPicker,
  AnnotationForm,
  useAnnotations,
} from './AnnotationTool';
import {
  CrossSectionToolbar,
  CrossSectionOverlay,
  useCrossSection,
} from './CrossSectionTool';
import {
  MeasurementToolbar,
  MeasurementPicker,
  MeasurementOverlay,
  useMeasurements,
} from './MeasurementTool';
import {
  RenderModeToolbar,
  RenderModeApplicator,
  useRenderMode,
} from './RenderModeTool';
import {
  ScreenshotToolbar,
  ScreenshotCapture,
  useScreenshot,
} from './ScreenshotTool';

// Types imported from annotation API when needed

interface AdvancedCADViewerProps {
  /** URL to the STL file */
  stlUrl?: string;
  /** Raw STL data as ArrayBuffer */
  stlData?: ArrayBuffer;
  /** Design ID for annotations */
  designId?: string;
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
  /** Show measurement tool */
  showMeasurementTool?: boolean;
  /** Show cross-section tool */
  showCrossSectionTool?: boolean;
  /** Show render mode tool */
  showRenderModeTool?: boolean;
  /** Show annotations */
  showAnnotations?: boolean;
  /** Show screenshot tool */
  showScreenshotTool?: boolean;
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
  onBoundsUpdate,
}: {
  url?: string;
  data?: ArrayBuffer;
  color?: string;
  onLoad?: () => void;
  onError?: (error: Error) => void;
  onBoundsUpdate?: (min: THREE.Vector3, max: THREE.Vector3) => void;
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
      const scale = 100 / maxDim;
      geo.scale(scale, scale, scale);

      // Recompute bounds after scaling
      geo.computeBoundingBox();
      if (onBoundsUpdate && geo.boundingBox) {
        onBoundsUpdate(geo.boundingBox.min, geo.boundingBox.max);
      }

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
      <div className="flex flex-col items-center gap-2 text-gray-500 dark:text-gray-400">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="text-sm">Loading model...</span>
      </div>
    </Html>
  );
}

/**
 * Camera controller for programmatic camera control.
 * Reserved for future advanced camera controls.
 */
function CameraController({
  controlsRef: _controlsRef,
}: {
  controlsRef: React.RefObject<any>;
}) {
  return null;
}

/**
 * Advanced CAD Viewer with integrated tools.
 */
export function AdvancedCADViewer({
  stlUrl,
  stlData,
  designId,
  color = '#3b82f6',
  showGrid = true,
  showAxes = false,
  backgroundColor = '#f8fafc',
  onLoad,
  onError,
  showMeasurementTool = true,
  showCrossSectionTool = true,
  showRenderModeTool = true,
  showAnnotations = true,
  showScreenshotTool = true,
  className = '',
}: AdvancedCADViewerProps) {
  const controlsRef = useRef<any>(null);
  const originalMaterialsRef = useRef(new Map());
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Tool hooks
  const measurements = useMeasurements();
  const crossSection = useCrossSection();
  const renderMode = useRenderMode();
  const annotations = useAnnotations(designId || '');
  const screenshot = useScreenshot();

  const handleLoad = useCallback(() => {
    setIsLoading(false);
    onLoad?.();
  }, [onLoad]);

  const handleError = useCallback((err: Error) => {
    setIsLoading(false);
    setError(err);
    onError?.(err);
  }, [onError]);

  const handleBoundsUpdate = useCallback((min: THREE.Vector3, max: THREE.Vector3) => {
    crossSection.updateBounds(min, max);
  }, [crossSection.updateBounds]);

  const resetView = () => {
    if (controlsRef.current) {
      controlsRef.current.reset();
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

  const toggleFullscreen = useCallback(() => {
    if (!containerRef.current) return;

    if (!isFullscreen) {
      containerRef.current.requestFullscreen?.();
    } else {
      document.exitFullscreen?.();
    }
  }, [isFullscreen]);

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(document.fullscreenElement === containerRef.current);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

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

  return (
    <div ref={containerRef} className={`relative h-full w-full ${className}`}>
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
                onBoundsUpdate={handleBoundsUpdate}
              />
            )}
          </Center>

          {/* Render mode applicator */}
          <RenderModeApplicator
            config={renderMode.config}
            originalMaterials={originalMaterialsRef}
          />

          {/* Cross-section overlay */}
          {crossSection.crossSectionEnabled && (
            <CrossSectionOverlay
              clipPlanes={crossSection.clipPlanes}
              showPlaneHelpers={crossSection.showHelpers}
            />
          )}

          {/* Measurement overlay */}
          <MeasurementOverlay measurements={measurements.measurements} />

          {/* Measurement picker */}
          <MeasurementPicker
            enabled={measurements.measurementEnabled}
            measurementType={measurements.measurementType}
            onMeasurementComplete={measurements.addMeasurement}
            unit={measurements.unit}
          />

          {/* Annotation markers */}
          {showAnnotations && designId && (
            <AnnotationMarkers
              annotations={annotations.annotations}
              selectedId={annotations.selectedAnnotationId}
              onSelect={annotations.selectAnnotation}
            />
          )}

          {/* Annotation picker */}
          {showAnnotations && designId && (
            <AnnotationPicker
              enabled={annotations.isAddingAnnotation}
              onPick={annotations.handlePick}
            />
          )}

          {/* Screenshot capture setup */}
          <ScreenshotCapture onReady={screenshot.setCaptureFunctions} />

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

      {/* Tool panels - Left side */}
      <div className="absolute top-4 left-4 flex flex-col gap-2">
        {showMeasurementTool && (
          <MeasurementToolbar
            enabled={measurements.measurementEnabled}
            onToggle={measurements.toggleMeasurement}
            measurementType={measurements.measurementType}
            onTypeChange={measurements.setMeasurementType}
            measurements={measurements.measurements}
            onClear={measurements.clearMeasurements}
            onExport={measurements.exportMeasurements}
            unit={measurements.unit}
            onUnitChange={measurements.setUnit}
          />
        )}

        {showCrossSectionTool && (
          <CrossSectionToolbar
            enabled={crossSection.crossSectionEnabled}
            onToggle={crossSection.toggleCrossSection}
            clipPlanes={crossSection.clipPlanes}
            onAddPlane={crossSection.addClipPlane}
            onRemovePlane={crossSection.removeClipPlane}
            onUpdatePlane={crossSection.updateClipPlane}
            showHelpers={crossSection.showHelpers}
            onToggleHelpers={crossSection.toggleHelpers}
            bounds={crossSection.bounds}
          />
        )}

        {showRenderModeTool && (
          <RenderModeToolbar
            mode={renderMode.mode}
            onModeChange={renderMode.setMode}
            config={renderMode.config}
            onConfigChange={renderMode.updateConfig}
          />
        )}
      </div>

      {/* Screenshot tool - Top right */}
      {showScreenshotTool && (
        <div className="absolute top-4 right-4">
          <ScreenshotToolbar
            onCapture={screenshot.handleCapture}
            isCapturing={screenshot.isCapturing}
          />
        </div>
      )}

      {/* Annotations panel - Right side */}
      {showAnnotations && designId && (
        <div className="absolute top-20 right-4">
          <AnnotationListPanel
            annotations={annotations.annotations}
            selectedId={annotations.selectedAnnotationId}
            onSelect={annotations.selectAnnotation}
            onFilterChange={annotations.setFilter}
            filter={annotations.filter}
            onAddClick={annotations.startAddingAnnotation}
          />
        </div>
      )}

      {/* Annotation form popup */}
      {annotations.pendingPosition && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/20">
          <AnnotationForm
            position={annotations.pendingPosition}
            onSubmit={annotations.createAnnotation}
            onCancel={annotations.cancelAddingAnnotation}
          />
        </div>
      )}

      {/* Control buttons - Bottom right */}
      <div className="absolute bottom-4 right-4 flex gap-2">
        <button
          onClick={toggleFullscreen}
          className="p-2 bg-white dark:bg-gray-800 rounded-lg shadow-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
        >
          {isFullscreen ? (
            <Minimize2 className="h-4 w-4 text-gray-600 dark:text-gray-400" />
          ) : (
            <Maximize2 className="h-4 w-4 text-gray-600 dark:text-gray-400" />
          )}
        </button>
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
  );
}

export default AdvancedCADViewer;
