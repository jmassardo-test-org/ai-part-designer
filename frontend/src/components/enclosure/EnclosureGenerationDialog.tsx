/**
 * Enclosure Generation Dialog
 * 
 * Modal dialog for generating an enclosure from a component layout.
 */

import React, { useState } from 'react';
import type { LayoutDimensions, ComponentPlacement } from '../layout/types';
import { cn } from '@/lib/utils';

export type EnclosureStyle = 
  | 'rectangular' 
  | 'rounded' 
  | 'chamfered' 
  | 'minimal';

export type LidType = 
  | 'snap_fit' 
  | 'screw' 
  | 'slide' 
  | 'none';

export type VentilationType = 
  | 'none' 
  | 'slots' 
  | 'honeycomb' 
  | 'perforated';

export type MountingType = 
  | 'none' 
  | 'standoffs' 
  | 'pcb_rails' 
  | 'screw_bosses';

export interface EnclosureGenerationOptions {
  // Basic dimensions
  wallThickness: number;
  bottomThickness: number;
  topThickness: number;
  
  // Style
  style: EnclosureStyle;
  cornerRadius: number;
  chamferSize: number;
  
  // Lid
  lidType: LidType;
  lidClearance: number;
  screwHoleDiameter: number;
  screwHoleCount: number;
  
  // Ventilation
  ventilationType: VentilationType;
  ventilationSize: number;
  ventilationSpacing: number;
  ventilationFaces: string[];
  
  // Mounting
  mountingType: MountingType;
  standoffHeight: number;
  standoffDiameter: number;
  
  // Cutouts
  autoCutouts: boolean;
  cutoutClearance: number;
  
  // Additional features
  cableManagement: boolean;
  labelEmboss: boolean;
  labelText: string;
}

const defaultOptions: EnclosureGenerationOptions = {
  wallThickness: 2,
  bottomThickness: 2,
  topThickness: 2,
  style: 'rounded',
  cornerRadius: 3,
  chamferSize: 2,
  lidType: 'snap_fit',
  lidClearance: 0.2,
  screwHoleDiameter: 3,
  screwHoleCount: 4,
  ventilationType: 'none',
  ventilationSize: 2,
  ventilationSpacing: 3,
  ventilationFaces: [],
  mountingType: 'standoffs',
  standoffHeight: 3,
  standoffDiameter: 6,
  autoCutouts: true,
  cutoutClearance: 0.5,
  cableManagement: false,
  labelEmboss: false,
  labelText: '',
};

interface EnclosureGenerationDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onGenerate: (options: EnclosureGenerationOptions) => Promise<void>;
  dimensions: LayoutDimensions;
  placements: ComponentPlacement[];
  isGenerating?: boolean;
}

