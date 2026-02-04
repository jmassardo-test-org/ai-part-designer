/**
 * Template detail and customization page.
 * Allows users to customize template parameters and preview/generate parts.
 */

import { 
  ArrowLeft, 
  Download, 
  Eye,
  Loader2,
  AlertCircle,
  RefreshCw,
  Info,
  ChevronDown,
  ChevronUp,
  Sparkles
} from 'lucide-react';
import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ModelViewer } from '@/components/viewer';
import { useAuth } from '@/contexts/AuthContext';

// Types
interface TemplateParameter {
  name: string;
  type: 'float' | 'int' | 'number' | 'bool' | 'boolean' | 'string' | 'choice' | 'select';
  label: string;
  description?: string;
  default: number | string | boolean;
  min?: number;
  max?: number;
  step?: number;
  choices?: string[];
  options?: string[];
  unit?: string;
}

interface Template {
  id: string;
  slug: string;
  name: string;
  description: string;
  category: string;
  tags: string[];
  thumbnail_url?: string;
  tier_required: 'free' | 'basic' | 'pro' | 'enterprise';
  parameters: TemplateParameter[];
  is_featured: boolean;
  usage_count: number;
}

// API base URL
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export function TemplateDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const { token } = useAuth();
  
  // State
  const [template, setTemplate] = useState<Template | null>(null);
  const [parameters, setParameters] = useState<Record<string, number | string | boolean>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewData, setPreviewData] = useState<ArrayBuffer | null>(null);
  const [generating, setGenerating] = useState(false);
  const [expandedParams, setExpandedParams] = useState(true);

  // Fetch template details
  useEffect(() => {
    const fetchTemplate = async () => {
      if (!slug) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const response = await fetch(`${API_BASE}/templates/${slug}`);
        if (!response.ok) {
          if (response.status === 404) {
            throw new Error('Template not found');
          }
          throw new Error('Failed to fetch template');
        }
        
        const data = await response.json();
        setTemplate(data);
        
        // Initialize parameters with defaults
        const defaults: Record<string, number | string | boolean> = {};
        data.parameters.forEach((param: TemplateParameter) => {
          defaults[param.name] = param.default;
        });
        setParameters(defaults);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load template');
      } finally {
        setLoading(false);
      }
    };

    fetchTemplate();
  }, [slug]);

  // Generate preview
  const handlePreview = useCallback(async () => {
    if (!template) return;
    
    setPreviewLoading(true);
    
    try {
      const response = await fetch(`${API_BASE}/templates/${template.slug}/preview`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        body: JSON.stringify({ parameters }),
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to generate preview');
      }
      
      const data = await response.arrayBuffer();
      setPreviewData(data);
    } catch (err) {
      console.error('Preview error:', err);
      setError(err instanceof Error ? err.message : 'Failed to generate preview');
    } finally {
      setPreviewLoading(false);
    }
  }, [template, parameters, token]);

  // Auto-preview on initial load and parameter changes (debounced)
  useEffect(() => {
    if (!template || loading) return;
    
    const timer = setTimeout(() => {
      handlePreview();
    }, 500);
    
    return () => clearTimeout(timer);
  }, [template, parameters, loading, handlePreview]);

  // Generate and download
  const handleGenerate = async (format: 'step' | 'stl') => {
    if (!template) return;
    
    setGenerating(true);
    
    try {
      const response = await fetch(`${API_BASE}/templates/${template.slug}/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        body: JSON.stringify({ 
          parameters,
          format 
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to generate part');
      }
      
      // Download the file
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${template.slug}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Generate error:', err);
      setError(err instanceof Error ? err.message : 'Failed to generate part');
    } finally {
      setGenerating(false);
    }
  };

  // Generate a natural language prompt from current parameters
  const generatePromptFromTemplate = useCallback((): string => {
    if (!template) return '';
    
    const paramDescriptions = template.parameters.map((param) => {
      const value = parameters[param.name];
      const unit = param.unit || '';
      
      switch (param.type) {
        case 'float':
        case 'int':
        case 'number':
          return `${param.label}: ${value}${unit}`;
        case 'bool':
        case 'boolean':
          return value ? `with ${param.label.toLowerCase()}` : `without ${param.label.toLowerCase()}`;
        default:
          return `${param.label}: ${value}`;
      }
    }).filter(Boolean);
    
    return `Create a ${template.name.toLowerCase()}: ${paramDescriptions.join(', ')}. ${template.description}`;
  }, [template, parameters]);

  // Navigate to Generate page with template context
  const handleCustomizeWithAI = () => {
    if (!template) return;
    
    navigate('/generate', {
      state: {
        templateName: template.name,
        templateSlug: template.slug,
        templateDescription: template.description,
        parameters: parameters,
        suggestedPrompt: generatePromptFromTemplate(),
      }
    });
  };

  // Update a parameter value
  const updateParameter = (name: string, value: number | string | boolean) => {
    setParameters((prev) => ({ ...prev, [name]: value }));
  };

  // Render parameter input based on type
  const renderParameterInput = (param: TemplateParameter) => {
    const value = parameters[param.name];
    
    switch (param.type) {
      case 'float':
      case 'int':
      case 'number':
        return (
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <input
                type="range"
                min={param.min ?? 0}
                max={param.max ?? 100}
                step={param.step ?? (param.type === 'int' ? 1 : 0.1)}
                value={value as number}
                onChange={(e) => updateParameter(param.name, parseFloat(e.target.value))}
                className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
              />
              <input
                type="number"
                min={param.min}
                max={param.max}
                step={param.step ?? (param.type === 'int' ? 1 : 0.1)}
                value={value as number}
                onChange={(e) => updateParameter(param.name, parseFloat(e.target.value))}
                className="w-20 px-2 py-1 border border-gray-300 dark:border-gray-600 rounded text-sm text-right bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              />
              {param.unit && (
                <span className="text-sm text-gray-500 dark:text-gray-400 w-8">{param.unit}</span>
              )}
            </div>
          </div>
        );
      
      case 'bool':
      case 'boolean':
        return (
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={value as boolean}
              onChange={(e) => updateParameter(param.name, e.target.checked)}
              className="h-4 w-4 text-primary-600 border-gray-300 dark:border-gray-600 rounded focus:ring-primary-500"
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">Enabled</span>
          </label>
        );
      
      case 'choice':
      case 'select':
        return (
          <select
            value={value as string}
            onChange={(e) => updateParameter(param.name, e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
          >
            {(param.choices || param.options || []).map((choice) => (
              <option key={choice} value={choice}>
                {choice}
              </option>
            ))}
          </select>
        );
      
      case 'string':
        return (
          <input
            type="text"
            value={value as string}
            onChange={(e) => updateParameter(param.name, e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
          />
        );
      
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    );
  }

  if (error && !template) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
        <p className="text-gray-600 dark:text-gray-400 mb-4">{error}</p>
        <button
          onClick={() => navigate('/templates')}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
        >
          Back to Templates
        </button>
      </div>
    );
  }

  if (!template) return null;

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate('/templates')}
          className="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 mb-4"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Templates
        </button>
        
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">{template.name}</h1>
            <p className="mt-1 text-gray-600 dark:text-gray-400">{template.description}</p>
          </div>
          
          <div className="flex items-center gap-3">
            <button
              onClick={handlePreview}
              disabled={previewLoading}
              className="flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 text-gray-700 dark:text-gray-300"
            >
              {previewLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              Refresh Preview
            </button>
            
            {/* Customize with AI button */}
            <button
              onClick={handleCustomizeWithAI}
              className="flex items-center gap-2 px-4 py-2 border border-purple-300 dark:border-purple-600 text-purple-700 dark:text-purple-300 rounded-lg hover:bg-purple-50 dark:hover:bg-purple-900/20"
            >
              <Sparkles className="h-4 w-4" />
              Customize with AI
            </button>
            
            <div className="relative group">
              <button
                onClick={() => handleGenerate('step')}
                disabled={generating}
                className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
              >
                {generating ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Download className="h-4 w-4" />
                )}
                Download
              </button>
              
              {/* Download dropdown */}
              <div className="absolute right-0 top-full mt-1 w-40 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
                <button
                  onClick={() => handleGenerate('step')}
                  disabled={generating}
                  className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700 rounded-t-lg text-gray-700 dark:text-gray-300"
                >
                  Download STEP
                </button>
                <button
                  onClick={() => handleGenerate('stl')}
                  disabled={generating}
                  className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700 rounded-b-lg text-gray-700 dark:text-gray-300"
                >
                  Download STL
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0" />
          <p className="text-red-700">{error}</p>
          <button
            onClick={() => setError(null)}
            className="ml-auto text-red-500 hover:text-red-700"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main content */}
      <div className="grid lg:grid-cols-5 gap-6">
        {/* Parameters Panel */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
            {/* Panel header */}
            <button
              onClick={() => setExpandedParams(!expandedParams)}
              className="w-full flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              <h2 className="font-semibold text-gray-900 dark:text-gray-100">Parameters</h2>
              {expandedParams ? (
                <ChevronUp className="h-5 w-5 text-gray-400" />
              ) : (
                <ChevronDown className="h-5 w-5 text-gray-400" />
              )}
            </button>
            
            {/* Parameters list */}
            {expandedParams && (
              <div className="border-t border-gray-200 dark:border-gray-700 divide-y divide-gray-100 dark:divide-gray-700">
                {(template.parameters || []).map((param) => (
                  <div key={param.name} className="p-4">
                    <div className="flex items-start justify-between mb-2">
                      <label className="font-medium text-gray-900 dark:text-gray-100 text-sm">
                        {param.label}
                      </label>
                      {param.description && (
                        <div className="group relative">
                          <Info className="h-4 w-4 text-gray-400 cursor-help" />
                          <div className="absolute right-0 top-full mt-1 w-48 p-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
                            {param.description}
                          </div>
                        </div>
                      )}
                    </div>
                    {renderParameterInput(param)}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Reset button */}
          <button
            onClick={() => {
              const defaults: Record<string, number | string | boolean> = {};
              template.parameters.forEach((param) => {
                defaults[param.name] = param.default;
              });
              setParameters(defaults);
            }}
            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            Reset to Defaults
          </button>

          {/* Tags */}
          {(template.tags || []).length > 0 && (
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-3 text-sm">Tags</h3>
              <div className="flex flex-wrap gap-2">
                {(template.tags || []).map((tag) => (
                  <span
                    key={tag}
                    className="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 text-xs rounded"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* 3D Viewer */}
        <div className="lg:col-span-3">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="h-[500px] relative">
              {previewLoading && !previewData ? (
                <div className="absolute inset-0 flex items-center justify-center bg-gray-50 dark:bg-gray-900">
                  <div className="text-center">
                    <Loader2 className="h-8 w-8 animate-spin text-primary-600 mx-auto mb-2" />
                    <p className="text-sm text-gray-600 dark:text-gray-400">Generating preview...</p>
                  </div>
                </div>
              ) : previewData ? (
                <ModelViewer 
                  stlData={previewData}
                  showGrid={true}
                  showAxes={true}
                  backgroundColor="#f9fafb"
                />
              ) : (
                <div className="absolute inset-0 flex items-center justify-center bg-gray-50 dark:bg-gray-900">
                  <div className="text-center">
                    <Eye className="h-12 w-12 text-gray-400 mx-auto mb-2" />
                    <p className="text-gray-600 dark:text-gray-400">Preview will appear here</p>
                    <button
                      onClick={handlePreview}
                      className="mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                    >
                      Generate Preview
                    </button>
                  </div>
                </div>
              )}
              
              {/* Loading overlay */}
              {previewLoading && previewData && (
                <div className="absolute inset-0 bg-white/50 flex items-center justify-center">
                  <Loader2 className="h-6 w-6 animate-spin text-primary-600" />
                </div>
              )}
            </div>
          </div>
          
          {/* Quick info */}
          <div className="mt-4 grid grid-cols-3 gap-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-3 text-center">
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{template.parameters.length}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">Parameters</p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-3 text-center">
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 capitalize">{template.category}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">Category</p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-3 text-center">
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{template.usage_count.toLocaleString()}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">Uses</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
