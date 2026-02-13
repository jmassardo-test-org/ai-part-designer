/**
 * Natural Language Part Generation Page.
 * 
 * Allows users to describe parts in natural language and generate CAD files.
 * Supports pre-filling from templates via URL state/params.
 */

import { 
  Wand2, 
  Download, 
  Loader2, 
  AlertCircle, 
  CheckCircle2,
  Lightbulb,
  RotateCcw,
  ChevronDown,
  ChevronUp,
  Copy,
  Sparkles,
  Package,
  ExternalLink,
  Layers,
  ArrowLeft
} from 'lucide-react';
import { useState, useCallback, useEffect } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { ModelViewer } from '@/components/viewer';
import { useAuth } from '@/contexts/AuthContext';
import { 
  generateFromDescription, 
  downloadGeneratedFile,
  getPreviewData,
  type GenerateResponse,
} from '@/lib/generate';

// Example prompts for user guidance
const EXAMPLE_PROMPTS = [
  "Create a box 100mm long, 50mm wide, and 30mm tall with 3mm fillets on all edges",
  "Make a cylinder 2 inches in diameter and 4 inches tall with a 10mm center hole",
  "Design a 60mm diameter sphere",
  "Build a mounting bracket: 80x60x3mm plate with four 5mm holes near the corners",
  "Create a 2-part enclosure 120x80x50mm with lid, gasket, and M3 mounting screws",
];

// Quality options for STL export
const QUALITY_OPTIONS = [
  { value: 'draft', label: 'Draft', description: 'Fast, lower detail' },
  { value: 'standard', label: 'Standard', description: 'Balanced quality' },
  { value: 'high', label: 'High', description: 'Detailed, larger files' },
  { value: 'ultra', label: 'Ultra', description: 'Maximum detail' },
] as const;

// Template context passed via navigation state
interface TemplateContext {
  templateName: string;
  templateSlug: string;
  templateDescription: string;
  parameters: Record<string, number | string | boolean>;
  suggestedPrompt: string;
}