export function EnclosureGenerationDialog({
  isOpen,
  onClose,
  onGenerate,
  dimensions,
  placements,
  isGenerating = false,
}: EnclosureGenerationDialogProps) {
  const [options, setOptions] = useState<EnclosureGenerationOptions>(defaultOptions);
  const [activeTab, setActiveTab] = useState<'basic' | 'style' | 'features'>('basic');

  if (!isOpen) return null;

  const handleGenerate = async () => {
    await onGenerate(options);
  };

  // Calculate final dimensions
  const finalWidth = dimensions.width + (options.wallThickness * 2);
  const finalDepth = dimensions.depth + (options.wallThickness * 2);
  const finalHeight = dimensions.height + options.bottomThickness + options.topThickness;

  // Count components that need cutouts
  const cutoutCount = placements.filter(p => p.faceDirection && p.faceDirection !== 'none').length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Dialog */}
      <div className="relative w-full max-w-2xl max-h-[90vh] bg-slate-800 rounded-xl shadow-2xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
          <div>
            <h2 className="text-lg font-semibold text-white">Generate Enclosure</h2>
            <p className="text-sm text-slate-400">
              Configure and generate a custom enclosure for your layout
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-700"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-700">
          <TabButton 
            active={activeTab === 'basic'} 
            onClick={() => setActiveTab('basic')}
          >
            Basic
          </TabButton>
          <TabButton 
            active={activeTab === 'style'} 
            onClick={() => setActiveTab('style')}
          >
            Style & Lid
          </TabButton>
          <TabButton 
            active={activeTab === 'features'} 
            onClick={() => setActiveTab('features')}
          >
            Features
          </TabButton>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'basic' && (
            <BasicTab 
              options={options} 
              onChange={setOptions}
              dimensions={dimensions}
            />
          )}
          {activeTab === 'style' && (
            <StyleTab 
              options={options} 
              onChange={setOptions}
            />
          )}
          {activeTab === 'features' && (
            <FeaturesTab 
              options={options} 
              onChange={setOptions}
              placements={placements}
            />
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-700 bg-slate-800/50">
          {/* Summary */}
          <div className="text-sm text-slate-400">
            <span className="text-white font-medium">{finalWidth} × {finalDepth} × {finalHeight}</span> mm
            <span className="mx-2">•</span>
            <span>{placements.length} components</span>
            {cutoutCount > 0 && (
              <>
                <span className="mx-2">•</span>
                <span>{cutoutCount} cutouts</span>
              </>
            )}
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-slate-300 hover:text-white"
            >
              Cancel
            </button>
            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium',
                'bg-blue-600 hover:bg-blue-500 text-white',
                'disabled:opacity-50 disabled:cursor-not-allowed',
              )}
            >
              {isGenerating ? (
                <>
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  <span>Generating...</span>
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                  </svg>
                  <span>Generate Enclosure</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

interface TabButtonProps {
  children: React.ReactNode;
  active: boolean;
  onClick: () => void;
}

function TabButton({ children, active, onClick }: TabButtonProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'px-4 py-3 text-sm font-medium transition-colors',
        active
          ? 'text-blue-400 border-b-2 border-blue-400'
          : 'text-slate-400 hover:text-white',
      )}
    >
      {children}
    </button>
  );
}

// Tab Components

interface TabProps {
  options: EnclosureGenerationOptions;
  onChange: (options: EnclosureGenerationOptions) => void;
}

