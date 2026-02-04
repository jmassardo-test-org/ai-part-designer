/**
 * Layout Page
 * 
 * Full-featured layout editor page with 2D editor and 3D preview.
 */

import React, { useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { LayoutEditor, LayoutPreview3D } from '@/components/layout';
import type { LayoutAlgorithm } from '@/components/layout/LayoutToolbar';
import { 
  apiToLayoutDimensions, 
  apiToPlacement,
  type ComponentData, 
  type ComponentPlacement, 
  type LayoutDimensions,
  type ValidationResult,
} from '@/components/layout/types';
import { 
  useLayout, 
  useUpdateLayout, 
  useAddPlacement, 
  useUpdatePlacement, 
  useRemovePlacement,
  useValidateLayout,
  useAutoLayout,
} from '@/hooks/useLayout';
import { cn } from '@/lib/utils';

type ViewMode = '2d' | '3d' | 'split';

export function LayoutPage() {
  const { layoutId } = useParams<{ layoutId: string }>();
  const navigate = useNavigate();
  const [viewMode, setViewMode] = useState<ViewMode>('split');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // API hooks
  const { data: layout, isLoading, error } = useLayout(layoutId);
  const updateLayoutMutation = useUpdateLayout();
  const addPlacementMutation = useAddPlacement();
  const updatePlacementMutation = useUpdatePlacement();
  const removePlacementMutation = useRemovePlacement();
  const validateMutation = useValidateLayout();
  const autoLayoutMutation = useAutoLayout();

  // TODO: Fetch from project's reference components
  const availableComponents: ComponentData[] = [
    { id: '1', name: 'Arduino Nano', width: 18, depth: 45, height: 8 },
    { id: '2', name: 'Raspberry Pi 4', width: 56, depth: 85, height: 20 },
    { id: '3', name: 'USB-C Port', width: 9, depth: 7, height: 3.5, connectorFaces: ['back'] },
    { id: '4', name: 'Power Regulator', width: 15, depth: 20, height: 10, isThermalSource: true },
    { id: '5', name: 'OLED Display', width: 27, depth: 27, height: 4, connectorFaces: ['front'] },
    { id: '6', name: 'Button Switch', width: 12, depth: 12, height: 8, connectorFaces: ['top'] },
  ];

  // Convert API data to component format
  const dimensions: LayoutDimensions = layout 
    ? apiToLayoutDimensions(layout)
    : { width: 100, depth: 80, height: 40, gridSize: 5, clearance: 2, autoDimensions: false };

  const placements: ComponentPlacement[] = layout?.placements.map(apiToPlacement) || [];

  // Handlers
  const handleDimensionsChange = useCallback((updates: Partial<LayoutDimensions>) => {
    if (!layoutId) return;
    
    const apiUpdates: Record<string, any> = {};
    if (updates.width !== undefined) apiUpdates.internalWidth = updates.width;
    if (updates.depth !== undefined) apiUpdates.internalDepth = updates.depth;
    if (updates.height !== undefined) apiUpdates.internalHeight = updates.height;
    if (updates.gridSize !== undefined) apiUpdates.gridSize = updates.gridSize;
    if (updates.clearance !== undefined) apiUpdates.clearanceMargin = updates.clearance;
    if (updates.autoDimensions !== undefined) apiUpdates.autoDimensions = updates.autoDimensions;

    updateLayoutMutation.mutate({ layoutId, updates: apiUpdates });
  }, [layoutId, updateLayoutMutation]);

  const handleAddPlacement = useCallback((component: ComponentData, x: number, y: number) => {
    if (!layoutId) return;

    addPlacementMutation.mutate({
      layoutId,
      componentId: component.id,
      xPosition: x,
      yPosition: y,
      zPosition: 0,
      rotationZ: 0,
      width: component.width,
      depth: component.depth,
      height: component.height,
    });
  }, [layoutId, addPlacementMutation]);

  const handleUpdatePlacement = useCallback((id: string, updates: Partial<ComponentPlacement>) => {
    if (!layoutId) return;

    const apiUpdates: Record<string, any> = {};
    if (updates.x !== undefined) apiUpdates.xPosition = updates.x;
    if (updates.y !== undefined) apiUpdates.yPosition = updates.y;
    if (updates.z !== undefined) apiUpdates.zPosition = updates.z;
    if (updates.rotation !== undefined) apiUpdates.rotationZ = updates.rotation;
    if (updates.faceDirection !== undefined) apiUpdates.faceDirection = updates.faceDirection;
    if (updates.locked !== undefined) apiUpdates.locked = updates.locked;

    updatePlacementMutation.mutate({ layoutId, placementId: id, updates: apiUpdates });
  }, [layoutId, updatePlacementMutation]);

  const handleRemovePlacement = useCallback((id: string) => {
    if (!layoutId) return;
    removePlacementMutation.mutate({ layoutId, placementId: id });
  }, [layoutId, removePlacementMutation]);

  const handleAutoLayout = useCallback(async (algorithm: LayoutAlgorithm) => {
    if (!layoutId) return;
    await autoLayoutMutation.mutateAsync({ layoutId, algorithm });
  }, [layoutId, autoLayoutMutation]);

  const handleValidate = useCallback(async (): Promise<ValidationResult> => {
    if (!layoutId) {
      return { valid: false, errors: [], warnings: [] };
    }
    return validateMutation.mutateAsync(layoutId);
  }, [layoutId, validateMutation]);

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center bg-slate-900">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-red-400 mb-2">Error loading layout</h2>
          <p className="text-slate-400 mb-4">{(error as Error).message}</p>
          <button
            onClick={() => navigate(-1)}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-white"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-screen bg-slate-900">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-2 bg-slate-800 border-b border-slate-700">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(-1)}
            className="p-1.5 text-slate-400 hover:text-white rounded"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
          </button>
          <div>
            <h1 className="text-lg font-semibold text-white">
              {layout?.name || 'Layout Editor'}
            </h1>
            <p className="text-xs text-slate-400">
              {dimensions.width} × {dimensions.depth} × {dimensions.height} mm
            </p>
          </div>
        </div>

        {/* View mode toggle */}
        <div className="flex items-center gap-1 bg-slate-900 rounded-lg p-1">
          <ViewModeButton
            active={viewMode === '2d'}
            onClick={() => setViewMode('2d')}
          >
            2D
          </ViewModeButton>
          <ViewModeButton
            active={viewMode === 'split'}
            onClick={() => setViewMode('split')}
          >
            Split
          </ViewModeButton>
          <ViewModeButton
            active={viewMode === '3d'}
            onClick={() => setViewMode('3d')}
          >
            3D
          </ViewModeButton>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <button
            className="px-3 py-1.5 text-sm bg-slate-700 hover:bg-slate-600 rounded-lg text-white"
          >
            Export
          </button>
          <button
            className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-500 rounded-lg text-white"
          >
            Generate Enclosure
          </button>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {viewMode === '2d' && (
          <LayoutEditor
            layoutId={layoutId!}
            dimensions={dimensions}
            placements={placements}
            availableComponents={availableComponents}
            onDimensionsChange={handleDimensionsChange}
            onAddPlacement={handleAddPlacement}
            onUpdatePlacement={handleUpdatePlacement}
            onRemovePlacement={handleRemovePlacement}
            onAutoLayout={handleAutoLayout}
            onValidate={handleValidate}
            isLoading={isLoading}
          />
        )}

        {viewMode === '3d' && (
          <div className="flex-1">
            <LayoutPreview3D
              dimensions={dimensions}
              placements={placements}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          </div>
        )}

        {viewMode === 'split' && (
          <>
            <div className="flex-1 border-r border-slate-700">
              <LayoutEditor
                layoutId={layoutId!}
                dimensions={dimensions}
                placements={placements}
                availableComponents={availableComponents}
                onDimensionsChange={handleDimensionsChange}
                onAddPlacement={handleAddPlacement}
                onUpdatePlacement={handleUpdatePlacement}
                onRemovePlacement={handleRemovePlacement}
                onAutoLayout={handleAutoLayout}
                onValidate={handleValidate}
                isLoading={isLoading}
              />
            </div>
            <div className="w-1/3 min-w-[300px]">
              <LayoutPreview3D
                dimensions={dimensions}
                placements={placements}
                selectedId={selectedId}
                onSelect={setSelectedId}
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

interface ViewModeButtonProps {
  children: React.ReactNode;
  active: boolean;
  onClick: () => void;
}

function ViewModeButton({ children, active, onClick }: ViewModeButtonProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'px-3 py-1 text-sm rounded transition-colors',
        active 
          ? 'bg-blue-600 text-white' 
          : 'text-slate-400 hover:text-white',
      )}
    >
      {children}
    </button>
  );
}
