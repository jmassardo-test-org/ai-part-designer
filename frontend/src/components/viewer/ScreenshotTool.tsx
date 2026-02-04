/**
 * Screenshot & Export Tool for 3D viewer.
 *
 * Captures the current view as an image with various options.
 */

import { useThree } from '@react-three/fiber';
import { Camera, Download, Settings, Image, FileImage } from 'lucide-react';
import { useState, useCallback, useRef } from 'react';
import * as THREE from 'three';

export type ImageFormat = 'png' | 'jpg';
export type ResolutionPreset = '1x' | '2x' | '4x' | 'hd' | 'fullhd' | '4k' | 'custom';

export interface ScreenshotOptions {
  format: ImageFormat;
  resolution: ResolutionPreset;
  customWidth?: number;
  customHeight?: number;
  transparentBackground: boolean;
  includeAnnotations: boolean;
  quality: number; // 0-1 for JPEG
}

const RESOLUTION_SIZES: Record<Exclude<ResolutionPreset, 'custom'>, { label: string; multiplier?: number; width?: number; height?: number }> = {
  '1x': { label: '1x (Current)', multiplier: 1 },
  '2x': { label: '2x', multiplier: 2 },
  '4x': { label: '4x', multiplier: 4 },
  'hd': { label: 'HD (1280×720)', width: 1280, height: 720 },
  'fullhd': { label: 'Full HD (1920×1080)', width: 1920, height: 1080 },
  '4k': { label: '4K (3840×2160)', width: 3840, height: 2160 },
};

// Screenshot tool props are defined inline in component

/**
 * Hook to capture screenshots from the Three.js canvas.
 */
