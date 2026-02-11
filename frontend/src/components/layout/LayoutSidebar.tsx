/**
 * Layout Sidebar
 * 
 * Component list, properties panel, and layout settings.
 */

import React from 'react';
import { ComponentItem } from './ComponentItem';
import type { ComponentData, ComponentPlacement, LayoutDimensions } from './types';
import { cn } from '@/lib/utils';

interface LayoutSidebarProps {
  availableComponents: ComponentData[];
  placements: ComponentPlacement[];
  selectedId: string | null;
  dimensions: LayoutDimensions;
  onComponentDragStart: (component: ComponentData) => void;
  onSelectPlacement: (id: string | null) => void;
  onUpdatePlacement: (id: string, updates: Partial<ComponentPlacement>) => void;
  onDimensionsChange: (dimensions: Partial<LayoutDimensions>) => void;
}

type TabId = 'components' | 'layout' | 'properties';

export function LayoutSidebar({
  availableComponents,
  placements,
  selectedId,
  dimensions,
  onComponentDragStart,
  onSelectPlacement,
  onUpdatePlacement,
  onDimensionsChange,
}: LayoutSidebarProps) {
  const [activeTab, setActiveTab] = React.useState<TabId>('components');
  const selectedPlacement = placements.find(p => p.id === selectedId);

  // Switch to properties tab when something is selected
  React.useEffect(() => {
    if (selectedId && activeTab === 'components') {
      setActiveTab('properties');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  return (
    <div className="w-72 bg-slate-900 border-l border-slate-700 flex flex-col">
      {/* Tabs */}
      <div className="flex border-b border-slate-700">
        <TabButton 
          active={activeTab === 'components'} 
          onClick={() => setActiveTab('components')}
        >
          Components
        </TabButton>
        <TabButton 
          active={activeTab === 'layout'} 
          onClick={() => setActiveTab('layout')}
        >
          Layout
        </TabButton>
        <TabButton 
          active={activeTab === 'properties'} 
          onClick={() => setActiveTab('properties')}
          disabled={!selectedPlacement}
        >
          Properties
        </TabButton>
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'components' && (
          <ComponentsTab
            components={availableComponents}
            placedIds={placements.map(p => p.componentId)}
            onDragStart={onComponentDragStart}
          />
        )}
        {activeTab === 'layout' && (
          <LayoutSettingsTab
            dimensions={dimensions}
            onChange={onDimensionsChange}
          />
        )}
        {activeTab === 'properties' && selectedPlacement && (
          <PropertiesTab
            placement={selectedPlacement}
            onUpdate={(updates) => onUpdatePlacement(selectedPlacement.id, updates)}
          />
        )}
        {activeTab === 'properties' && !selectedPlacement && (
          <div className="p-4 text-center text-slate-500 text-sm">
            Select a component to view properties
          </div>
        )}
      </div>

      {/* Placed components list */}
      <div className="border-t border-slate-700">
        <div className="px-3 py-2 text-xs font-medium text-slate-400 uppercase tracking-wider">
          Placed ({placements.length})
        </div>
        <div className="max-h-48 overflow-y-auto p-2 space-y-1">
          {placements.length === 0 ? (
            <div className="text-center text-slate-500 text-xs py-2">
              Drag components to place
            </div>
          ) : (
            placements.map(placement => (
              <button
                key={placement.id}
                onClick={() => onSelectPlacement(placement.id)}
                className={cn(
                  'w-full flex items-center gap-2 px-2 py-1.5 rounded text-sm text-left transition-colors',
                  selectedId === placement.id
                    ? 'bg-blue-600/20 text-blue-400 border border-blue-500/50'
                    : 'hover:bg-slate-800 text-slate-300',
                )}
              >
                <span className="flex-1 truncate">{placement.name}</span>
                {placement.locked && (
                  <svg className="w-3 h-3 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                )}
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

interface TabButtonProps {
  children: React.ReactNode;
  active: boolean;
  onClick: () => void;
  disabled?: boolean;
}

function TabButton({ children, active, onClick, disabled }: TabButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'flex-1 px-3 py-2 text-xs font-medium transition-colors',
        active
          ? 'text-blue-400 border-b-2 border-blue-400'
          : 'text-slate-400 hover:text-white',
        disabled && 'opacity-50 cursor-not-allowed',
      )}
    >
      {children}
    </button>
  );
}

interface ComponentsTabProps {
  components: ComponentData[];
  placedIds: string[];
  onDragStart: (component: ComponentData) => void;
}

function ComponentsTab({ components, placedIds, onDragStart }: ComponentsTabProps) {
  const [search, setSearch] = React.useState('');

  const filtered = components.filter(c => 
    c.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex flex-col h-full">
      {/* Search */}
      <div className="p-2">
        <div className="relative">
          <svg className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search components..."
            className="w-full pl-9 pr-3 py-1.5 text-sm bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
        </div>
      </div>

      {/* Component list */}
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {filtered.length === 0 ? (
          <div className="text-center text-slate-500 text-sm py-4">
            No components found
          </div>
        ) : (
          filtered.map(component => (
            <ComponentItem
              key={component.id}
              component={component}
              onDragStart={onDragStart}
              disabled={placedIds.includes(component.id)}
            />
          ))
        )}
      </div>
    </div>
  );
}

interface LayoutSettingsTabProps {
  dimensions: LayoutDimensions;
  onChange: (updates: Partial<LayoutDimensions>) => void;
}

function LayoutSettingsTab({ dimensions, onChange }: LayoutSettingsTabProps) {
  return (
    <div className="p-4 space-y-4">
      <div>
        <h3 className="text-sm font-medium text-white mb-3">Enclosure Dimensions</h3>
        <div className="grid grid-cols-3 gap-2">
          <NumberInput
            label="Width"
            value={dimensions.width}
            onChange={(v) => onChange({ width: v })}
            unit="mm"
          />
          <NumberInput
            label="Depth"
            value={dimensions.depth}
            onChange={(v) => onChange({ depth: v })}
            unit="mm"
          />
          <NumberInput
            label="Height"
            value={dimensions.height}
            onChange={(v) => onChange({ height: v })}
            unit="mm"
          />
        </div>
      </div>

      <div>
        <h3 className="text-sm font-medium text-white mb-3">Grid Settings</h3>
        <div className="grid grid-cols-2 gap-2">
          <NumberInput
            label="Grid Size"
            value={dimensions.gridSize}
            onChange={(v) => onChange({ gridSize: v })}
            unit="mm"
            min={1}
            max={50}
          />
          <NumberInput
            label="Clearance"
            value={dimensions.clearance}
            onChange={(v) => onChange({ clearance: v })}
            unit="mm"
            min={0}
            max={20}
          />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="autoDimensions"
          checked={dimensions.autoDimensions}
          onChange={(e) => onChange({ autoDimensions: e.target.checked })}
          className="w-4 h-4 rounded bg-slate-700 border-slate-600 text-blue-600 focus:ring-blue-500"
        />
        <label htmlFor="autoDimensions" className="text-sm text-slate-300">
          Auto-size enclosure
        </label>
      </div>
    </div>
  );
}

interface PropertiesTabProps {
  placement: ComponentPlacement;
  onUpdate: (updates: Partial<ComponentPlacement>) => void;
}

function PropertiesTab({ placement, onUpdate }: PropertiesTabProps) {
  return (
    <div className="p-4 space-y-4">
      <div>
        <h3 className="text-sm font-medium text-white mb-1">{placement.name}</h3>
        <div className="text-xs text-slate-400">
          {placement.width} × {placement.depth} × {placement.height} mm
        </div>
      </div>

      <div>
        <h4 className="text-xs font-medium text-slate-400 uppercase mb-2">Position</h4>
        <div className="grid grid-cols-3 gap-2">
          <NumberInput
            label="X"
            value={placement.x}
            onChange={(v) => onUpdate({ x: v })}
            unit="mm"
            disabled={placement.locked}
          />
          <NumberInput
            label="Y"
            value={placement.y}
            onChange={(v) => onUpdate({ y: v })}
            unit="mm"
            disabled={placement.locked}
          />
          <NumberInput
            label="Z"
            value={placement.z}
            onChange={(v) => onUpdate({ z: v })}
            unit="mm"
            disabled={placement.locked}
          />
        </div>
      </div>

      <div>
        <h4 className="text-xs font-medium text-slate-400 uppercase mb-2">Rotation</h4>
        <NumberInput
          label="Angle"
          value={placement.rotation}
          onChange={(v) => onUpdate({ rotation: v % 360 })}
          unit="°"
          step={90}
          disabled={placement.locked}
        />
      </div>

      <div>
        <h4 className="text-xs font-medium text-slate-400 uppercase mb-2">Face Direction</h4>
        <select
          value={placement.faceDirection || 'none'}
          onChange={(e) => onUpdate({ faceDirection: e.target.value as ComponentPlacement['faceDirection'] })}
          disabled={placement.locked}
          className="w-full px-3 py-1.5 text-sm bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500 disabled:opacity-50"
        >
          <option value="none">None</option>
          <option value="front">Front</option>
          <option value="back">Back</option>
          <option value="left">Left</option>
          <option value="right">Right</option>
          <option value="top">Top</option>
          <option value="bottom">Bottom</option>
        </select>
      </div>

      <div className="flex items-center gap-2 pt-2">
        <input
          type="checkbox"
          id="locked"
          checked={placement.locked}
          onChange={(e) => onUpdate({ locked: e.target.checked })}
          className="w-4 h-4 rounded bg-slate-700 border-slate-600 text-blue-600 focus:ring-blue-500"
        />
        <label htmlFor="locked" className="text-sm text-slate-300">
          Lock position
        </label>
      </div>
    </div>
  );
}

interface NumberInputProps {
  label: string;
  value: number;
  onChange: (value: number) => void;
  unit?: string;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
}

function NumberInput({ 
  label, 
  value, 
  onChange, 
  unit, 
  min = 0, 
  max = 1000,
  step = 1,
  disabled = false,
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
          disabled={disabled}
          className={cn(
            'w-full px-2 py-1 text-sm bg-slate-800 border border-slate-700 rounded text-white text-right focus:outline-none focus:border-blue-500',
            unit && 'pr-8',
            disabled && 'opacity-50 cursor-not-allowed',
          )}
        />
        {unit && (
          <span className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-slate-500">
            {unit}
          </span>
        )}
      </div>
    </div>
  );
}
