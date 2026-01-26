/**
 * Enclosure Options Panel
 * 
 * Collapsible sidebar panel for real-time enclosure configuration.
 */

import React, { useState } from 'react';
import { cn } from '@/lib/utils';
import type { EnclosureGenerationOptions } from './EnclosureGenerationDialog';

interface EnclosureOptionsPanelProps {
  options: EnclosureGenerationOptions;
  onChange: (options: Partial<EnclosureGenerationOptions>) => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export function EnclosureOptionsPanel({
  options,
  onChange,
  isCollapsed = false,
  onToggleCollapse,
}: EnclosureOptionsPanelProps) {
  const [expandedSection, setExpandedSection] = useState<string | null>('dimensions');

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  if (isCollapsed) {
    return (
      <div className="w-10 bg-slate-900 border-l border-slate-700 flex flex-col items-center py-4">
        <button
          onClick={onToggleCollapse}
          className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800"
          title="Expand options panel"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
          </svg>
        </button>
      </div>
    );
  }

  return (
    <div className="w-72 bg-slate-900 border-l border-slate-700 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
        <h3 className="text-sm font-medium text-white">Enclosure Options</h3>
        {onToggleCollapse && (
          <button
            onClick={onToggleCollapse}
            className="p-1 text-slate-400 hover:text-white rounded"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
            </svg>
          </button>
        )}
      </div>

      {/* Sections */}
      <div className="flex-1 overflow-y-auto">
        {/* Dimensions Section */}
        <Section
          title="Dimensions"
          expanded={expandedSection === 'dimensions'}
          onToggle={() => toggleSection('dimensions')}
        >
          <div className="space-y-3">
            <SliderInput
              label="Wall Thickness"
              value={options.wallThickness}
              onChange={(v) => onChange({ wallThickness: v })}
              min={1}
              max={5}
              step={0.5}
              unit="mm"
            />
            <SliderInput
              label="Bottom Thickness"
              value={options.bottomThickness}
              onChange={(v) => onChange({ bottomThickness: v })}
              min={1}
              max={5}
              step={0.5}
              unit="mm"
            />
            <SliderInput
              label="Top Thickness"
              value={options.topThickness}
              onChange={(v) => onChange({ topThickness: v })}
              min={1}
              max={5}
              step={0.5}
              unit="mm"
            />
          </div>
        </Section>

        {/* Style Section */}
        <Section
          title="Style"
          expanded={expandedSection === 'style'}
          onToggle={() => toggleSection('style')}
        >
          <div className="space-y-4">
            <div>
              <label className="block text-xs text-slate-400 mb-2">Shape</label>
              <div className="grid grid-cols-2 gap-2">
                {(['rectangular', 'rounded', 'chamfered', 'minimal'] as const).map((style) => (
                  <button
                    key={style}
                    onClick={() => onChange({ style })}
                    className={cn(
                      'px-3 py-2 text-xs rounded-lg border transition-colors capitalize',
                      options.style === style
                        ? 'border-blue-500 bg-blue-500/10 text-blue-400'
                        : 'border-slate-700 text-slate-400 hover:border-slate-600',
                    )}
                  >
                    {style}
                  </button>
                ))}
              </div>
            </div>

            {options.style === 'rounded' && (
              <SliderInput
                label="Corner Radius"
                value={options.cornerRadius}
                onChange={(v) => onChange({ cornerRadius: v })}
                min={1}
                max={15}
                unit="mm"
              />
            )}

            {options.style === 'chamfered' && (
              <SliderInput
                label="Chamfer Size"
                value={options.chamferSize}
                onChange={(v) => onChange({ chamferSize: v })}
                min={1}
                max={10}
                unit="mm"
              />
            )}
          </div>
        </Section>

        {/* Lid Section */}
        <Section
          title="Lid"
          expanded={expandedSection === 'lid'}
          onToggle={() => toggleSection('lid')}
        >
          <div className="space-y-4">
            <div>
              <label className="block text-xs text-slate-400 mb-2">Type</label>
              <select
                value={options.lidType}
                onChange={(e) => onChange({ lidType: e.target.value as any })}
                className="w-full px-3 py-2 text-sm bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
              >
                <option value="snap_fit">Snap Fit</option>
                <option value="screw">Screw Mount</option>
                <option value="slide">Slide On</option>
                <option value="none">No Lid</option>
              </select>
            </div>

            {options.lidType !== 'none' && (
              <SliderInput
                label="Lid Clearance"
                value={options.lidClearance}
                onChange={(v) => onChange({ lidClearance: v })}
                min={0.1}
                max={0.5}
                step={0.05}
                unit="mm"
              />
            )}

            {options.lidType === 'screw' && (
              <>
                <SliderInput
                  label="Screw Hole ∅"
                  value={options.screwHoleDiameter}
                  onChange={(v) => onChange({ screwHoleDiameter: v })}
                  min={2}
                  max={5}
                  step={0.5}
                  unit="mm"
                />
                <SliderInput
                  label="Screw Count"
                  value={options.screwHoleCount}
                  onChange={(v) => onChange({ screwHoleCount: v })}
                  min={2}
                  max={8}
                  step={1}
                />
              </>
            )}
          </div>
        </Section>

        {/* Mounting Section */}
        <Section
          title="Mounting"
          expanded={expandedSection === 'mounting'}
          onToggle={() => toggleSection('mounting')}
        >
          <div className="space-y-4">
            <div>
              <label className="block text-xs text-slate-400 mb-2">Type</label>
              <select
                value={options.mountingType}
                onChange={(e) => onChange({ mountingType: e.target.value as any })}
                className="w-full px-3 py-2 text-sm bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
              >
                <option value="none">None</option>
                <option value="standoffs">Standoffs</option>
                <option value="pcb_rails">PCB Rails</option>
                <option value="screw_bosses">Screw Bosses</option>
              </select>
            </div>

            {options.mountingType === 'standoffs' && (
              <>
                <SliderInput
                  label="Height"
                  value={options.standoffHeight}
                  onChange={(v) => onChange({ standoffHeight: v })}
                  min={2}
                  max={15}
                  unit="mm"
                />
                <SliderInput
                  label="Diameter"
                  value={options.standoffDiameter}
                  onChange={(v) => onChange({ standoffDiameter: v })}
                  min={4}
                  max={10}
                  unit="mm"
                />
              </>
            )}
          </div>
        </Section>

        {/* Ventilation Section */}
        <Section
          title="Ventilation"
          expanded={expandedSection === 'ventilation'}
          onToggle={() => toggleSection('ventilation')}
        >
          <div className="space-y-4">
            <div>
              <label className="block text-xs text-slate-400 mb-2">Pattern</label>
              <select
                value={options.ventilationType}
                onChange={(e) => onChange({ ventilationType: e.target.value as any })}
                className="w-full px-3 py-2 text-sm bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
              >
                <option value="none">None</option>
                <option value="slots">Slots</option>
                <option value="honeycomb">Honeycomb</option>
                <option value="perforated">Perforated</option>
              </select>
            </div>

            {options.ventilationType !== 'none' && (
              <>
                <SliderInput
                  label="Hole Size"
                  value={options.ventilationSize}
                  onChange={(v) => onChange({ ventilationSize: v })}
                  min={1}
                  max={5}
                  unit="mm"
                />
                <SliderInput
                  label="Spacing"
                  value={options.ventilationSpacing}
                  onChange={(v) => onChange({ ventilationSpacing: v })}
                  min={2}
                  max={10}
                  unit="mm"
                />
              </>
            )}
          </div>
        </Section>

        {/* Features Section */}
        <Section
          title="Features"
          expanded={expandedSection === 'features'}
          onToggle={() => toggleSection('features')}
        >
          <div className="space-y-3">
            <Toggle
              label="Auto Cutouts"
              description="Generate connector cutouts"
              checked={options.autoCutouts}
              onChange={(v) => onChange({ autoCutouts: v })}
            />
            <Toggle
              label="Cable Management"
              description="Add cable routing"
              checked={options.cableManagement}
              onChange={(v) => onChange({ cableManagement: v })}
            />
            <Toggle
              label="Label Emboss"
              description="Emboss text on surface"
              checked={options.labelEmboss}
              onChange={(v) => onChange({ labelEmboss: v })}
            />
            {options.labelEmboss && (
              <input
                type="text"
                value={options.labelText}
                onChange={(e) => onChange({ labelText: e.target.value })}
                placeholder="Label text..."
                className="w-full px-3 py-2 text-sm bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
              />
            )}
          </div>
        </Section>
      </div>

      {/* Apply Button */}
      <div className="p-4 border-t border-slate-700">
        <button
          className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          Update Preview
        </button>
      </div>
    </div>
  );
}

interface SectionProps {
  title: string;
  expanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

function Section({ title, expanded, onToggle, children }: SectionProps) {
  return (
    <div className="border-b border-slate-700">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-white hover:bg-slate-800/50"
      >
        {title}
        <svg
          className={cn(
            'w-4 h-4 text-slate-400 transition-transform',
            expanded && 'rotate-180',
          )}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {expanded && (
        <div className="px-4 pb-4">
          {children}
        </div>
      )}
    </div>
  );
}

interface SliderInputProps {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  step?: number;
  unit?: string;
}

function SliderInput({ label, value, onChange, min, max, step = 1, unit }: SliderInputProps) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <label className="text-xs text-slate-400">{label}</label>
        <span className="text-xs text-white">
          {value}{unit && <span className="text-slate-400 ml-0.5">{unit}</span>}
        </span>
      </div>
      <input
        type="range"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        min={min}
        max={max}
        step={step}
        className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
      />
    </div>
  );
}

interface ToggleProps {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}

function Toggle({ label, description, checked, onChange }: ToggleProps) {
  return (
    <label className="flex items-start gap-3 cursor-pointer">
      <div className="relative mt-0.5">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="sr-only"
        />
        <div className={cn(
          'w-8 h-4 rounded-full transition-colors',
          checked ? 'bg-blue-600' : 'bg-slate-700',
        )}>
          <div className={cn(
            'w-3 h-3 bg-white rounded-full absolute top-0.5 transition-transform',
            checked ? 'translate-x-4' : 'translate-x-0.5',
          )} />
        </div>
      </div>
      <div>
        <div className="text-sm text-white">{label}</div>
        {description && (
          <div className="text-xs text-slate-400">{description}</div>
        )}
      </div>
    </label>
  );
}
