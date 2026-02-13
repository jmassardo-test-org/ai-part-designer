/**
 * Component Item
 * 
 * Draggable component representation for the layout editor sidebar.
 */

import React from 'react';
import { cn } from '@/lib/utils';
import type { ComponentData } from './types';

interface ComponentItemProps {
  component: ComponentData;
  onDragStart: (component: ComponentData) => void;
  disabled?: boolean;
}

export function ComponentItem({ 
  component, 
  onDragStart,
  disabled = false,
}: ComponentItemProps) {
  const handleDragStart = (e: React.DragEvent) => {
    if (disabled) {
      e.preventDefault();
      return;
    }
    e.dataTransfer.setData('component', JSON.stringify(component));
    e.dataTransfer.effectAllowed = 'copy';
    onDragStart(component);
  };

  return (
    <div
      draggable={!disabled}
      onDragStart={handleDragStart}
      className={cn(
        'flex items-center gap-3 p-2 rounded-lg border',
        'transition-colors cursor-grab active:cursor-grabbing',
        disabled 
          ? 'bg-slate-800/50 border-slate-700 opacity-50 cursor-not-allowed'
          : 'bg-slate-800 border-slate-600 hover:border-blue-500 hover:bg-slate-700',
      )}
    >
      {/* Thumbnail */}
      <div className="w-10 h-10 rounded bg-slate-700 flex items-center justify-center flex-shrink-0">
        {component.thumbnailUrl ? (
          <img 
            src={component.thumbnailUrl} 
            alt={component.name}
            className="w-full h-full object-cover rounded"
          />
        ) : (
          <svg className="w-5 h-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
          </svg>
        )}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-white truncate">
          {component.name}
        </div>
        <div className="text-xs text-slate-400">
          {component.width} × {component.depth} × {component.height} mm
        </div>
      </div>

      {/* Drag handle */}
      <div className="text-slate-500">
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8h16M4 16h16" />
        </svg>
      </div>
    </div>
  );
}