function BasicTab({ options, onChange, dimensions }: TabProps & { dimensions: LayoutDimensions }) {
  return (
    <div className="space-y-6">
      {/* Wall Thickness */}
      <div>
        <h3 className="text-sm font-medium text-white mb-3">Wall Thickness</h3>
        <div className="grid grid-cols-3 gap-4">
          <NumberInput
            label="Walls"
            value={options.wallThickness}
            onChange={(v) => onChange({ ...options, wallThickness: v })}
            unit="mm"
            min={1}
            max={10}
            step={0.5}
          />
          <NumberInput
            label="Bottom"
            value={options.bottomThickness}
            onChange={(v) => onChange({ ...options, bottomThickness: v })}
            unit="mm"
            min={1}
            max={10}
            step={0.5}
          />
          <NumberInput
            label="Top"
            value={options.topThickness}
            onChange={(v) => onChange({ ...options, topThickness: v })}
            unit="mm"
            min={1}
            max={10}
            step={0.5}
          />
        </div>
      </div>

      {/* Internal Dimensions (read-only) */}
      <div>
        <h3 className="text-sm font-medium text-white mb-3">Internal Dimensions (from layout)</h3>
        <div className="grid grid-cols-3 gap-4">
          <div className="p-3 bg-slate-700/50 rounded-lg">
            <div className="text-xs text-slate-400">Width</div>
            <div className="text-lg font-medium text-white">{dimensions.width} mm</div>
          </div>
          <div className="p-3 bg-slate-700/50 rounded-lg">
            <div className="text-xs text-slate-400">Depth</div>
            <div className="text-lg font-medium text-white">{dimensions.depth} mm</div>
          </div>
          <div className="p-3 bg-slate-700/50 rounded-lg">
            <div className="text-xs text-slate-400">Height</div>
            <div className="text-lg font-medium text-white">{dimensions.height} mm</div>
          </div>
        </div>
      </div>

      {/* Mounting */}
      <div>
        <h3 className="text-sm font-medium text-white mb-3">Component Mounting</h3>
        <div className="grid grid-cols-2 gap-3">
          {[
            { value: 'none', label: 'None', desc: 'Components rest on bottom' },
            { value: 'standoffs', label: 'Standoffs', desc: 'Raised mounting posts' },
            { value: 'pcb_rails', label: 'PCB Rails', desc: 'Slide-in guides' },
            { value: 'screw_bosses', label: 'Screw Bosses', desc: 'Threaded mounting points' },
          ].map((option) => (
            <button
              key={option.value}
              onClick={() => onChange({ ...options, mountingType: option.value as MountingType })}
              className={cn(
                'p-3 rounded-lg border text-left transition-colors',
                options.mountingType === option.value
                  ? 'border-blue-500 bg-blue-500/10'
                  : 'border-slate-600 hover:border-slate-500',
              )}
            >
              <div className="text-sm font-medium text-white">{option.label}</div>
              <div className="text-xs text-slate-400">{option.desc}</div>
            </button>
          ))}
        </div>

        {options.mountingType === 'standoffs' && (
          <div className="grid grid-cols-2 gap-4 mt-4">
            <NumberInput
              label="Standoff Height"
              value={options.standoffHeight}
              onChange={(v) => onChange({ ...options, standoffHeight: v })}
              unit="mm"
              min={1}
              max={20}
            />
            <NumberInput
              label="Standoff Diameter"
              value={options.standoffDiameter}
              onChange={(v) => onChange({ ...options, standoffDiameter: v })}
              unit="mm"
              min={3}
              max={15}
            />
          </div>
        )}
      </div>
    </div>
  );
}

function StyleTab({ options, onChange }: TabProps) {
  return (
    <div className="space-y-6">
      {/* Style */}
      <div>
        <h3 className="text-sm font-medium text-white mb-3">Enclosure Style</h3>
        <div className="grid grid-cols-4 gap-3">
          {[
            { value: 'rectangular', label: 'Rectangular', icon: '▢' },
            { value: 'rounded', label: 'Rounded', icon: '⬭' },
            { value: 'chamfered', label: 'Chamfered', icon: '⬡' },
            { value: 'minimal', label: 'Minimal', icon: '◇' },
          ].map((style) => (
            <button
              key={style.value}
              onClick={() => onChange({ ...options, style: style.value as EnclosureStyle })}
              className={cn(
                'p-4 rounded-lg border flex flex-col items-center gap-2 transition-colors',
                options.style === style.value
                  ? 'border-blue-500 bg-blue-500/10'
                  : 'border-slate-600 hover:border-slate-500',
              )}
            >
              <span className="text-2xl">{style.icon}</span>
              <span className="text-xs text-slate-300">{style.label}</span>
            </button>
          ))}
        </div>

        {options.style === 'rounded' && (
          <div className="mt-4">
            <NumberInput
              label="Corner Radius"
              value={options.cornerRadius}
              onChange={(v) => onChange({ ...options, cornerRadius: v })}
              unit="mm"
              min={1}
              max={20}
            />
          </div>
        )}

        {options.style === 'chamfered' && (
          <div className="mt-4">
            <NumberInput
              label="Chamfer Size"
              value={options.chamferSize}
              onChange={(v) => onChange({ ...options, chamferSize: v })}
              unit="mm"
              min={1}
              max={10}
            />
          </div>
        )}
      </div>

      {/* Lid Type */}
      <div>
        <h3 className="text-sm font-medium text-white mb-3">Lid Type</h3>
        <div className="grid grid-cols-2 gap-3">
          {[
            { value: 'snap_fit', label: 'Snap Fit', desc: 'Click-lock closure' },
            { value: 'screw', label: 'Screw Mount', desc: 'Secure with screws' },
            { value: 'slide', label: 'Slide On', desc: 'Sliding lid' },
            { value: 'none', label: 'No Lid', desc: 'Open top' },
          ].map((lid) => (
            <button
              key={lid.value}
              onClick={() => onChange({ ...options, lidType: lid.value as LidType })}
              className={cn(
                'p-3 rounded-lg border text-left transition-colors',
                options.lidType === lid.value
                  ? 'border-blue-500 bg-blue-500/10'
                  : 'border-slate-600 hover:border-slate-500',
              )}
            >
              <div className="text-sm font-medium text-white">{lid.label}</div>
              <div className="text-xs text-slate-400">{lid.desc}</div>
            </button>
          ))}
        </div>

        {options.lidType === 'screw' && (
          <div className="grid grid-cols-2 gap-4 mt-4">
            <NumberInput
              label="Screw Hole Diameter"
              value={options.screwHoleDiameter}
              onChange={(v) => onChange({ ...options, screwHoleDiameter: v })}
              unit="mm"
              min={2}
              max={6}
              step={0.5}
            />
            <NumberInput
              label="Number of Screws"
              value={options.screwHoleCount}
              onChange={(v) => onChange({ ...options, screwHoleCount: v })}
              min={2}
              max={8}
            />
          </div>
        )}

        {options.lidType !== 'none' && (
          <div className="mt-4">
            <NumberInput
              label="Lid Clearance"
              value={options.lidClearance}
              onChange={(v) => onChange({ ...options, lidClearance: v })}
              unit="mm"
              min={0.1}
              max={1}
              step={0.05}
            />
          </div>
        )}
      </div>
    </div>
  );
}

