/**
 * CAD v2 Generation Page.
 *
 * Uses the v2 API with EnclosureSpec schema for intelligent enclosure generation.
 * Supports remix mode when navigating from a starter design.
 */

import {
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Download,
  GitFork,
  Lightbulb,
  Loader2,
  Package,
  Plus,
  RotateCcw,
  Save,
  Sparkles,
  Trash2,
  Wand2,
} from 'lucide-react';
import { useCallback, useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ModelViewer } from '@/components/viewer';
import { useAuth } from '@/contexts/AuthContext';
import {
  useGenerateV2,
  usePreviewSchema,
  useCompileEnclosure,
  useSaveDesignV2,
} from '@/hooks/useGenerateV2';
import {
  createEnclosureSpec,
  addVentilation,
  addLid,
  getDownloadUrl,
} from '@/lib/generate-v2';
import type {
  EnclosureSpec,
  GenerateV2Response,
  CompileResponse,
} from '@/types/cad-v2';

// Example prompts for v2 enclosure generation
const EXAMPLE_PROMPTS = [
  'Create an enclosure for a Raspberry Pi 4 with ventilation on the sides and a snap-fit lid',
  'Box 150x100x60mm with honeycomb ventilation, screw-on lid with 4 M3 screws',
  'Compact case for Arduino Nano with USB port cutout on front',
  'Electronics enclosure 200x150x80mm with PCB standoffs and cable routing channels',
  'Waterproof junction box 120x80x40mm with cable glands on both sides',
];

// Dimension presets
const DIMENSION_PRESETS = [
  { name: 'Small', width: 80, depth: 60, height: 30 },
  { name: 'Medium', width: 120, depth: 80, height: 50 },
  { name: 'Large', width: 200, depth: 150, height: 80 },
  { name: 'Pi Case', width: 95, depth: 65, height: 35 },
  { name: 'Arduino', width: 75, depth: 55, height: 30 },
];

type GenerationMode = 'ai' | 'manual';

// Feature types for cutouts/ports
type FeatureSide = 'front' | 'back' | 'left' | 'right' | 'top' | 'bottom';

interface PortFeature {
  id: string;
  type: 'usb_c' | 'usb_a' | 'hdmi' | 'ethernet' | 'power_jack' | 'sd_card' | 'audio' | 'custom';
  side: FeatureSide;
  label: string;
}

// Common port presets
const PORT_PRESETS: Array<{ type: PortFeature['type']; label: string; width: number; height: number }> = [
  { type: 'usb_c', label: 'USB-C', width: 9, height: 3.5 },
  { type: 'usb_a', label: 'USB-A', width: 13, height: 6 },
  { type: 'hdmi', label: 'HDMI', width: 15, height: 6 },
  { type: 'ethernet', label: 'Ethernet', width: 16, height: 13.5 },
  { type: 'power_jack', label: 'Power Jack', width: 9, height: 11 },
  { type: 'sd_card', label: 'SD Card', width: 12, height: 2 },
  { type: 'audio', label: 'Audio Jack', width: 6, height: 6 },
];

// Location state for remix mode
interface RemixLocationState {
  remixMode?: boolean;
  enclosureSpec?: EnclosureSpec;
  remixedFrom?: {
    id: string;
    name: string;
  };
  designId?: string;
  designName?: string;
}

