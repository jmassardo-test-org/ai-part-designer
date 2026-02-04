/**
 * DrawingPanel - 2D Technical Drawing Generation UI
 * 
 * Interface for generating, customizing, and downloading technical drawings
 * from 3D CAD models.
 */

import {
  FileImage,
  Download,
  Trash2,
  Eye,
  Loader2,
  ChevronDown,
  ChevronRight,
  Grid3X3,
  FileText,
  Maximize2,
} from 'lucide-react';
import React, { useState } from 'react';

interface ViewConfig {
  view_type: string;
  position_x: number;
  position_y: number;
  scale: number;
  show_hidden_lines: boolean;
  show_center_lines: boolean;
  label: string | null;
}

interface TitleBlockConfig {
  company_name: string;
  project_name: string;
  drawing_title: string;
  part_number: string;
  revision: string;
  drawn_by: string;
  material: string;
  notes: string[];
}

interface DrawingConfig {
  paper_size: string;
  orientation: string;
  output_format: string;
  views: ViewConfig[];
  title_block: TitleBlockConfig;
  auto_dimensions: boolean;
  show_border: boolean;
  projection_type: string;
}

interface DrawingPanelProps {
  designId: string;
  designName: string;
  className?: string;
}

const PAPER_SIZES = [
  { id: 'A4', name: 'A4 (210×297mm)' },
  { id: 'A3', name: 'A3 (297×420mm)' },
  { id: 'A2', name: 'A2 (420×594mm)' },
  { id: 'A1', name: 'A1 (594×841mm)' },
  { id: 'A0', name: 'A0 (841×1189mm)' },
  { id: 'letter', name: 'Letter (8.5×11in)' },
  { id: 'legal', name: 'Legal (8.5×14in)' },
  { id: 'tabloid', name: 'Tabloid (11×17in)' },
];

const VIEW_TYPES = [
  { id: 'front', name: 'Front', icon: '⬜' },
  { id: 'back', name: 'Back', icon: '⬜' },
  { id: 'left', name: 'Left', icon: '⬜' },
  { id: 'right', name: 'Right', icon: '⬜' },
  { id: 'top', name: 'Top', icon: '⬜' },
  { id: 'bottom', name: 'Bottom', icon: '⬜' },
  { id: 'isometric', name: 'Isometric', icon: '🔷' },
  { id: 'section', name: 'Section', icon: '✂️' },
  { id: 'detail', name: 'Detail', icon: '🔍' },
];

const OUTPUT_FORMATS = [
  { id: 'svg', name: 'SVG', description: 'Vector - web viewing' },
  { id: 'pdf', name: 'PDF', description: 'Document - printing' },
  { id: 'dxf', name: 'DXF', description: 'CAD exchange format' },
  { id: 'png', name: 'PNG', description: 'Raster image' },
];

const DEFAULT_CONFIG: DrawingConfig = {
  paper_size: 'A4',
  orientation: 'landscape',
  output_format: 'svg',
  views: [
    { view_type: 'front', position_x: 0.3, position_y: 0.5, scale: 1.0, show_hidden_lines: false, show_center_lines: true, label: null },
    { view_type: 'top', position_x: 0.3, position_y: 0.8, scale: 1.0, show_hidden_lines: false, show_center_lines: true, label: null },
    { view_type: 'right', position_x: 0.6, position_y: 0.5, scale: 1.0, show_hidden_lines: false, show_center_lines: true, label: null },
  ],
  title_block: {
    company_name: '',
    project_name: '',
    drawing_title: '',
    part_number: '',
    revision: 'A',
    drawn_by: '',
    material: '',
    notes: [],
  },
  auto_dimensions: true,
  show_border: true,
  projection_type: 'third_angle',
};