export function useScreenshotCapture() {
  const { gl, scene, camera } = useThree();

  const capture = useCallback((options: ScreenshotOptions): string => {
    const canvas = gl.domElement;
    const originalWidth = canvas.width;
    const originalHeight = canvas.height;

    // Calculate target size
    let targetWidth = originalWidth;
    let targetHeight = originalHeight;

    if (options.resolution === 'custom') {
      targetWidth = options.customWidth || originalWidth;
      targetHeight = options.customHeight || originalHeight;
    } else {
      const preset = RESOLUTION_SIZES[options.resolution];
      if (preset.multiplier) {
        targetWidth = originalWidth * preset.multiplier;
        targetHeight = originalHeight * preset.multiplier;
      } else if (preset.width && preset.height) {
        targetWidth = preset.width;
        targetHeight = preset.height;
      }
    }

    // Create offscreen canvas
    const offscreenCanvas = document.createElement('canvas');
    offscreenCanvas.width = targetWidth;
    offscreenCanvas.height = targetHeight;

    // Create offscreen renderer
    const offscreenRenderer = new THREE.WebGLRenderer({
      canvas: offscreenCanvas,
      antialias: true,
      alpha: options.transparentBackground,
      preserveDrawingBuffer: true,
    });
    offscreenRenderer.setSize(targetWidth, targetHeight);
    offscreenRenderer.setPixelRatio(1);

    // Set background
    if (!options.transparentBackground) {
      offscreenRenderer.setClearColor(0xf8fafc, 1); // Light gray background
    } else {
      offscreenRenderer.setClearColor(0x000000, 0);
    }

    // Update camera aspect ratio
    const originalAspect = (camera as THREE.PerspectiveCamera).aspect;
    (camera as THREE.PerspectiveCamera).aspect = targetWidth / targetHeight;
    (camera as THREE.PerspectiveCamera).updateProjectionMatrix();

    // Render
    offscreenRenderer.render(scene, camera);

    // Get data URL
    const mimeType = options.format === 'jpg' ? 'image/jpeg' : 'image/png';
    const quality = options.format === 'jpg' ? options.quality : undefined;
    const dataUrl = offscreenCanvas.toDataURL(mimeType, quality);

    // Restore camera
    (camera as THREE.PerspectiveCamera).aspect = originalAspect;
    (camera as THREE.PerspectiveCamera).updateProjectionMatrix();

    // Cleanup
    offscreenRenderer.dispose();

    return dataUrl;
  }, [gl, scene, camera]);

  const download = useCallback((dataUrl: string, filename: string) => {
    const link = document.createElement('a');
    link.href = dataUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, []);

  return { capture, download };
}

interface ScreenshotToolbarProps {
  onCapture: (options: ScreenshotOptions) => void;
  isCapturing: boolean;
}

/**
 * UI toolbar for screenshot controls.
 */
export function ScreenshotToolbar({ onCapture, isCapturing }: ScreenshotToolbarProps) {
  const [showOptions, setShowOptions] = useState(false);
  const [options, setOptions] = useState<ScreenshotOptions>({
    format: 'png',
    resolution: '2x',
    transparentBackground: false,
    includeAnnotations: true,
    quality: 0.92,
  });

  const handleQuickCapture = () => {
    onCapture(options);
  };

  const updateOption = <K extends keyof ScreenshotOptions>(
    key: K,
    value: ScreenshotOptions[K]
  ) => {
    setOptions((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="flex flex-col gap-2 p-2 bg-white rounded-lg shadow-lg min-w-[180px]">
      {/* Quick capture button */}
      <div className="flex items-center gap-2">
        <button
          onClick={handleQuickCapture}
          disabled={isCapturing}
          className={`
            flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg
            ${isCapturing
              ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
              : 'bg-blue-500 text-white hover:bg-blue-600'}
          `}
        >
          <Camera className="h-4 w-4" />
          <span className="text-sm">{isCapturing ? 'Capturing...' : 'Capture'}</span>
        </button>
        <button
          onClick={() => setShowOptions(!showOptions)}
          className={`
            p-2 rounded-lg transition-colors
            ${showOptions ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}
          `}
        >
          <Settings className="h-4 w-4" />
        </button>
      </div>

      {/* Options panel */}
      {showOptions && (
        <div className="border-t pt-2 space-y-3">
          {/* Format */}
          <div>
            <label className="text-[10px] text-gray-500 uppercase tracking-wide mb-1 block">
              Format
            </label>
            <div className="flex gap-1">
              <button
                onClick={() => updateOption('format', 'png')}
                className={`
                  flex-1 flex items-center justify-center gap-1 px-2 py-1.5 text-xs rounded
                  ${options.format === 'png'
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-gray-50 text-gray-600 hover:bg-gray-100'}
                `}
              >
                <Image className="h-3 w-3" />
                PNG
              </button>
              <button
                onClick={() => updateOption('format', 'jpg')}
                className={`
                  flex-1 flex items-center justify-center gap-1 px-2 py-1.5 text-xs rounded
                  ${options.format === 'jpg'
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-gray-50 text-gray-600 hover:bg-gray-100'}
                `}
              >
                <FileImage className="h-3 w-3" />
                JPG
              </button>
            </div>
          </div>

          {/* Resolution */}
          <div>
            <label className="text-[10px] text-gray-500 uppercase tracking-wide mb-1 block">
              Resolution
            </label>
            <select
              value={options.resolution}
              onChange={(e) => updateOption('resolution', e.target.value as ResolutionPreset)}
              className="w-full text-xs p-1.5 border rounded bg-white"
            >
              {Object.entries(RESOLUTION_SIZES).map(([key, { label }]) => (
                <option key={key} value={key}>{label}</option>
              ))}
              <option value="custom">Custom...</option>
            </select>
          </div>

          {/* Custom resolution inputs */}
          {options.resolution === 'custom' && (
            <div className="flex gap-2">
              <div className="flex-1">
                <label className="text-[10px] text-gray-500 block mb-1">Width</label>
                <input
                  type="number"
                  value={options.customWidth || 1920}
                  onChange={(e) => updateOption('customWidth', parseInt(e.target.value))}
                  className="w-full text-xs p-1.5 border rounded"
                  min={100}
                  max={8192}
                />
              </div>
              <div className="flex-1">
                <label className="text-[10px] text-gray-500 block mb-1">Height</label>
                <input
                  type="number"
                  value={options.customHeight || 1080}
                  onChange={(e) => updateOption('customHeight', parseInt(e.target.value))}
                  className="w-full text-xs p-1.5 border rounded"
                  min={100}
                  max={8192}
                />
              </div>
            </div>
          )}

          {/* Quality (for JPEG) */}
          {options.format === 'jpg' && (
            <div>
              <label className="text-[10px] text-gray-500 uppercase tracking-wide mb-1 block">
                Quality: {Math.round(options.quality * 100)}%
              </label>
              <input
                type="range"
                min={0.5}
                max={1}
                step={0.05}
                value={options.quality}
                onChange={(e) => updateOption('quality', parseFloat(e.target.value))}
                className="w-full h-1"
              />
            </div>
          )}

          {/* Options */}
          <div className="space-y-2">
            <label className="flex items-center gap-2 text-xs text-gray-600 cursor-pointer">
              <input
                type="checkbox"
                checked={options.transparentBackground}
                onChange={(e) => updateOption('transparentBackground', e.target.checked)}
                className="rounded border-gray-300"
                disabled={options.format === 'jpg'}
              />
              Transparent background
              {options.format === 'jpg' && (
                <span className="text-gray-400">(PNG only)</span>
              )}
            </label>
            <label className="flex items-center gap-2 text-xs text-gray-600 cursor-pointer">
              <input
                type="checkbox"
                checked={options.includeAnnotations}
                onChange={(e) => updateOption('includeAnnotations', e.target.checked)}
                className="rounded border-gray-300"
              />
              Include annotations
            </label>
          </div>

          {/* Capture with current options */}
          <button
            onClick={handleQuickCapture}
            disabled={isCapturing}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-blue-500 text-white text-sm rounded-lg hover:bg-blue-600 disabled:opacity-50"
          >
            <Download className="h-4 w-4" />
            Download
          </button>
        </div>
      )}
    </div>
  );
}

/**
 * Hook to manage screenshot state.
 */
export function useScreenshot() {
  const [isCapturing, setIsCapturing] = useState(false);
  const [lastCapture, setLastCapture] = useState<string | null>(null);

  const captureRef = useRef<((options: ScreenshotOptions) => string) | null>(null);
  const downloadRef = useRef<((dataUrl: string, filename: string) => void) | null>(null);

  const setCaptureFunctions = useCallback((
    capture: (options: ScreenshotOptions) => string,
    download: (dataUrl: string, filename: string) => void
  ) => {
    captureRef.current = capture;
    downloadRef.current = download;
  }, []);

  const handleCapture = useCallback(async (options: ScreenshotOptions) => {
    if (!captureRef.current || !downloadRef.current) return;

    setIsCapturing(true);
    try {
      // Small delay to allow UI to update
      await new Promise((r) => setTimeout(r, 100));

      const dataUrl = captureRef.current(options);
      setLastCapture(dataUrl);

      // Generate filename
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
      const extension = options.format === 'jpg' ? 'jpg' : 'png';
      const filename = `screenshot-${timestamp}.${extension}`;

      downloadRef.current(dataUrl, filename);
    } finally {
      setIsCapturing(false);
    }
  }, []);

  return {
    isCapturing,
    lastCapture,
    handleCapture,
    setCaptureFunctions,
  };
}

/**
 * Component that sets up capture functions inside the Canvas.
 */
export function ScreenshotCapture({
  onReady,
}: {
  onReady: (
    capture: (options: ScreenshotOptions) => string,
    download: (dataUrl: string, filename: string) => void
  ) => void;
}) {
  const { capture, download } = useScreenshotCapture();

  // Report capture functions to parent
  useState(() => {
    onReady(capture, download);
  });

  return null;
}

export default ScreenshotToolbar;