function FeaturesTab({ 
  options, 
  onChange, 
  placements 
}: TabProps & { placements: ComponentPlacement[] }) {
  const facesWithConnectors = ['front', 'back', 'left', 'right', 'top', 'bottom'];

  return (
    <div className="space-y-6">
      {/* Cutouts */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-white">Automatic Cutouts</h3>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={options.autoCutouts}
              onChange={(e) => onChange({ ...options, autoCutouts: e.target.checked })}
              className="w-4 h-4 rounded bg-slate-700 border-slate-600 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-slate-300">Enable</span>
          </label>
        </div>
        
        {options.autoCutouts && (
          <div className="p-3 bg-slate-700/50 rounded-lg text-sm text-slate-300">
            <p className="mb-2">
              {placements.filter(p => p.faceDirection && p.faceDirection !== 'none').length} components 
              will have automatic cutouts generated based on their face direction.
            </p>
            <NumberInput
              label="Cutout Clearance"
              value={options.cutoutClearance}
              onChange={(v) => onChange({ ...options, cutoutClearance: v })}
              unit="mm"
              min={0}
              max={2}
              step={0.1}
            />
          </div>
        )}
      </div>

      {/* Ventilation */}
      <div>
        <h3 className="text-sm font-medium text-white mb-3">Ventilation</h3>
        <div className="grid grid-cols-2 gap-3">
          {[
            { value: 'none', label: 'None' },
            { value: 'slots', label: 'Slots' },
            { value: 'honeycomb', label: 'Honeycomb' },
            { value: 'perforated', label: 'Perforated' },
          ].map((vent) => (
            <button
              key={vent.value}
              onClick={() => onChange({ ...options, ventilationType: vent.value as VentilationType })}
              className={cn(
                'p-3 rounded-lg border text-center transition-colors',
                options.ventilationType === vent.value
                  ? 'border-blue-500 bg-blue-500/10'
                  : 'border-slate-600 hover:border-slate-500',
              )}
            >
              <span className="text-sm text-white">{vent.label}</span>
            </button>
          ))}
        </div>

        {options.ventilationType !== 'none' && (
          <>
            <div className="grid grid-cols-2 gap-4 mt-4">
              <NumberInput
                label="Hole Size"
                value={options.ventilationSize}
                onChange={(v) => onChange({ ...options, ventilationSize: v })}
                unit="mm"
                min={1}
                max={10}
              />
              <NumberInput
                label="Spacing"
                value={options.ventilationSpacing}
                onChange={(v) => onChange({ ...options, ventilationSpacing: v })}
                unit="mm"
                min={1}
                max={20}
              />
            </div>

            <div className="mt-4">
              <label className="block text-xs text-slate-400 mb-2">Ventilation Faces</label>
              <div className="flex flex-wrap gap-2">
                {facesWithConnectors.map((face) => (
                  <button
                    key={face}
                    onClick={() => {
                      const faces = options.ventilationFaces.includes(face)
                        ? options.ventilationFaces.filter(f => f !== face)
                        : [...options.ventilationFaces, face];
                      onChange({ ...options, ventilationFaces: faces });
                    }}
                    className={cn(
                      'px-3 py-1 rounded-full text-xs transition-colors',
                      options.ventilationFaces.includes(face)
                        ? 'bg-blue-600 text-white'
                        : 'bg-slate-700 text-slate-300 hover:bg-slate-600',
                    )}
                  >
                    {face}
                  </button>
                ))}
              </div>
            </div>
          </>
        )}
      </div>

      {/* Additional Features */}
      <div>
        <h3 className="text-sm font-medium text-white mb-3">Additional Features</h3>
        <div className="space-y-3">
          <label className="flex items-center gap-3 p-3 bg-slate-700/50 rounded-lg cursor-pointer hover:bg-slate-700">
            <input
              type="checkbox"
              checked={options.cableManagement}
              onChange={(e) => onChange({ ...options, cableManagement: e.target.checked })}
              className="w-4 h-4 rounded bg-slate-700 border-slate-600 text-blue-600 focus:ring-blue-500"
            />
            <div>
              <div className="text-sm font-medium text-white">Cable Management</div>
              <div className="text-xs text-slate-400">Add cable routing channels and clips</div>
            </div>
          </label>

          <div className="p-3 bg-slate-700/50 rounded-lg">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={options.labelEmboss}
                onChange={(e) => onChange({ ...options, labelEmboss: e.target.checked })}
                className="w-4 h-4 rounded bg-slate-700 border-slate-600 text-blue-600 focus:ring-blue-500"
              />
              <div>
                <div className="text-sm font-medium text-white">Label Emboss</div>
                <div className="text-xs text-slate-400">Emboss text on enclosure surface</div>
              </div>
            </label>
            
            {options.labelEmboss && (
              <input
                type="text"
                value={options.labelText}
                onChange={(e) => onChange({ ...options, labelText: e.target.value })}
                placeholder="Enter label text..."
                className="mt-3 w-full px-3 py-2 text-sm bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Utility Components

interface NumberInputProps {
  label: string;
  value: number;
  onChange: (value: number) => void;
  unit?: string;
  min?: number;
  max?: number;
  step?: number;
}

function NumberInput({ 
  label, 
  value, 
  onChange, 
  unit, 
  min = 0, 
  max = 100,
  step = 1,
}: NumberInputProps) {
  return (
    <div>
      <label className="block text-xs text-slate-400 mb-1">{label}</label>
      <div className="relative">
        <input
          type="number"
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
          min={min}
          max={max}
          step={step}
          className={cn(
            'w-full px-3 py-2 text-sm bg-slate-700 border border-slate-600 rounded-lg text-white text-right focus:outline-none focus:border-blue-500',
            unit && 'pr-10',
          )}
        />
        {unit && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400">
            {unit}
          </span>
        )}
      </div>
    </div>
  );
}