export function GeneratePageV2() {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const locationState = location.state as RemixLocationState | null;

  // Remix state
  const [isRemixMode, setIsRemixMode] = useState(false);
  const [remixedFrom, setRemixedFrom] = useState<{ id: string; name: string } | null>(null);
  const [, setCurrentDesignId] = useState<string | null>(null);

  // Generation mode
  const [mode, setMode] = useState<GenerationMode>('ai');

  // AI mode state
  const [description, setDescription] = useState('');

  // Manual mode state
  const [width, setWidth] = useState(120);
  const [depth, setDepth] = useState(80);
  const [height, setHeight] = useState(50);
  const [wallThickness, setWallThickness] = useState(2);
  const [cornerRadius, setCornerRadius] = useState(3);
  const [lidType, setLidType] = useState<'snap_fit' | 'screw_on' | 'hinged'>('snap_fit');
  const [hasVentilation, setHasVentilation] = useState(true);
  const [ventPattern, setVentPattern] = useState<'slots' | 'honeycomb' | 'circular'>('slots');
  const [features, setFeatures] = useState<PortFeature[]>([]);

  // UI state
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [saveName, setSaveName] = useState('');
  const [saveDescription, setSaveDescription] = useState('');

  // Results
  const [result, setResult] = useState<GenerateV2Response | CompileResponse | null>(null);
  const [generatedSpec, setGeneratedSpec] = useState<EnclosureSpec | null>(null);

  // Hooks
  const generateV2 = useGenerateV2();
  const previewSchema = usePreviewSchema();
  const compileEnclosure = useCompileEnclosure();
  const saveDesign = useSaveDesignV2();

  // Handle remix mode from navigation
  useEffect(() => {
    if (locationState?.remixMode && locationState.enclosureSpec) {
      setIsRemixMode(true);
      setGeneratedSpec(locationState.enclosureSpec);
      
      if (locationState.remixedFrom) {
        setRemixedFrom(locationState.remixedFrom);
      }
      
      if (locationState.designId) {
        setCurrentDesignId(locationState.designId);
      }
      
      if (locationState.designName) {
        setSaveName(locationState.designName);
      }

      // Pre-fill description to guide the user
      setDescription(`This is a remix of "${locationState.remixedFrom?.name || 'a starter design'}". What changes would you like to make?`);
      
      // Extract dimensions from spec to populate manual mode
      const spec = locationState.enclosureSpec;
      if (spec.exterior) {
        setWidth(spec.exterior.width?.value || 120);
        setDepth(spec.exterior.depth?.value || 80);
        setHeight(spec.exterior.height?.value || 50);
      }
      if (spec.walls?.thickness) {
        setWallThickness(spec.walls.thickness.value || 2);
      }
      if (spec.corner_radius) {
        setCornerRadius(spec.corner_radius.value || 3);
      }
      if (spec.lid?.type) {
        setLidType(spec.lid.type as 'snap_fit' | 'screw_on' | 'hinged');
      }
      if (spec.ventilation?.enabled) {
        setHasVentilation(true);
        if (spec.ventilation.pattern) {
          setVentPattern(spec.ventilation.pattern as 'slots' | 'honeycomb' | 'circular');
        }
      }

      // Auto-compile to show the 3D preview
      compileEnclosure.mutateAsync({ 
        enclosure_schema: locationState.enclosureSpec,
        export_format: 'stl',
      }).then((response) => {
        setResult(response);
      }).catch(console.error);
    }
  }, []); // Only run once on mount

  const isGenerating =
    generateV2.isPending || previewSchema.isPending || compileEnclosure.isPending;

  // Feature management
  const addFeature = useCallback((type: PortFeature['type'], side: FeatureSide = 'front') => {
    const preset = PORT_PRESETS.find((p) => p.type === type);
    const newFeature: PortFeature = {
      id: `${type}-${Date.now()}`,
      type,
      side,
      label: preset?.label || type,
    };
    setFeatures((prev) => [...prev, newFeature]);
  }, []);

  const removeFeature = useCallback((id: string) => {
    setFeatures((prev) => prev.filter((f) => f.id !== id));
  }, []);

  const updateFeatureSide = useCallback((id: string, side: FeatureSide) => {
    setFeatures((prev) =>
      prev.map((f) => (f.id === id ? { ...f, side } : f))
    );
  }, []);

  // Build spec from manual inputs
  const buildSpecFromInputs = useCallback((): EnclosureSpec => {
    let spec = createEnclosureSpec(width, depth, height, {
      walls: { thickness: { value: wallThickness } },
      corner_radius: { value: cornerRadius },
    });

    if (hasVentilation) {
      spec = addVentilation(spec, {
        pattern: ventPattern,
        sides: ['left', 'right'],
      });
    }

    spec = addLid(spec, lidType);

    // Add port features as cutouts
    if (features.length > 0) {
      const featureSpecs = features.map((f) => {
        const preset = PORT_PRESETS.find((p) => p.type === f.type);
        return {
          type: 'port' as const,
          port_type: f.type,
          face: f.side,
          width: { value: preset?.width || 10, unit: 'mm' as const },
          height: { value: preset?.height || 5, unit: 'mm' as const },
          position: { x: 0, y: 0 }, // Centered by default
        };
      });
      spec = { ...spec, features: featureSpecs };
    }

    return spec;
  }, [width, depth, height, wallThickness, cornerRadius, lidType, hasVentilation, ventPattern, features]);

  // Handle AI generation - navigates to chat view
  const handleAIGenerate = useCallback(() => {
    if (!description.trim()) return;

    // Navigate to create page with the description as initial prompt
    // The create page has a full chat interface for iterating on the design
    navigate('/create', {
      state: {
        initialPrompt: description.trim(),
        // Pass remix context if available
        ...(isRemixMode && remixedFrom && {
          remixMode: true,
          remixedFrom,
          enclosureSpec: generatedSpec,
        }),
      },
    });
  }, [description, navigate, isRemixMode, remixedFrom, generatedSpec]);

  // Handle manual compile
  const handleManualCompile = useCallback(async () => {
    const spec = buildSpecFromInputs();
    setGeneratedSpec(spec);

    try {
      const response = await compileEnclosure.mutateAsync({ 
        enclosure_schema: spec,
        export_format: 'stl',
      });
      setResult(response);
    } catch {
      // Error is handled by the hook
    }
  }, [buildSpecFromInputs, compileEnclosure]);

  // Handle preview schema
  const handlePreview = useCallback(async () => {
    if (mode === 'ai' && !description.trim()) return;

    try {
      if (mode === 'ai') {
        const preview = await previewSchema.mutateAsync({ description: description.trim() });
        if (preview.generated_schema) {
          setGeneratedSpec(preview.generated_schema);
        }
      } else {
        const spec = buildSpecFromInputs();
        setGeneratedSpec(spec);
      }
    } catch {
      // Error is handled by the hook
    }
  }, [mode, description, buildSpecFromInputs, previewSchema]);

  // Reset form
  const handleReset = () => {
    setDescription('');
    setResult(null);
    setGeneratedSpec(null);
    generateV2.reset();
    previewSchema.reset();
    compileEnclosure.reset();
  };

  // Apply dimension preset
  const applyPreset = (preset: (typeof DIMENSION_PRESETS)[0]) => {
    setWidth(preset.width);
    setDepth(preset.depth);
    setHeight(preset.height);
  };

  // Handle save to project
  const handleSaveToProject = useCallback(async () => {
    if (!result || !('job_id' in result) || !saveName.trim()) return;

    try {
      await saveDesign.mutateAsync({
        job_id: result.job_id,
        name: saveName.trim(),
        description: saveDescription.trim() || undefined,
        tags: [],
      });
      setShowSaveDialog(false);
      setSaveName('');
      setSaveDescription('');
      // Show success message (could use toast)
      alert('Design saved successfully!');
    } catch {
      // Error is handled by the hook
    }
  }, [result, saveName, saveDescription, saveDesign]);

  // Current error from any hook
  const error =
    generateV2.error?.message ||
    previewSchema.error?.message ||
    compileEnclosure.error?.message ||
    saveDesign.error?.message;

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="h-10 w-10 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg flex items-center justify-center">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Generate Enclosure
          </h1>
          <span className="px-2 py-0.5 text-xs font-medium bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-300 rounded-full">
            v2
          </span>
        </div>
        <p className="text-gray-600 dark:text-gray-400">
          Create professional enclosures using AI or manual configuration.
        </p>
      </div>

      {/* Remix Banner */}
      {isRemixMode && remixedFrom && (
        <div className="mb-6 p-4 bg-gradient-to-r from-primary-50 to-primary-100 dark:from-primary-900/30 dark:to-primary-800/30 border border-primary-200 dark:border-primary-700 rounded-lg">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 bg-primary-500 rounded-full flex items-center justify-center">
              <GitFork className="h-4 w-4 text-white" />
            </div>
            <div>
              <p className="font-medium text-primary-900 dark:text-primary-100">
                Remixing: {remixedFrom.name}
              </p>
              <p className="text-sm text-primary-700 dark:text-primary-300">
                The design is loaded below. Use the AI chat to describe your changes, or switch to manual mode to adjust parameters directly.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Mode Toggle */}
      <div className="mb-6">
        <div className="inline-flex rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-100 dark:bg-gray-800 p-1">
          <button
            onClick={() => setMode('ai')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              mode === 'ai'
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
            }`}
          >
            <div className="flex items-center gap-2">
              <Wand2 className="h-4 w-4" />
              AI Description
            </div>
          </button>
          <button
            onClick={() => setMode('manual')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              mode === 'manual'
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
            }`}
          >
            <div className="flex items-center gap-2">
              <Package className="h-4 w-4" />
              Manual Config
            </div>
          </button>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-8">
        {/* Left Column: Input */}
        <div className="space-y-6">
          {mode === 'ai' ? (
            <>
              {/* AI Description Input */}
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <label className="block font-medium text-gray-900 dark:text-gray-100 mb-2">
                  Describe your enclosure
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g., Create an enclosure for Raspberry Pi 4 with ventilation and snap-fit lid"
                  rows={4}
                  className="w-full px-4 py-3 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none placeholder:text-gray-400 dark:placeholder:text-gray-500"
                  disabled={isGenerating}
                />

                <div className="mt-4 flex items-center justify-between">
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    {description.length}/2000
                  </span>

                  <div className="flex items-center gap-2">
                    {description && (
                      <button
                        onClick={handleReset}
                        className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
                        disabled={isGenerating}
                      >
                        <RotateCcw className="h-4 w-4" />
                        Clear
                      </button>
                    )}
                    <button
                      onClick={handlePreview}
                      disabled={isGenerating || !description.trim()}
                      className="flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
                    >
                      Preview Schema
                    </button>
                    <button
                      onClick={handleAIGenerate}
                      disabled={isGenerating || !description.trim()}
                      className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {generateV2.isPending ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Generating...
                        </>
                      ) : (
                        <>
                          <Wand2 className="h-4 w-4" />
                          Generate
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>

              {/* Example Prompts */}
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Lightbulb className="h-5 w-5 text-amber-500" />
                  <h3 className="font-medium text-gray-900 dark:text-gray-100">
                    Example Prompts
                  </h3>
                </div>
                <div className="space-y-2">
                  {EXAMPLE_PROMPTS.map((prompt, index) => (
                    <button
                      key={index}
                      onClick={() => setDescription(prompt)}
                      disabled={isGenerating}
                      className="w-full text-left p-3 text-sm text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors disabled:opacity-50"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <>
              {/* Manual Configuration */}
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-4">
                  Dimensions
                </h3>

                {/* Presets */}
                <div className="flex flex-wrap gap-2 mb-4">
                  {DIMENSION_PRESETS.map((preset) => (
                    <button
                      key={preset.name}
                      onClick={() => applyPreset(preset)}
                      className="px-3 py-1 text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full hover:bg-gray-200 dark:hover:bg-gray-600"
                    >
                      {preset.name}
                    </button>
                  ))}
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">
                      Width (mm)
                    </label>
                    <input
                      type="number"
                      value={width}
                      onChange={(e) => setWidth(Number(e.target.value))}
                      min={20}
                      max={500}
                      className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">
                      Depth (mm)
                    </label>
                    <input
                      type="number"
                      value={depth}
                      onChange={(e) => setDepth(Number(e.target.value))}
                      min={20}
                      max={500}
                      className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">
                      Height (mm)
                    </label>
                    <input
                      type="number"
                      value={height}
                      onChange={(e) => setHeight(Number(e.target.value))}
                      min={10}
                      max={300}
                      className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg"
                    />
                  </div>
                </div>
              </div>

              {/* Features */}
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-4">Features</h3>

                <div className="space-y-4">
                  {/* Wall Thickness */}
                  <div>
                    <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">
                      Wall Thickness (mm)
                    </label>
                    <input
                      type="range"
                      value={wallThickness}
                      onChange={(e) => setWallThickness(Number(e.target.value))}
                      min={1}
                      max={5}
                      step={0.5}
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-gray-500">
                      <span>1mm</span>
                      <span className="font-medium">{wallThickness}mm</span>
                      <span>5mm</span>
                    </div>
                  </div>

                  {/* Corner Radius */}
                  <div>
                    <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">
                      Corner Radius (mm)
                    </label>
                    <input
                      type="range"
                      value={cornerRadius}
                      onChange={(e) => setCornerRadius(Number(e.target.value))}
                      min={0}
                      max={10}
                      step={0.5}
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-gray-500">
                      <span>0mm</span>
                      <span className="font-medium">{cornerRadius}mm</span>
                      <span>10mm</span>
                    </div>
                  </div>

                  {/* Lid Type */}
                  <div>
                    <label className="block text-sm text-gray-600 dark:text-gray-400 mb-2">
                      Lid Type
                    </label>
                    <div className="flex gap-2">
                      {(['snap_fit', 'screw_on', 'hinged'] as const).map((type) => (
                        <button
                          key={type}
                          onClick={() => setLidType(type)}
                          className={`flex-1 py-2 px-3 text-sm rounded-lg border ${
                            lidType === type
                              ? 'bg-primary-50 dark:bg-primary-900/30 border-primary-500 text-primary-700 dark:text-primary-300'
                              : 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                          }`}
                        >
                          {type.replace('_', ' ')}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Ventilation */}
                  <div>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={hasVentilation}
                        onChange={(e) => setHasVentilation(e.target.checked)}
                        className="h-4 w-4 text-primary-600 rounded"
                      />
                      <span className="text-sm text-gray-700 dark:text-gray-300">
                        Add ventilation
                      </span>
                    </label>

                    {hasVentilation && (
                      <div className="mt-2 flex gap-2 ml-6">
                        {(['slots', 'honeycomb', 'circular'] as const).map((pattern) => (
                          <button
                            key={pattern}
                            onClick={() => setVentPattern(pattern)}
                            className={`py-1 px-3 text-xs rounded-full border ${
                              ventPattern === pattern
                                ? 'bg-primary-50 dark:bg-primary-900/30 border-primary-500 text-primary-700 dark:text-primary-300'
                                : 'border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400'
                            }`}
                          >
                            {pattern}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Ports & Cutouts */}
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-medium text-gray-900 dark:text-gray-100">
                    Ports & Cutouts
                  </h3>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {features.length} added
                  </span>
                </div>

                {/* Add Port Buttons */}
                <div className="flex flex-wrap gap-2 mb-4">
                  {PORT_PRESETS.map((preset) => (
                    <button
                      key={preset.type}
                      onClick={() => addFeature(preset.type)}
                      className="flex items-center gap-1 px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
                    >
                      <Plus className="h-3 w-3" />
                      {preset.label}
                    </button>
                  ))}
                </div>

                {/* Added Features List */}
                {features.length > 0 && (
                  <div className="space-y-2">
                    {features.map((feature) => (
                      <div
                        key={feature.id}
                        className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-700 rounded-lg"
                      >
                        <span className="text-sm text-gray-700 dark:text-gray-300">
                          {feature.label}
                        </span>
                        <div className="flex items-center gap-2">
                          <select
                            value={feature.side}
                            onChange={(e) =>
                              updateFeatureSide(feature.id, e.target.value as FeatureSide)
                            }
                            className="text-xs px-2 py-1 bg-white dark:bg-gray-600 border border-gray-300 dark:border-gray-500 rounded"
                          >
                            <option value="front">Front</option>
                            <option value="back">Back</option>
                            <option value="left">Left</option>
                            <option value="right">Right</option>
                            <option value="top">Top</option>
                            <option value="bottom">Bottom</option>
                          </select>
                          <button
                            onClick={() => removeFeature(feature.id)}
                            className="p-1 text-gray-400 hover:text-red-500"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {features.length === 0 && (
                  <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-2">
                    Click buttons above to add ports/cutouts
                  </p>
                )}
              </div>

              {/* Generate Button */}
              <button
                onClick={handleManualCompile}
                disabled={isGenerating}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {compileEnclosure.isPending ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Compiling...
                  </>
                ) : (
                  <>
                    <Package className="h-5 w-5" />
                    Generate Enclosure
                  </>
                )}
              </button>
            </>
          )}

          {/* Error Display */}
          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-medium text-red-800 dark:text-red-200">
                    Generation Failed
                  </h4>
                  <p className="text-sm text-red-600 dark:text-red-300 mt-1">{error}</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Preview & Results */}
        <div className="space-y-6">
          {/* 3D Viewer */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="aspect-square bg-gray-50 dark:bg-gray-900">
              {result && 'success' in result && result.success && result.parts?.length > 0 ? (
                <ModelViewer
                  stlUrl={getDownloadUrl(result.job_id, `${result.parts[0]}.stl`)}
                />
              ) : (
                <div className="h-full flex items-center justify-center text-gray-400 dark:text-gray-500">
                  <div className="text-center">
                    <Package className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p className="text-sm">
                      {isGenerating ? 'Generating preview...' : 'Preview will appear here'}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Generated Spec */}
          {generatedSpec && (
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
              <button
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="w-full flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  Generated Schema
                </span>
                {showAdvanced ? (
                  <ChevronUp className="h-5 w-5 text-gray-400" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-gray-400" />
                )}
              </button>

              {showAdvanced && (
                <div className="border-t border-gray-200 dark:border-gray-700 p-4">
                  <pre className="text-xs text-gray-600 dark:text-gray-400 overflow-auto max-h-64">
                    {JSON.stringify(generatedSpec, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}

          {/* Download Buttons */}
          {result && 'success' in result && result.success && (
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-3">Downloads</h4>
              <div className="space-y-3">
                {result.parts?.map((part) => (
                  <div key={part} className="flex gap-2">
                    <a
                      href={getDownloadUrl(result.job_id, `${part}.step`)}
                      download
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
                    >
                      <Download className="h-4 w-4" />
                      {part}.step
                    </a>
                    <a
                      href={getDownloadUrl(result.job_id, `${part}.stl`)}
                      download
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
                    >
                      <Download className="h-4 w-4" />
                      {part}.stl
                    </a>
                  </div>
                ))}
              </div>

              {/* Save to Project */}
              {isAuthenticated && (
                <button
                  className="w-full mt-3 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                  onClick={() => setShowSaveDialog(true)}
                  disabled={saveDesign.isPending}
                >
                  <Save className="h-4 w-4" />
                  Save to Project
                </button>
              )}
            </div>
          )}

          {/* Save Dialog */}
          {showSaveDialog && result && 'job_id' in result && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
              <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md mx-4 shadow-xl">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                  Save to Project
                </h3>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Design Name *
                    </label>
                    <input
                      type="text"
                      value={saveName}
                      onChange={(e) => setSaveName(e.target.value)}
                      placeholder="My Enclosure"
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                      autoFocus
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Description (optional)
                    </label>
                    <textarea
                      value={saveDescription}
                      onChange={(e) => setSaveDescription(e.target.value)}
                      placeholder="Add a description..."
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 resize-none"
                    />
                  </div>
                </div>

                <div className="mt-6 flex gap-3 justify-end">
                  <button
                    onClick={() => {
                      setShowSaveDialog(false);
                      setSaveName('');
                      setSaveDescription('');
                    }}
                    className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                    disabled={saveDesign.isPending}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSaveToProject}
                    disabled={!saveName.trim() || saveDesign.isPending}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    {saveDesign.isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <Save className="h-4 w-4" />
                        Save
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