export function DrawingPanel({
  designId,
  designName,
  className = '',
}: DrawingPanelProps) {
  const [config, setConfig] = useState<DrawingConfig>({
    ...DEFAULT_CONFIG,
    title_block: {
      ...DEFAULT_CONFIG.title_block,
      drawing_title: designName,
    },
  });
  const [isGenerating, setIsGenerating] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedSection, setExpandedSection] = useState<string | null>('views');

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  const updateConfig = (updates: Partial<DrawingConfig>) => {
    setConfig(prev => ({ ...prev, ...updates }));
  };

  const updateTitleBlock = (updates: Partial<TitleBlockConfig>) => {
    setConfig(prev => ({
      ...prev,
      title_block: { ...prev.title_block, ...updates },
    }));
  };

  const addView = (viewType: string) => {
    const newView: ViewConfig = {
      view_type: viewType,
      position_x: 0.5,
      position_y: 0.5,
      scale: 1.0,
      show_hidden_lines: false,
      show_center_lines: true,
      label: null,
    };
    updateConfig({ views: [...config.views, newView] });
  };

  const removeView = (index: number) => {
    updateConfig({ views: config.views.filter((_, i) => i !== index) });
  };

  const updateView = (index: number, updates: Partial<ViewConfig>) => {
    const newViews = [...config.views];
    newViews[index] = { ...newViews[index], ...updates };
    updateConfig({ views: newViews });
  };

  const generatePreview = async () => {
    setIsGenerating(true);
    setError(null);
    
    try {
      // First get a preview of what will be generated
      const response = await fetch(`/api/v1/designs/${designId}/drawings/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(config),
      });
      
      if (!response.ok) {
        throw new Error('Failed to generate preview');
      }
      
      // Now generate the actual SVG for preview
      const svgConfig = { ...config, output_format: 'svg' };
      const svgResponse = await fetch(`/api/v1/designs/${designId}/drawings/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(svgConfig),
      });
      
      if (!svgResponse.ok) {
        throw new Error('Failed to generate drawing');
      }
      
      const svgText = await svgResponse.text();
      const blob = new Blob([svgText], { type: 'image/svg+xml' });
      const url = URL.createObjectURL(blob);
      setPreview(url);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Generation failed');
    } finally {
      setIsGenerating(false);
    }
  };

  const downloadDrawing = async () => {
    setIsGenerating(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/v1/designs/${designId}/drawings/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(config),
      });
      
      if (!response.ok) {
        throw new Error('Failed to generate drawing');
      }
      
      // Get the filename from content-disposition or use default
      const disposition = response.headers.get('content-disposition');
      const filenameMatch = disposition?.match(/filename="(.+)"/);
      const filename = filenameMatch?.[1] || `${designName}_drawing.${config.output_format}`;
      
      // Download the file
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Download failed');
    } finally {
      setIsGenerating(false);
    }
  };

  const SectionHeader = ({
    title,
    icon: Icon,
    section,
  }: {
    title: string;
    icon: React.ElementType;
    section: string;
  }) => (
    <button
      onClick={() => toggleSection(section)}
      className="flex items-center justify-between w-full px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-700"
    >
      <div className="flex items-center gap-2">
        <Icon className="w-4 h-4 text-gray-500" />
        <span className="font-medium">{title}</span>
      </div>
      {expandedSection === section ? (
        <ChevronDown className="w-4 h-4 text-gray-400" />
      ) : (
        <ChevronRight className="w-4 h-4 text-gray-400" />
      )}
    </button>
  );

  return (
    <div className={`flex flex-col h-full bg-white dark:bg-gray-800 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b dark:border-gray-700">
        <div className="flex items-center gap-2">
          <FileImage className="w-5 h-5 text-blue-600" />
          <span className="font-medium">2D Drawing</span>
        </div>
      </div>

      {/* Configuration panels */}
      <div className="flex-1 overflow-y-auto">
        {/* Paper Settings */}
        <div className="border-b dark:border-gray-700">
          <SectionHeader title="Paper Settings" icon={Grid3X3} section="paper" />
          {expandedSection === 'paper' && (
            <div className="px-4 pb-4 space-y-3">
              <div>
                <label className="text-xs text-gray-500 block mb-1">Paper Size</label>
                <select
                  value={config.paper_size}
                  onChange={(e) => updateConfig({ paper_size: e.target.value })}
                  className="w-full px-3 py-2 text-sm border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                >
                  {PAPER_SIZES.map((size) => (
                    <option key={size.id} value={size.id}>
                      {size.name}
                    </option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="text-xs text-gray-500 block mb-1">Orientation</label>
                <div className="flex gap-2">
                  {['landscape', 'portrait'].map((o) => (
                    <button
                      key={o}
                      onClick={() => updateConfig({ orientation: o })}
                      className={`flex-1 px-3 py-2 text-sm rounded-lg border transition-colors ${
                        config.orientation === o
                          ? 'bg-blue-600 text-white border-blue-600'
                          : 'border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
                      }`}
                    >
                      {o.charAt(0).toUpperCase() + o.slice(1)}
                    </button>
                  ))}
                </div>
              </div>
              
              <div>
                <label className="text-xs text-gray-500 block mb-1">Projection</label>
                <div className="flex gap-2">
                  {[
                    { id: 'third_angle', name: '3rd Angle (US)' },
                    { id: 'first_angle', name: '1st Angle (ISO)' },
                  ].map((p) => (
                    <button
                      key={p.id}
                      onClick={() => updateConfig({ projection_type: p.id })}
                      className={`flex-1 px-3 py-2 text-xs rounded-lg border transition-colors ${
                        config.projection_type === p.id
                          ? 'bg-blue-600 text-white border-blue-600'
                          : 'border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
                      }`}
                    >
                      {p.name}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Views */}
        <div className="border-b dark:border-gray-700">
          <SectionHeader title="Views" icon={Maximize2} section="views" />
          {expandedSection === 'views' && (
            <div className="px-4 pb-4 space-y-3">
              {/* Current views */}
              {config.views.map((view, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-700 rounded-lg"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-lg">
                      {VIEW_TYPES.find((v) => v.id === view.view_type)?.icon || '⬜'}
                    </span>
                    <span className="text-sm font-medium">
                      {VIEW_TYPES.find((v) => v.id === view.view_type)?.name || view.view_type}
                    </span>
                    <span className="text-xs text-gray-500">
                      {view.scale}:1
                    </span>
                  </div>
                  
                  <div className="flex items-center gap-1">
                    <input
                      type="number"
                      value={view.scale}
                      onChange={(e) => updateView(index, { scale: parseFloat(e.target.value) || 1 })}
                      className="w-16 px-2 py-1 text-xs border rounded dark:bg-gray-600 dark:border-gray-500"
                      step={0.1}
                      min={0.1}
                      max={10}
                    />
                    <button
                      onClick={() => removeView(index)}
                      className="p-1 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
              
              {/* Add view dropdown */}
              <div className="relative">
                <select
                  onChange={(e) => {
                    if (e.target.value) {
                      addView(e.target.value);
                      e.target.value = '';
                    }
                  }}
                  className="w-full px-3 py-2 text-sm border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                  defaultValue=""
                >
                  <option value="" disabled>
                    + Add View
                  </option>
                  {VIEW_TYPES.map((view) => (
                    <option key={view.id} value={view.id}>
                      {view.icon} {view.name}
                    </option>
                  ))}
                </select>
              </div>
              
              {/* Quick options */}
              <div className="flex items-center gap-4 text-sm">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={config.auto_dimensions}
                    onChange={(e) => updateConfig({ auto_dimensions: e.target.checked })}
                    className="rounded"
                  />
                  <span>Auto dimensions</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={config.show_border}
                    onChange={(e) => updateConfig({ show_border: e.target.checked })}
                    className="rounded"
                  />
                  <span>Show border</span>
                </label>
              </div>
            </div>
          )}
        </div>

        {/* Title Block */}
        <div className="border-b dark:border-gray-700">
          <SectionHeader title="Title Block" icon={FileText} section="title" />
          {expandedSection === 'title' && (
            <div className="px-4 pb-4 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 block mb-1">Company</label>
                  <input
                    type="text"
                    value={config.title_block.company_name}
                    onChange={(e) => updateTitleBlock({ company_name: e.target.value })}
                    className="w-full px-3 py-2 text-sm border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                    placeholder="Company name"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500 block mb-1">Part Number</label>
                  <input
                    type="text"
                    value={config.title_block.part_number}
                    onChange={(e) => updateTitleBlock({ part_number: e.target.value })}
                    className="w-full px-3 py-2 text-sm border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                    placeholder="P/N"
                  />
                </div>
              </div>
              
              <div>
                <label className="text-xs text-gray-500 block mb-1">Drawing Title</label>
                <input
                  type="text"
                  value={config.title_block.drawing_title}
                  onChange={(e) => updateTitleBlock({ drawing_title: e.target.value })}
                  className="w-full px-3 py-2 text-sm border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                  placeholder="Drawing title"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 block mb-1">Revision</label>
                  <input
                    type="text"
                    value={config.title_block.revision}
                    onChange={(e) => updateTitleBlock({ revision: e.target.value })}
                    className="w-full px-3 py-2 text-sm border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                    placeholder="A"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500 block mb-1">Material</label>
                  <input
                    type="text"
                    value={config.title_block.material}
                    onChange={(e) => updateTitleBlock({ material: e.target.value })}
                    className="w-full px-3 py-2 text-sm border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                    placeholder="ABS, Aluminum..."
                  />
                </div>
              </div>
              
              <div>
                <label className="text-xs text-gray-500 block mb-1">Drawn By</label>
                <input
                  type="text"
                  value={config.title_block.drawn_by}
                  onChange={(e) => updateTitleBlock({ drawn_by: e.target.value })}
                  className="w-full px-3 py-2 text-sm border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                  placeholder="Your name"
                />
              </div>
            </div>
          )}
        </div>

        {/* Output Format */}
        <div className="border-b dark:border-gray-700">
          <SectionHeader title="Output Format" icon={Download} section="output" />
          {expandedSection === 'output' && (
            <div className="px-4 pb-4">
              <div className="grid grid-cols-2 gap-2">
                {OUTPUT_FORMATS.map((format) => (
                  <button
                    key={format.id}
                    onClick={() => updateConfig({ output_format: format.id })}
                    className={`p-3 text-left rounded-lg border transition-colors ${
                      config.output_format === format.id
                        ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-500'
                        : 'border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
                    }`}
                  >
                    <div className="font-medium text-sm">{format.name}</div>
                    <div className="text-xs text-gray-500">{format.description}</div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Preview area */}
      {preview && (
        <div className="border-t dark:border-gray-700 p-4">
          <div className="bg-gray-100 dark:bg-gray-900 rounded-lg p-2 overflow-hidden">
            <img
              src={preview}
              alt="Drawing preview"
              className="max-w-full max-h-48 mx-auto object-contain"
            />
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="px-4 py-2 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Actions */}
      <div className="border-t dark:border-gray-700 p-4 space-y-2">
        <button
          onClick={generatePreview}
          disabled={isGenerating || config.views.length === 0}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm border border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/20 disabled:opacity-50 transition-colors"
        >
          {isGenerating ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Eye className="w-4 h-4" />
          )}
          Preview
        </button>
        
        <button
          onClick={downloadDrawing}
          disabled={isGenerating || config.views.length === 0}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {isGenerating ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Download className="w-4 h-4" />
          )}
          Download {config.output_format.toUpperCase()}
        </button>
      </div>
    </div>
  );
}

export default DrawingPanel;
