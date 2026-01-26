/**
 * Layout Editor
 * 
 * Main component that combines canvas, toolbar, and sidebar
 * for 2D spatial layout editing.
 */

import React from 'react';
import { LayoutCanvas } from './LayoutCanvas';
import { LayoutToolbar, type LayoutAlgorithm } from './LayoutToolbar';
import { LayoutSidebar } from './LayoutSidebar';
import type { 
  ComponentData, 
  ComponentPlacement, 
  LayoutDimensions,
  ValidationResult,
} from './types';

interface LayoutEditorProps {
  layoutId: string;
  dimensions: LayoutDimensions;
  placements: ComponentPlacement[];
  availableComponents: ComponentData[];
  onDimensionsChange: (dimensions: Partial<LayoutDimensions>) => void;
  onAddPlacement: (component: ComponentData, x: number, y: number) => void;
  onUpdatePlacement: (id: string, updates: Partial<ComponentPlacement>) => void;
  onRemovePlacement: (id: string) => void;
  onAutoLayout: (algorithm: LayoutAlgorithm) => Promise<void>;
  onValidate: () => Promise<ValidationResult>;
  isLoading?: boolean;
}

export function LayoutEditor({
  // layoutId is passed for API operations but managed at parent level
  dimensions,
  placements,
  availableComponents,
  onDimensionsChange,
  onAddPlacement,
  onUpdatePlacement,
  onRemovePlacement,
  onAutoLayout,
  onValidate,
  isLoading = false,
}: LayoutEditorProps) {
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [zoom, setZoom] = React.useState(1);
  const [draggingComponent, setDraggingComponent] = React.useState<ComponentData | null>(null);
  const [isAutoLayouting, setIsAutoLayouting] = React.useState(false);
  const [isValidating, setIsValidating] = React.useState(false);
  const [validationResult, setValidationResult] = React.useState<ValidationResult | null>(null);

  const selectedPlacement = placements.find(p => p.id === selectedId);

  // Keyboard shortcuts
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!selectedPlacement || selectedPlacement.locked) return;

      switch (e.key) {
        case 'Delete':
        case 'Backspace':
          e.preventDefault();
          handleDeleteSelected();
          break;
        case 'r':
        case 'R':
          e.preventDefault();
          handleRotateSelected();
          break;
        case 'l':
        case 'L':
          e.preventDefault();
          handleToggleLock();
          break;
        case 'Escape':
          setSelectedId(null);
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedPlacement]);

  const handleZoomIn = () => setZoom(z => Math.min(z * 1.25, 4));
  const handleZoomOut = () => setZoom(z => Math.max(z / 1.25, 0.25));
  const handleZoomReset = () => setZoom(1);

  const handleRotateSelected = () => {
    if (!selectedPlacement || selectedPlacement.locked) return;
    onUpdatePlacement(selectedPlacement.id, { 
      rotation: (selectedPlacement.rotation + 90) % 360 
    });
  };

  const handleDeleteSelected = () => {
    if (!selectedPlacement) return;
    onRemovePlacement(selectedPlacement.id);
    setSelectedId(null);
  };

  const handleToggleLock = () => {
    if (!selectedPlacement) return;
    onUpdatePlacement(selectedPlacement.id, { 
      locked: !selectedPlacement.locked 
    });
  };

  const handleAutoLayout = async (algorithm: LayoutAlgorithm) => {
    setIsAutoLayouting(true);
    try {
      await onAutoLayout(algorithm);
      setValidationResult(null);
    } finally {
      setIsAutoLayouting(false);
    }
  };

  const handleValidate = async () => {
    setIsValidating(true);
    try {
      const result = await onValidate();
      setValidationResult(result);
    } finally {
      setIsValidating(false);
    }
  };

  const handleDrop = (x: number, y: number) => {
    if (!draggingComponent) return;
    
    // Snap to grid
    const snappedX = Math.round(x / dimensions.gridSize) * dimensions.gridSize;
    const snappedY = Math.round(y / dimensions.gridSize) * dimensions.gridSize;
    
    onAddPlacement(draggingComponent, snappedX, snappedY);
    setDraggingComponent(null);
  };

  return (
    <div className="flex h-full bg-slate-900">
      {/* Main canvas area */}
      <div className="flex-1 flex flex-col min-w-0">
        <LayoutToolbar
          zoom={zoom}
          onZoomIn={handleZoomIn}
          onZoomOut={handleZoomOut}
          onZoomReset={handleZoomReset}
          onRotateSelected={handleRotateSelected}
          onDeleteSelected={handleDeleteSelected}
          onToggleLock={handleToggleLock}
          onAutoLayout={handleAutoLayout}
          onValidate={handleValidate}
          hasSelection={!!selectedPlacement}
          isLocked={selectedPlacement?.locked ?? false}
          isAutoLayouting={isAutoLayouting}
          isValidating={isValidating}
        />

        {/* Validation results banner */}
        {validationResult && (
          <ValidationBanner 
            result={validationResult} 
            onDismiss={() => setValidationResult(null)}
          />
        )}

        {/* Canvas */}
        <div className="flex-1 relative overflow-hidden">
          {isLoading ? (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-900/80">
              <div className="flex flex-col items-center gap-3">
                <svg className="w-8 h-8 animate-spin text-blue-500" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                <span className="text-slate-400 text-sm">Loading layout...</span>
              </div>
            </div>
          ) : (
            <LayoutCanvas
              dimensions={dimensions}
              placements={placements}
              gridSize={dimensions.gridSize}
              clearanceMargin={dimensions.clearance}
              selectedId={selectedId}
              onSelect={setSelectedId}
              onMove={(id, x, y) => onUpdatePlacement(id, { x, y })}
              onRotate={(id) => {
                const p = placements.find(p => p.id === id);
                if (p) onUpdatePlacement(id, { rotation: (p.rotation + 90) % 360 });
              }}
            />
          )}
        </div>
      </div>

      {/* Sidebar */}
      <LayoutSidebar
        availableComponents={availableComponents}
        placements={placements}
        selectedId={selectedId}
        dimensions={dimensions}
        onComponentDragStart={setDraggingComponent}
        onSelectPlacement={setSelectedId}
        onUpdatePlacement={onUpdatePlacement}
        onDimensionsChange={onDimensionsChange}
      />
    </div>
  );
}