export function GeneratePage() {
  const { token } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  
  // Get template context from navigation state (if coming from template page)
  const templateContext = location.state as TemplateContext | null;
  
  // Form state
  const [description, setDescription] = useState('');
  const [stlQuality, setStlQuality] = useState<'draft' | 'standard' | 'high' | 'ultra'>('standard');
  const [exportStep, setExportStep] = useState(true);
  const [exportStl, setExportStl] = useState(true);
  
  // Generation state
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [previewData, setPreviewData] = useState<ArrayBuffer | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // UI state
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [downloading, setDownloading] = useState<'step' | 'stl' | null>(null);

  // Pre-fill description from template context
  useEffect(() => {
    if (templateContext?.suggestedPrompt) {
      setDescription(templateContext.suggestedPrompt);
    }
  }, [templateContext]);

  // Handle generation
  const handleGenerate = useCallback(async () => {
    if (!description.trim()) {
      setError('Please enter a description');
      return;
    }

    setGenerating(true);
    setError(null);
    setResult(null);
    setPreviewData(null);

    try {
      const response = await generateFromDescription({
        description: description.trim(),
        export_step: exportStep,
        export_stl: exportStl,
        stl_quality: stlQuality,
      }, token || undefined);

      setResult(response);

      // Load preview if STL was generated
      if (response.downloads.stl) {
        try {
          const preview = await getPreviewData(response.job_id, (token || undefined)!);
          setPreviewData(preview);
        } catch (previewError) {
          console.error('Failed to load preview:', previewError);
          // Non-fatal - generation succeeded
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Generation failed');
    } finally {
      setGenerating(false);
    }
  }, [description, exportStep, exportStl, stlQuality, token]);

  // Handle file download
  const handleDownload = useCallback(async (format: 'step' | 'stl') => {
    if (!result) return;

    setDownloading(format);
    try {
      const blob = await downloadGeneratedFile(result.job_id, format, (token || undefined)!);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `generated-part.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      setError(`Failed to download ${format.toUpperCase()} file`);
    } finally {
      setDownloading(null);
    }
  }, [result, token]);

  // Use example prompt
  const handleExampleSelect = (prompt: string) => {
    setDescription(prompt);
    setError(null);
  };

  // Reset form
  const handleReset = () => {
    setDescription('');
    setResult(null);
    setPreviewData(null);
    setError(null);
  };

  // Format dimension value
  const formatDimension = (key: string, value: number) => {
    return `${key}: ${value.toFixed(1)}mm`;
  };

  return (
    <div className="max-w-7xl mx-auto">
      {/* Breadcrumb Navigation (when coming from template) */}
      {templateContext && (
        <nav className="mb-4 flex items-center gap-2 text-sm">
          <Link 
            to="/templates" 
            className="text-gray-500 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400"
          >
            Templates
          </Link>
          <span className="text-gray-400 dark:text-gray-500">/</span>
          <Link 
            to={`/templates/${templateContext.templateSlug}`}
            className="text-gray-500 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400"
          >
            {templateContext.templateName}
          </Link>
          <span className="text-gray-400 dark:text-gray-500">/</span>
          <span className="text-gray-900 dark:text-gray-100 font-medium">Customize with AI</span>
        </nav>
      )}
      
      {/* Back button (when coming from template) */}
      {templateContext && (
        <button
          onClick={() => navigate(`/templates/${templateContext.templateSlug}`)}
          className="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 mb-4"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to {templateContext.templateName}
        </button>
      )}
      
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="h-10 w-10 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg flex items-center justify-center">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {templateContext ? `Customize: ${templateContext.templateName}` : 'Generate Part'}
          </h1>
        </div>
        <p className="text-gray-600 dark:text-gray-400">
          {templateContext 
            ? `Modify the pre-filled description below to customize your ${templateContext.templateName}.`
            : 'Describe the part you want to create in natural language, and our AI will generate it for you.'
          }
        </p>
      </div>

      <div className="grid lg:grid-cols-2 gap-8">
        {/* Left Column: Input */}
        <div className="space-y-6">
          {/* Description Input */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <label className="block font-medium text-gray-900 dark:text-gray-100 mb-2">
              Describe your part
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g., Create a box 100mm long, 50mm wide, and 30mm tall with 3mm fillets on all edges"
              rows={5}
              className="w-full px-4 py-3 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none placeholder:text-gray-400 dark:placeholder:text-gray-500"
              disabled={generating}
            />
            
            <div className="mt-4 flex items-center justify-between">
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {description.length}/2000 characters
              </span>
              
              <div className="flex items-center gap-2">
                {description && (
                  <button
                    onClick={handleReset}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
                    disabled={generating}
                  >
                    <RotateCcw className="h-4 w-4" />
                    Clear
                  </button>
                )}
                <button
                  onClick={handleGenerate}
                  disabled={generating || !description.trim()}
                  className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {generating ? (
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
              <h3 className="font-medium text-gray-900 dark:text-gray-100">Example Prompts</h3>
            </div>
            <div className="space-y-2">
              {EXAMPLE_PROMPTS.map((prompt, index) => (
                <button
                  key={index}
                  onClick={() => handleExampleSelect(prompt)}
                  disabled={generating}
                  className="w-full text-left p-3 text-sm text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors disabled:opacity-50"
                >
                  <div className="flex items-start gap-2">
                    <Copy className="h-4 w-4 text-gray-400 dark:text-gray-500 flex-shrink-0 mt-0.5" />
                    <span>{prompt}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Advanced Options */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="w-full flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              <span className="font-medium text-gray-900 dark:text-gray-100">Advanced Options</span>
              {showAdvanced ? (
                <ChevronUp className="h-5 w-5 text-gray-400" />
              ) : (
                <ChevronDown className="h-5 w-5 text-gray-400" />
              )}
            </button>
            
            {showAdvanced && (
              <div className="border-t border-gray-200 dark:border-gray-700 p-4 space-y-4">
                {/* Export formats */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Export Formats
                  </label>
                  <div className="flex items-center gap-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={exportStep}
                        onChange={(e) => setExportStep(e.target.checked)}
                        className="h-4 w-4 text-primary-600 border-gray-300 dark:border-gray-600 rounded"
                      />
                      <span className="text-sm text-gray-700 dark:text-gray-300">STEP</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={exportStl}
                        onChange={(e) => setExportStl(e.target.checked)}
                        className="h-4 w-4 text-primary-600 border-gray-300 dark:border-gray-600 rounded"
                      />
                      <span className="text-sm text-gray-700 dark:text-gray-300">STL</span>
                    </label>
                  </div>
                </div>

                {/* STL Quality */}
                {exportStl && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      STL Quality
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      {QUALITY_OPTIONS.map((option) => (
                        <button
                          key={option.value}
                          onClick={() => setStlQuality(option.value)}
                          className={`p-3 rounded-lg border text-left transition-colors ${
                            stlQuality === option.value
                              ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30'
                              : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'
                          }`}
                        >
                          <p className="font-medium text-sm text-gray-900 dark:text-gray-100">{option.label}</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">{option.description}</p>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Results */}
        <div className="space-y-6">
          {/* Error Display */}
          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-red-800 dark:text-red-300">Generation Failed</p>
                <p className="text-sm text-red-700 dark:text-red-400 mt-1">{error}</p>
              </div>
            </div>
          )}

          {/* 3D Preview */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="h-[400px] relative">
              {generating ? (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-800">
                  <Loader2 className="h-12 w-12 animate-spin text-primary-600 mb-4" />
                  <p className="text-gray-600 dark:text-gray-300 font-medium">Generating your part...</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">This may take a few seconds</p>
                </div>
              ) : previewData ? (
                <ModelViewer 
                  stlData={previewData}
                  showGrid={true}
                  showAxes={true}
                  backgroundColor="#f9fafb"
                  className="h-full w-full"
                />
              ) : (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-800">
                  <Wand2 className="h-12 w-12 text-gray-300 dark:text-gray-600 mb-4" />
                  <p className="text-gray-500 dark:text-gray-400">3D preview will appear here</p>
                  <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">Enter a description and click Generate</p>
                </div>
              )}
            </div>
          </div>

          {/* Generation Results */}
          {result && (
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 space-y-4">
              {/* Success header */}
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center">
                  <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <p className="font-semibold text-gray-900 dark:text-gray-100">Part Generated Successfully</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {result.shape} • {result.confidence.toFixed(0)}% confidence
                  </p>
                </div>
              </div>

              {/* Dimensions */}
              <div>
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Extracted Dimensions</h4>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(result.dimensions).map(([key, value]) => (
                    <span
                      key={key}
                      className="px-3 py-1 bg-gray-100 dark:bg-gray-700 rounded-full text-sm text-gray-700 dark:text-gray-300"
                    >
                      {formatDimension(key, value as number)}
                    </span>
                  ))}
                </div>
              </div>

              {/* Assembly Parts */}
              {result.is_assembly && result.parts && result.parts.length > 0 && (
                <div className="border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Layers className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                    <h4 className="font-medium text-blue-900 dark:text-blue-300">Assembly Parts ({result.parts.length})</h4>
                  </div>
                  <div className="space-y-3">
                    {result.parts.map((part: { name: string; description: string; downloads: { step: string; stl: string } }, index: number) => (
                      <div key={index} className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-blue-100 dark:border-blue-800">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="font-medium text-gray-900 dark:text-gray-100">{part.name}</p>
                            <p className="text-sm text-gray-500 dark:text-gray-400">{part.description}</p>
                          </div>
                          <div className="flex gap-2">
                            <a
                              href={`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}${part.downloads.step}`}
                              className="flex items-center gap-1 px-2 py-1 text-xs bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded hover:bg-primary-200 dark:hover:bg-primary-900/50"
                            >
                              <Download className="h-3 w-3" />
                              STEP
                            </a>
                            <a
                              href={`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}${part.downloads.stl}`}
                              className="flex items-center gap-1 px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
                            >
                              <Download className="h-3 w-3" />
                              STL
                            </a>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Bill of Materials */}
              {result.is_assembly && result.bom && result.bom.length > 0 && (
                <div className="border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Package className="h-5 w-5 text-green-600 dark:text-green-400" />
                    <h4 className="font-medium text-green-900 dark:text-green-300">Bill of Materials</h4>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-green-800 dark:text-green-300">
                          <th className="pb-2">Item</th>
                          <th className="pb-2">Qty</th>
                          <th className="pb-2">Material</th>
                          <th className="pb-2">Supplier</th>
                        </tr>
                      </thead>
                      <tbody className="text-gray-700 dark:text-gray-300">
                        {result.bom.map((item: { name: string; quantity: number; material: string; supplier_url?: string; mcmaster_pn?: string }, index: number) => (
                          <tr key={index} className="border-t border-green-100 dark:border-green-800">
                            <td className="py-2">{item.name}</td>
                            <td className="py-2">{item.quantity}</td>
                            <td className="py-2">{item.material}</td>
                            <td className="py-2">
                              {item.supplier_url ? (
                                <a
                                  href={item.supplier_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="flex items-center gap-1 text-green-700 dark:text-green-400 hover:text-green-900 dark:hover:text-green-300"
                                >
                                  {item.mcmaster_pn || 'McMaster'}
                                  <ExternalLink className="h-3 w-3" />
                                </a>
                              ) : (
                                <span className="text-gray-400 dark:text-gray-500">—</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Warnings */}
              {result.warnings.length > 0 && (
                <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3">
                  <p className="text-sm font-medium text-amber-800 dark:text-amber-300 mb-1">Warnings</p>
                  <ul className="text-sm text-amber-700 dark:text-amber-400 space-y-1">
                    {result.warnings.map((warning: string, index: number) => (
                      <li key={index}>• {warning}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Timing */}
              <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-4">
                <span>Parse: {result.timing.parse_ms.toFixed(0)}ms</span>
                <span>Generate: {result.timing.generate_ms.toFixed(0)}ms</span>
                <span>Export: {result.timing.export_ms.toFixed(0)}ms</span>
                <span className="font-medium">Total: {result.timing.total_ms.toFixed(0)}ms</span>
              </div>

              {/* Download buttons (for single parts or backward compat) */}
              {!result.is_assembly && (
                <div className="flex items-center gap-3 pt-2">
                  {result.downloads.step && (
                    <button
                      onClick={() => handleDownload('step')}
                      disabled={downloading === 'step'}
                      className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                    >
                      {downloading === 'step' ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Download className="h-4 w-4" />
                      )}
                      Download STEP
                    </button>
                  )}
                  {result.downloads.stl && (
                    <button
                      onClick={() => handleDownload('stl')}
                      disabled={downloading === 'stl'}
                      className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50"
                    >
                      {downloading === 'stl' ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Download className="h-4 w-4" />
                      )}
                      Download STL
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default GeneratePage;
