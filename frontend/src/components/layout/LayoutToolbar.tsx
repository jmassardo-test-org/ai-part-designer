/**
 * Layout Toolbar
 * 
 * Tools for the 2D layout editor: zoom, rotation, auto-layout, etc.
 */

import React from 'react';
import { cn } from '@/lib/utils';

export type LayoutAlgorithm = 'packed' | 'grid' | 'thermal' | 'connector';

interface LayoutToolbarProps {
  zoom: number;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onZoomReset: () => void;
  onRotateSelected: () => void;
  onDeleteSelected: () => void;
  onToggleLock: () => void;
  onAutoLayout: (algorithm: LayoutAlgorithm) => void;
  onValidate: () => void;
  hasSelection: boolean;
  isLocked: boolean;
  isValidating?: boolean;
  isAutoLayouting?: boolean;
}

export function LayoutToolbar({
  zoom,
  onZoomIn,
  onZoomOut,
  onZoomReset,
  onRotateSelected,
  onDeleteSelected,
  onToggleLock,
  onAutoLayout,
  onValidate,
  hasSelection,
  isLocked,
  isValidating = false,
  isAutoLayouting = false,
}: LayoutToolbarProps) {
  const [showAutoLayoutMenu, setShowAutoLayoutMenu] = React.useState(false);

  return (
    <div className="flex items-center gap-2 p-2 bg-slate-800 border-b border-slate-700">
      {/* Zoom controls */}
      <div className="flex items-center gap-1 bg-slate-900 rounded-lg p-1">
        <ToolButton onClick={onZoomOut} title="Zoom out">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7" />
          </svg>
        </ToolButton>
        <button
          onClick={onZoomReset}
          className="px-2 py-1 text-xs text-slate-300 hover:text-white min-w-[3rem]"
          title="Reset zoom"
        >
          {Math.round(zoom * 100)}%
        </button>
        <ToolButton onClick={onZoomIn} title="Zoom in">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
          </svg>
        </ToolButton>
      </div>

      <div className="w-px h-6 bg-slate-700" />

      {/* Selection tools */}
      <div className="flex items-center gap-1">
        <ToolButton 
          onClick={onRotateSelected} 
          disabled={!hasSelection}
          title="Rotate 90° (R)"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </ToolButton>
        <ToolButton 
          onClick={onToggleLock} 
          disabled={!hasSelection}
          active={isLocked}
          title={isLocked ? 'Unlock (L)' : 'Lock position (L)'}
        >
          {isLocked ? (
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          ) : (
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 11V7a4 4 0 118 0m-4 8v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2z" />
            </svg>
          )}
        </ToolButton>
        <ToolButton 
          onClick={onDeleteSelected} 
          disabled={!hasSelection}
          title="Remove from layout (Delete)"
          variant="danger"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </ToolButton>
      </div>

      <div className="flex-1" />

      {/* Auto-layout dropdown */}
      <div className="relative">
        <button
          onClick={() => setShowAutoLayoutMenu(!showAutoLayoutMenu)}
          disabled={isAutoLayouting}
          className={cn(
            'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm',
            'bg-blue-600 hover:bg-blue-500 text-white',
            'disabled:opacity-50 disabled:cursor-not-allowed',
          )}
        >
          {isAutoLayouting ? (
            <>
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span>Arranging...</span>
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
              </svg>
              <span>Auto Layout</span>
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </>
          )}
        </button>

        {showAutoLayoutMenu && (
          <>
            <div 
              className="fixed inset-0 z-10" 
              onClick={() => setShowAutoLayoutMenu(false)} 
            />
            <div className="absolute right-0 top-full mt-1 z-20 bg-slate-800 border border-slate-600 rounded-lg shadow-xl py-1 min-w-[180px]">
              <AutoLayoutOption
                title="Packed"
                description="Dense shelf packing"
                onClick={() => {
                  onAutoLayout('packed');
                  setShowAutoLayoutMenu(false);
                }}
              />
              <AutoLayoutOption
                title="Grid"
                description="Uniform grid layout"
                onClick={() => {
                  onAutoLayout('grid');
                  setShowAutoLayoutMenu(false);
                }}
              />
              <AutoLayoutOption
                title="Thermal"
                description="Spread heat sources"
                onClick={() => {
                  onAutoLayout('thermal');
                  setShowAutoLayoutMenu(false);
                }}
              />
              <AutoLayoutOption
                title="Connector Access"
                description="Connectors at edges"
                onClick={() => {
                  onAutoLayout('connector');
                  setShowAutoLayoutMenu(false);
                }}
              />
            </div>
          </>
        )}
      </div>

      {/* Validate button */}
      <button
        onClick={onValidate}
        disabled={isValidating}
        className={cn(
          'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm',
          'bg-slate-700 hover:bg-slate-600 text-white',
          'disabled:opacity-50 disabled:cursor-not-allowed',
        )}
      >
        {isValidating ? (
          <>
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <span>Validating...</span>
          </>
        ) : (
          <>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>Validate</span>
          </>
        )}
      </button>
    </div>
  );
}

interface ToolButtonProps {
  children: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  active?: boolean;
  title?: string;
  variant?: 'default' | 'danger';
}

function ToolButton({ 
  children, 
  onClick, 
  disabled = false, 
  active = false,
  title,
  variant = 'default',
}: ToolButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={cn(
        'p-1.5 rounded transition-colors',
        disabled && 'opacity-40 cursor-not-allowed',
        !disabled && variant === 'default' && [
          active ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-700',
        ],
        !disabled && variant === 'danger' && 'text-slate-400 hover:text-red-400 hover:bg-red-500/10',
      )}
    >
      {children}
    </button>
  );
}

interface AutoLayoutOptionProps {
  title: string;
  description: string;
  onClick: () => void;
}

function AutoLayoutOption({ title, description, onClick }: AutoLayoutOptionProps) {
  return (
    <button
      onClick={onClick}
      className="w-full px-3 py-2 text-left hover:bg-slate-700 transition-colors"
    >
      <div className="text-sm font-medium text-white">{title}</div>
      <div className="text-xs text-slate-400">{description}</div>
    </button>
  );
}
