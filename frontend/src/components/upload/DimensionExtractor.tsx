/**
 * DimensionExtractor Component
 * 
 * Extracts dimensions from PDF datasheets or images using GPT-4 Vision.
 * Displays extracted dimensions with confidence scores for review.
 */

import {
  Upload,
  FileText,
  Image as ImageIcon,
  Link2,
  Loader2,
  CheckCircle,
  AlertTriangle,
  X,
  RefreshCw,
  Ruler,
  Circle,
  Square,
  Plug,
  AlertCircle,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { useState, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { extractionApi, DimensionResponse, MountingHole, Cutout, Connector } from '@/lib/api/extraction';

// =============================================================================
// Types
// =============================================================================

interface DimensionExtractorProps {
  onExtractionComplete?: (result: DimensionResponse) => void;
  onApply?: (result: DimensionResponse) => void;
  className?: string;
  initialContext?: string;
}

// =============================================================================
// Confidence Badge Component
// =============================================================================

interface ConfidenceBadgeProps {
  confidence: number;
}

function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  const percent = Math.round(confidence * 100);
  
  let color = 'bg-red-100 text-red-700';
  let label = 'Low';
  
  if (percent >= 80) {
    color = 'bg-green-100 text-green-700';
    label = 'High';
  } else if (percent >= 50) {
    color = 'bg-yellow-100 text-yellow-700';
    label = 'Medium';
  }
  
  return (
    <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium', color)}>
      {label} ({percent}%)
    </span>
  );
}

// =============================================================================
// Editable Dimension Component
// =============================================================================

interface EditableDimensionProps {
  label: string;
  value: number | string | undefined;
  unit?: string;
  onEdit?: (value: string) => void;
}

function EditableDimension({ label, value, unit = 'mm', onEdit }: EditableDimensionProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(String(value ?? ''));
  
  const handleSave = () => {
    onEdit?.(editValue);
    setIsEditing(false);
  };
  
  return (
    <div className="flex items-center justify-between py-2 border-b dark:border-gray-700 last:border-b-0">
      <span className="text-sm text-gray-600 dark:text-gray-400">{label}</span>
      {isEditing ? (
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            className="w-20 px-2 py-1 text-sm border rounded focus:ring-2 focus:ring-primary-500"
            autoFocus
          />
          <span className="text-xs text-gray-500">{unit}</span>
          <button
            onClick={handleSave}
            className="p-1 text-green-600 hover:bg-green-50 rounded"
          >
            <CheckCircle className="h-4 w-4" />
          </button>
          <button
            onClick={() => setIsEditing(false)}
            className="p-1 text-gray-400 hover:bg-gray-50 rounded"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <span className="font-medium text-gray-900 dark:text-gray-100">
            {value !== undefined && value !== null ? `${value} ${unit}` : '—'}
          </span>
          {onEdit && (
            <button
              onClick={() => setIsEditing(true)}
              className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
              title="Edit"
            >
              <Ruler className="h-3 w-3" />
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Collapsible Section Component
// =============================================================================

interface CollapsibleSectionProps {
  title: string;
  icon: React.ReactNode;
  count: number;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

function CollapsibleSection({ title, icon, count, children, defaultOpen = true }: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  
  return (
    <div className="border dark:border-gray-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
      >
        <div className="flex items-center gap-2">
          {icon}
          <span className="font-medium text-gray-900 dark:text-gray-100">{title}</span>
          <span className="text-sm text-gray-500 dark:text-gray-400">({count})</span>
        </div>
        {isOpen ? (
          <ChevronUp className="h-4 w-4 text-gray-500" />
        ) : (
          <ChevronDown className="h-4 w-4 text-gray-500" />
        )}
      </button>
      {isOpen && (
        <div className="p-4">
          {children}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function DimensionExtractor({
  onExtractionComplete,
  onApply,
  className,
  initialContext = '',
}: DimensionExtractorProps) {
  // State
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState('');
  const [context, setContext] = useState(initialContext);
  const [mode, setMode] = useState<'file' | 'url'>('file');
  const [isExtracting, setIsExtracting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DimensionResponse | null>(null);
  const [editedResult, setEditedResult] = useState<DimensionResponse | null>(null);
  
  // Handle file drop
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && isValidFile(droppedFile)) {
      setFile(droppedFile);
      setError(null);
    } else {
      setError('Invalid file type. Please upload a PDF, PNG, JPEG, or WebP file.');
    }
  }, []);
  
  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && isValidFile(selectedFile)) {
      setFile(selectedFile);
      setError(null);
    } else if (selectedFile) {
      setError('Invalid file type. Please upload a PDF, PNG, JPEG, or WebP file.');
    }
  }, []);
  
  const isValidFile = (f: File) => {
    const validTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/webp'];
    return validTypes.includes(f.type);
  };
  
  // Extract dimensions
  const handleExtract = async () => {
    setIsExtracting(true);
    setError(null);
    
    try {
      let extractionResult: DimensionResponse;
      
      if (mode === 'file' && file) {
        extractionResult = await extractionApi.extractFromFile(file, {
          context,
          analyzeAllPages: true,
        });
      } else if (mode === 'url' && url) {
        extractionResult = await extractionApi.extractFromUrl(url, context);
      } else {
        throw new Error('Please provide a file or URL');
      }
      
      setResult(extractionResult);
      setEditedResult(extractionResult);
      onExtractionComplete?.(extractionResult);
      
    } catch (err) {
      console.error('Extraction failed:', err);
      setError(err instanceof Error ? err.message : 'Extraction failed');
    } finally {
      setIsExtracting(false);
    }
  };
  
  // Reset
  const handleReset = () => {
    setFile(null);
    setUrl('');
    setResult(null);
    setEditedResult(null);
    setError(null);
  };
  
  // Apply edits
  const handleApply = () => {
    if (editedResult) {
      onApply?.(editedResult);
    }
  };
  
  // Update overall dimensions
  const updateDimension = (key: 'length' | 'width' | 'height', value: string) => {
    if (!editedResult) return;
    
    const numValue = parseFloat(value);
    if (isNaN(numValue)) return;
    
    setEditedResult({
      ...editedResult,
      overall_dimensions: {
        ...editedResult.overall_dimensions!,
        [key]: numValue,
      },
    });
  };

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Dimension Extraction</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Upload a datasheet or image to automatically extract dimensions using AI.
        </p>
      </div>
      
      {/* Input Mode Toggle */}
      <div className="flex border rounded-lg overflow-hidden w-fit">
        <button
          onClick={() => setMode('file')}
          className={cn(
            'flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors',
            mode === 'file'
              ? 'bg-primary-600 text-white'
              : 'bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600'
          )}
        >
          <FileText className="h-4 w-4" />
          Upload File
        </button>
        <button
          onClick={() => setMode('url')}
          className={cn(
            'flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors',
            mode === 'url'
              ? 'bg-primary-600 text-white'
              : 'bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600'
          )}
        >
          <Link2 className="h-4 w-4" />
          From URL
        </button>
      </div>
      
      {/* File Upload Zone */}
      {mode === 'file' && !result && (
        <div
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          className={cn(
            'border-2 border-dashed rounded-lg p-8 text-center transition-colors',
            file ? 'border-green-300 bg-green-50' : 'border-gray-300 hover:border-gray-400'
          )}
        >
          {file ? (
            <div className="flex items-center justify-center gap-3">
              {file.type === 'application/pdf' ? (
                <FileText className="h-8 w-8 text-red-500" />
              ) : (
                <ImageIcon className="h-8 w-8 text-blue-500" />
              )}
              <div className="text-left">
                <p className="font-medium text-gray-900 dark:text-gray-100">{file.name}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
              <button
                onClick={() => setFile(null)}
                className="p-1 text-gray-400 hover:text-gray-600"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
          ) : (
            <>
              <Upload className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600 dark:text-gray-300 mb-2">
                Drag and drop a file, or{' '}
                <label className="text-primary-600 hover:text-primary-700 cursor-pointer font-medium">
                  browse
                  <input
                    type="file"
                    accept=".pdf,.png,.jpg,.jpeg,.webp"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                </label>
              </p>
              <p className="text-sm text-gray-400 dark:text-gray-500">
                PDF, PNG, JPEG, or WebP up to 10MB
              </p>
            </>
          )}
        </div>
      )}
      
      {/* URL Input */}
      {mode === 'url' && !result && (
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Datasheet URL
          </label>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com/datasheet.pdf"
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Direct link to a PDF or image file
          </p>
        </div>
      )}
      
      {/* Context Input */}
      {!result && (
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Context (Optional)
          </label>
          <textarea
            value={context}
            onChange={(e) => setContext(e.target.value)}
            placeholder="e.g., Raspberry Pi 4 Model B"
            rows={2}
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
          />
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Provide context about the component to improve extraction accuracy
          </p>
        </div>
      )}
      
      {/* Error Display */}
      {error && (
        <div className="flex items-center gap-2 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          <p className="text-sm">{error}</p>
        </div>
      )}
      
      {/* Extract Button */}
      {!result && (
        <button
          onClick={handleExtract}
          disabled={isExtracting || (mode === 'file' && !file) || (mode === 'url' && !url)}
          className={cn(
            'w-full flex items-center justify-center gap-2 py-3 rounded-lg font-medium transition-colors',
            isExtracting || (mode === 'file' && !file) || (mode === 'url' && !url)
              ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
              : 'bg-primary-600 text-white hover:bg-primary-700'
          )}
        >
          {isExtracting ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Ruler className="h-5 w-5" />
              Extract Dimensions
            </>
          )}
        </button>
      )}
      
      {/* Results */}
      {result && editedResult && (
        <div className="space-y-4">
          {/* Result Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <CheckCircle className="h-5 w-5 text-green-500" />
              <span className="font-medium text-gray-900 dark:text-gray-100">Extraction Complete</span>
              <ConfidenceBadge confidence={result.confidence} />
            </div>
            <button
              onClick={handleReset}
              className="flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
            >
              <RefreshCw className="h-4 w-4" />
              Start Over
            </button>
          </div>
          
          {/* Pages Analyzed */}
          {result.pages_analyzed > 1 && (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Analyzed {result.pages_analyzed} pages
            </p>
          )}
          
          {/* Overall Dimensions */}
          {editedResult.overall_dimensions && (
            <div className="bg-white dark:bg-gray-800 border dark:border-gray-700 rounded-lg p-4">
              <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
                <Ruler className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                Overall Dimensions
              </h3>
              <div className="divide-y">
                <EditableDimension
                  label="Length"
                  value={editedResult.overall_dimensions.length}
                  unit={editedResult.overall_dimensions.unit || 'mm'}
                  onEdit={(v) => updateDimension('length', v)}
                />
                <EditableDimension
                  label="Width"
                  value={editedResult.overall_dimensions.width}
                  unit={editedResult.overall_dimensions.unit || 'mm'}
                  onEdit={(v) => updateDimension('width', v)}
                />
                <EditableDimension
                  label="Height"
                  value={editedResult.overall_dimensions.height}
                  unit={editedResult.overall_dimensions.unit || 'mm'}
                  onEdit={(v) => updateDimension('height', v)}
                />
              </div>
            </div>
          )}
          
          {/* Mounting Holes */}
          {editedResult.mounting_holes && editedResult.mounting_holes.length > 0 && (
            <CollapsibleSection
              title="Mounting Holes"
              icon={<Circle className="h-4 w-4 text-blue-500" />}
              count={editedResult.mounting_holes.length}
            >
              <div className="space-y-3">
                {editedResult.mounting_holes.map((hole: MountingHole, index: number) => (
                  <div key={index} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-700 rounded">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Hole {index + 1}
                    </span>
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      ⌀{hole.diameter}mm at ({hole.x}, {hole.y})
                    </div>
                  </div>
                ))}
              </div>
            </CollapsibleSection>
          )}
          
          {/* Cutouts */}
          {editedResult.cutouts && editedResult.cutouts.length > 0 && (
            <CollapsibleSection
              title="Cutouts"
              icon={<Square className="h-4 w-4 text-orange-500" />}
              count={editedResult.cutouts.length}
            >
              <div className="space-y-3">
                {editedResult.cutouts.map((cutout: Cutout, index: number) => (
                  <div key={index} className="p-2 bg-gray-50 dark:bg-gray-700 rounded">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        {cutout.type}
                      </span>
                      <div className="text-sm text-gray-600 dark:text-gray-400">
                        {cutout.width}×{cutout.height}mm at ({cutout.x}, {cutout.y})
                      </div>
                    </div>
                    {cutout.notes && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{cutout.notes}</p>
                    )}
                  </div>
                ))}
              </div>
            </CollapsibleSection>
          )}
          
          {/* Connectors */}
          {editedResult.connectors && editedResult.connectors.length > 0 && (
            <CollapsibleSection
              title="Connectors"
              icon={<Plug className="h-4 w-4 text-purple-500" />}
              count={editedResult.connectors.length}
            >
              <div className="space-y-3">
                {editedResult.connectors.map((connector: Connector, index: number) => (
                  <div key={index} className="p-2 bg-gray-50 dark:bg-gray-700 rounded">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        {connector.name}
                      </span>
                      <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded">
                        {connector.type}
                      </span>
                    </div>
                    {connector.notes && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{connector.notes}</p>
                    )}
                  </div>
                ))}
              </div>
            </CollapsibleSection>
          )}
          
          {/* Notes */}
          {editedResult.notes && editedResult.notes.length > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <h3 className="font-medium text-yellow-800 mb-2 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" />
                Notes
              </h3>
              <ul className="list-disc list-inside space-y-1">
                {editedResult.notes.map((note, index) => (
                  <li key={index} className="text-sm text-yellow-700">{note}</li>
                ))}
              </ul>
            </div>
          )}
          
          {/* Low Confidence Warning */}
          {result.confidence < 0.5 && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium text-amber-800">
                    Low confidence extraction
                  </p>
                  <p className="text-sm text-amber-700 mt-1">
                    The AI had difficulty extracting dimensions. Please review and edit
                    the values manually before applying.
                  </p>
                </div>
              </div>
            </div>
          )}
          
          {/* Action Buttons */}
          <div className="flex gap-3">
            {onApply && (
              <button
                onClick={handleApply}
                className="flex-1 flex items-center justify-center gap-2 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium"
              >
                <CheckCircle className="h-5 w-5" />
                Apply Dimensions
              </button>
            )}
            <button
              onClick={handleReset}
              className="px-4 py-3 border dark:border-gray-600 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default DimensionExtractor;
