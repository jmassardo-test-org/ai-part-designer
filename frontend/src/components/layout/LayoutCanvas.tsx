/**
 * Layout Canvas Component
 * 
 * Interactive 2D canvas for arranging components within an enclosure.
 * Supports drag-and-drop, rotation, snapping, and collision detection.
 */

import { useRef, useState, useCallback, useMemo } from 'react';
import { cn } from '@/lib/utils';
import type { 
  ComponentPlacement, 
  LayoutDimensions, 
  CanvasState,
} from './types';

interface LayoutCanvasProps {
  dimensions: LayoutDimensions;
  placements: ComponentPlacement[];
  gridSize: number;
  clearanceMargin: number;
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  onMove: (id: string, x: number, y: number) => void;
  onRotate: (id: string) => void;
  showGrid?: boolean;
  showClearance?: boolean;
  readOnly?: boolean;
}

// Scale: 1mm = 2px at zoom 1.0
const SCALE = 2;

export function LayoutCanvas({
  dimensions,
  placements,
  gridSize,
  clearanceMargin,
  selectedId,
  onSelect,
  onMove,
  onRotate,
  showGrid = true,
  showClearance = true,
  readOnly = false,
}: LayoutCanvasProps) {
  const canvasRef = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<CanvasState>({
    zoom: 1,
    panX: 0,
    panY: 0,
    selectedId: null,
    isDragging: false,
    dragOffset: { x: 0, y: 0 },
  });

  // Canvas dimensions in pixels
  const canvasWidth = dimensions.width * SCALE * state.zoom;
  const canvasHeight = dimensions.depth * SCALE * state.zoom;

  // Grid pattern
  const gridPattern = useMemo(() => {
    const gridPx = gridSize * SCALE * state.zoom;
    return `repeating-linear-gradient(
      0deg,
      transparent,
      transparent ${gridPx - 1}px,
      rgba(100, 100, 100, 0.2) ${gridPx - 1}px,
      rgba(100, 100, 100, 0.2) ${gridPx}px
    ),
    repeating-linear-gradient(
      90deg,
      transparent,
      transparent ${gridPx - 1}px,
      rgba(100, 100, 100, 0.2) ${gridPx - 1}px,
      rgba(100, 100, 100, 0.2) ${gridPx}px
    )`;
  }, [gridSize, state.zoom]);

  // Snap position to grid
  const snapToGrid = useCallback((value: number): number => {
    return Math.round(value / gridSize) * gridSize;
  }, [gridSize]);

  // Handle mouse down on component
  const handleComponentMouseDown = useCallback((
    e: React.MouseEvent,
    placement: ComponentPlacement
  ) => {
    if (readOnly || placement.locked) return;
    e.stopPropagation();

    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;

    const clickX = (e.clientX - rect.left) / (SCALE * state.zoom);
    const clickY = (e.clientY - rect.top) / (SCALE * state.zoom);

    setState(prev => ({
      ...prev,
      isDragging: true,
      selectedId: placement.id,
      dragOffset: {
        x: clickX - placement.x,
        y: clickY - placement.y,
      },
    }));
    onSelect(placement.id);
  }, [readOnly, state.zoom, onSelect]);

  // Handle mouse move for dragging
  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!state.isDragging || !state.selectedId) return;

    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;

    const mouseX = (e.clientX - rect.left) / (SCALE * state.zoom);
    const mouseY = (e.clientY - rect.top) / (SCALE * state.zoom);

    let newX = mouseX - state.dragOffset.x;
    let newY = mouseY - state.dragOffset.y;

    // Snap to grid
    newX = snapToGrid(newX);
    newY = snapToGrid(newY);

    // Clamp to enclosure bounds
    const placement = placements.find(p => p.id === state.selectedId);
    if (placement) {
      newX = Math.max(0, Math.min(newX, dimensions.width - placement.width));
      newY = Math.max(0, Math.min(newY, dimensions.depth - placement.depth));
    }

    onMove(state.selectedId, newX, newY);
  }, [state, placements, dimensions, snapToGrid, onMove]);

  // Handle mouse up
  const handleMouseUp = useCallback(() => {
    setState(prev => ({
      ...prev,
      isDragging: false,
    }));
  }, []);

  // Handle canvas click (deselect)
  const handleCanvasClick = useCallback((e: React.MouseEvent) => {
    if (e.target === canvasRef.current) {
      onSelect(null);
    }
  }, [onSelect]);

  // Handle double-click to rotate
  const handleDoubleClick = useCallback((
    e: React.MouseEvent,
    placement: ComponentPlacement
  ) => {
    if (readOnly || placement.locked) return;
    e.stopPropagation();
    onRotate(placement.id);
  }, [readOnly, onRotate]);

  // Handle zoom with wheel
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setState(prev => ({
      ...prev,
      zoom: Math.max(0.25, Math.min(4, prev.zoom * delta)),
    }));
  }, []);

  // Check for collisions
  const getCollisions = useCallback((placement: ComponentPlacement): string[] => {
    const collisions: string[] = [];
    for (const other of placements) {
      if (other.id === placement.id) continue;
      
      // Check bounding box overlap with clearance
      const margin = clearanceMargin;
      const aLeft = placement.x - margin;
      const aRight = placement.x + placement.width + margin;
      const aTop = placement.y - margin;
      const aBottom = placement.y + placement.depth + margin;
      
      const bLeft = other.x;
      const bRight = other.x + other.width;
      const bTop = other.y;
      const bBottom = other.y + other.depth;
      
      if (aRight > bLeft && aLeft < bRight && aBottom > bTop && aTop < bBottom) {
        collisions.push(other.id);
      }
    }
    return collisions;
  }, [placements, clearanceMargin]);

  return (
    <div 
      className="relative overflow-auto bg-slate-900 rounded-lg border border-slate-700"
      style={{ minHeight: '400px' }}
      onWheel={handleWheel}
    >
      {/* Canvas area */}
      <div
        ref={canvasRef}
        className="relative cursor-crosshair"
        style={{
          width: canvasWidth,
          height: canvasHeight,
          margin: '20px',
          backgroundColor: '#1e293b',
          backgroundImage: showGrid ? gridPattern : 'none',
          border: '2px solid #475569',
          borderRadius: '4px',
        }}
        onClick={handleCanvasClick}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        {/* Enclosure boundary label */}
        <div className="absolute -top-6 left-0 text-xs text-slate-400">
          {dimensions.width}mm × {dimensions.depth}mm
        </div>

        {/* Component placements */}
        {placements.map(placement => {
          const isSelected = placement.id === selectedId;
          const collisions = getCollisions(placement);
          const hasCollision = collisions.length > 0;
          
          const style: React.CSSProperties = {
            position: 'absolute',
            left: placement.x * SCALE * state.zoom,
            top: placement.y * SCALE * state.zoom,
            width: placement.width * SCALE * state.zoom,
            height: placement.depth * SCALE * state.zoom,
            transform: `rotate(${placement.rotation}deg)`,
            transformOrigin: 'center center',
            cursor: placement.locked ? 'not-allowed' : (state.isDragging ? 'grabbing' : 'grab'),
          };

          return (
            <div
              key={placement.id}
              style={style}
              className={cn(
                'rounded transition-shadow',
                'flex items-center justify-center',
                'text-xs font-medium text-white',
                'border-2',
                isSelected && 'ring-2 ring-blue-500 ring-offset-2 ring-offset-slate-900',
                hasCollision && 'border-red-500 bg-red-500/30',
                !hasCollision && !isSelected && 'border-slate-500 bg-slate-600/50',
                !hasCollision && isSelected && 'border-blue-500 bg-blue-500/30',
                placement.locked && 'opacity-75'
              )}
              onMouseDown={(e) => handleComponentMouseDown(e, placement)}
              onDoubleClick={(e) => handleDoubleClick(e, placement)}
            >
              {/* Component label */}
              <span className="truncate px-1 select-none pointer-events-none">
                {placement.name}
              </span>

              {/* Lock indicator */}
              {placement.locked && (
                <div className="absolute top-0.5 right-0.5">
                  <svg className="w-3 h-3 text-slate-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                  </svg>
                </div>
              )}

              {/* Rotation indicator */}
              {placement.rotation !== 0 && (
                <div className="absolute bottom-0.5 right-0.5 text-[10px] text-slate-400">
                  {placement.rotation}°
                </div>
              )}

              {/* Clearance zone visualization */}
              {showClearance && isSelected && (
                <div
                  className="absolute border border-dashed border-yellow-500/50 pointer-events-none"
                  style={{
                    left: -clearanceMargin * SCALE * state.zoom,
                    top: -clearanceMargin * SCALE * state.zoom,
                    right: -clearanceMargin * SCALE * state.zoom,
                    bottom: -clearanceMargin * SCALE * state.zoom,
                  }}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Zoom indicator */}
      <div className="absolute bottom-2 right-2 bg-slate-800 px-2 py-1 rounded text-xs text-slate-400">
        {Math.round(state.zoom * 100)}%
      </div>
    </div>
  );
}