interface ValidationBannerProps {
  result: ValidationResult;
  onDismiss: () => void;
}

function ValidationBanner({ result, onDismiss }: ValidationBannerProps) {
  const hasErrors = result.errors.length > 0;
  const hasWarnings = result.warnings.length > 0;

  if (!hasErrors && !hasWarnings) {
    return (
      <div className="flex items-center justify-between px-4 py-2 bg-green-900/30 border-b border-green-700">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-sm text-green-300">Layout is valid! No collisions or boundary issues detected.</span>
        </div>
        <button onClick={onDismiss} className="text-green-400 hover:text-green-300">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    );
  }

  return (
    <div className={`px-4 py-2 border-b ${hasErrors ? 'bg-red-900/30 border-red-700' : 'bg-yellow-900/30 border-yellow-700'}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          {hasErrors && (
            <div className="flex items-start gap-2 mb-1">
              <svg className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <span className="text-sm font-medium text-red-300">
                  {result.errors.length} error{result.errors.length !== 1 ? 's' : ''} found:
                </span>
                <ul className="text-xs text-red-200 mt-1 space-y-0.5">
                  {result.errors.slice(0, 3).map((err, i) => (
                    <li key={i}>• {err.message}</li>
                  ))}
                  {result.errors.length > 3 && (
                    <li>• ...and {result.errors.length - 3} more</li>
                  )}
                </ul>
              </div>
            </div>
          )}
          {hasWarnings && (
            <div className="flex items-start gap-2">
              <svg className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <div>
                <span className="text-sm font-medium text-yellow-300">
                  {result.warnings.length} warning{result.warnings.length !== 1 ? 's' : ''}
                </span>
                <ul className="text-xs text-yellow-200 mt-1 space-y-0.5">
                  {result.warnings.slice(0, 2).map((warn, i) => (
                    <li key={i}>• {warn.message}</li>
                  ))}
                  {result.warnings.length > 2 && (
                    <li>• ...and {result.warnings.length - 2} more</li>
                  )}
                </ul>
              </div>
            </div>
          )}
        </div>
        <button 
          onClick={onDismiss} 
          className={`${hasErrors ? 'text-red-400 hover:text-red-300' : 'text-yellow-400 hover:text-yellow-300'}`}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}

// Export type for external use
export type { LayoutAlgorithm };
