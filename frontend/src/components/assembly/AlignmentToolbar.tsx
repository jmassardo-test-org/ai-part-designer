/**
 * AlignmentToolbar Component
 *
 * UI controls for alignment guides with toggle button and settings popover.
 */

import { Magnet, Settings2 } from 'lucide-react';
import { useState, useRef, useCallback, useEffect } from 'react';
import { cn } from '@/lib/utils';
import {
  DEFAULT_ALIGNMENT_SETTINGS,
  type AlignmentSettings,
} from '../../hooks/useAlignmentGuides';

// =============================================================================
// Types
// =============================================================================

export interface AlignmentToolbarProps {
  /** Whether alignment guides are enabled. */
  enabled: boolean;
  /** Callback when alignment is toggled. */
  onToggle: () => void;
  /** Current alignment settings. */
  settings: AlignmentSettings;
  /** Callback when settings change. */
  onSettingsChange: (settings: Partial<AlignmentSettings>) => void;
  /** Optional class name for styling. */
  className?: string;
}

// =============================================================================
// Constants
// =============================================================================

/** Slider constraints. */
const SNAP_DISTANCE_MIN = 2;
const SNAP_DISTANCE_MAX = 30;
const SNAP_DISTANCE_STEP = 1;

const GRID_SNAP_MIN = 1;
const GRID_SNAP_MAX = 25;
const GRID_SNAP_STEP = 1;

// =============================================================================
// Component
// =============================================================================

/**
 * Toolbar component for controlling alignment guides.
 *
 * Features:
 * - Toggle button with magnet icon
 * - Popover with alignment type toggles
 * - Snap distance slider
 * - Keyboard accessible (A key handled by parent)
 *
 * @example
 * ```tsx
 * <AlignmentToolbar
 *   enabled={alignmentEnabled}
 *   onToggle={() => setAlignmentEnabled(!alignmentEnabled)}
 *   settings={alignmentSettings}
 *   onSettingsChange={updateSettings}
 * />
 * ```
 */
export function AlignmentToolbar({
  enabled,
  onToggle,
  settings,
  onSettingsChange,
  className,
}: AlignmentToolbarProps): JSX.Element {
  const [showPopover, setShowPopover] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  // Close popover when clicking outside
  useEffect(() => {
    if (!showPopover) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(e.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(e.target as Node)
      ) {
        setShowPopover(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showPopover]);

  // Handle primary button click
  const handleButtonClick = useCallback(() => {
    onToggle();
  }, [onToggle]);

  // Handle settings button click
  const handleSettingsClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      setShowPopover((prev) => !prev);
    },
    []
  );

  // Handle checkbox change
  const handleCheckboxChange = useCallback(
    (key: keyof AlignmentSettings) => (e: React.ChangeEvent<HTMLInputElement>) => {
      onSettingsChange({ [key]: e.target.checked });
    },
    [onSettingsChange]
  );

  // Handle snap distance change
  const handleSnapDistanceChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = parseInt(e.target.value, 10);
      onSettingsChange({ snapDistance: value });
    },
    [onSettingsChange]
  );

  // Handle snap threshold change (based on distance)
  const handleSnapThresholdChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = parseInt(e.target.value, 10);
      onSettingsChange({ snapThreshold: value });
    },
    [onSettingsChange]
  );

  return (
    <div className={cn('relative', className)}>
      {/* Main button group */}
      <div className="flex items-center">
        {/* Alignment toggle button */}
        <button
          ref={buttonRef}
          onClick={handleButtonClick}
          className={cn(
            'p-2 rounded-l transition-colors',
            enabled
              ? 'bg-primary-600 text-white'
              : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
          )}
          title={enabled ? 'Alignment Guides On (A)' : 'Alignment Guides Off (A)'}
          aria-label={enabled ? 'Disable alignment guides' : 'Enable alignment guides'}
          aria-pressed={enabled}
        >
          <Magnet className="w-5 h-5" />
        </button>

        {/* Settings button */}
        <button
          onClick={handleSettingsClick}
          className={cn(
            'p-2 rounded-r border-l transition-colors',
            enabled
              ? 'bg-primary-600 text-white border-primary-500'
              : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 border-gray-200 dark:border-gray-600'
          )}
          title="Alignment settings"
          aria-label="Alignment settings"
          aria-expanded={showPopover}
          aria-haspopup="dialog"
        >
          <Settings2 className="w-4 h-4" />
        </button>
      </div>

      {/* Settings popover */}
      {showPopover && (
        <div
          ref={popoverRef}
          role="dialog"
          aria-label="Alignment settings"
          className={cn(
            'absolute left-full top-0 ml-2 w-64 p-4',
            'bg-white dark:bg-gray-800 rounded-lg shadow-lg',
            'border border-gray-200 dark:border-gray-700',
            'z-50'
          )}
        >
          <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
            Alignment Guides
          </h4>

          {/* Alignment type toggles */}
          <div className="space-y-2 mb-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.enableEdgeAlignment}
                onChange={handleCheckboxChange('enableEdgeAlignment')}
                className="w-4 h-4 text-primary-600 bg-gray-100 border-gray-300 rounded focus:ring-primary-500 dark:bg-gray-700 dark:border-gray-600"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">Edge alignment</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.enableCenterAlignment}
                onChange={handleCheckboxChange('enableCenterAlignment')}
                className="w-4 h-4 text-primary-600 bg-gray-100 border-gray-300 rounded focus:ring-primary-500 dark:bg-gray-700 dark:border-gray-600"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">Center alignment</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.enableFaceAlignment}
                onChange={handleCheckboxChange('enableFaceAlignment')}
                className="w-4 h-4 text-primary-600 bg-gray-100 border-gray-300 rounded focus:ring-primary-500 dark:bg-gray-700 dark:border-gray-600"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">Face alignment</span>
            </label>
          </div>

          {/* Snap Distance slider */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Snap Distance
            </label>
            <input
              type="range"
              min={SNAP_DISTANCE_MIN}
              max={SNAP_DISTANCE_MAX}
              step={SNAP_DISTANCE_STEP}
              value={settings.snapDistance}
              onChange={handleSnapDistanceChange}
              className={cn(
                'w-full h-2 rounded-lg appearance-none cursor-pointer',
                'bg-gray-200 dark:bg-gray-700',
                '[&::-webkit-slider-thumb]:appearance-none',
                '[&::-webkit-slider-thumb]:w-4',
                '[&::-webkit-slider-thumb]:h-4',
                '[&::-webkit-slider-thumb]:rounded-full',
                '[&::-webkit-slider-thumb]:bg-primary-600',
                '[&::-webkit-slider-thumb]:cursor-pointer',
                '[&::-moz-range-thumb]:w-4',
                '[&::-moz-range-thumb]:h-4',
                '[&::-moz-range-thumb]:rounded-full',
                '[&::-moz-range-thumb]:bg-primary-600',
                '[&::-moz-range-thumb]:border-0',
                '[&::-moz-range-thumb]:cursor-pointer'
              )}
              aria-label="Snap distance"
              aria-valuenow={settings.snapDistance}
              aria-valuemin={SNAP_DISTANCE_MIN}
              aria-valuemax={SNAP_DISTANCE_MAX}
            />
            <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
              <span>{SNAP_DISTANCE_MIN}</span>
              <span className="font-medium text-gray-900 dark:text-gray-100">
                {settings.snapDistance} units
              </span>
              <span>{SNAP_DISTANCE_MAX}</span>
            </div>
          </div>

          {/* Grid Snap Increment slider */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Grid Snap Increment
            </label>
            <input
              type="range"
              min={GRID_SNAP_MIN}
              max={GRID_SNAP_MAX}
              step={GRID_SNAP_STEP}
              value={settings.snapThreshold}
              onChange={handleSnapThresholdChange}
              className={cn(
                'w-full h-2 rounded-lg appearance-none cursor-pointer',
                'bg-gray-200 dark:bg-gray-700',
                '[&::-webkit-slider-thumb]:appearance-none',
                '[&::-webkit-slider-thumb]:w-4',
                '[&::-webkit-slider-thumb]:h-4',
                '[&::-webkit-slider-thumb]:rounded-full',
                '[&::-webkit-slider-thumb]:bg-primary-600',
                '[&::-webkit-slider-thumb]:cursor-pointer',
                '[&::-moz-range-thumb]:w-4',
                '[&::-moz-range-thumb]:h-4',
                '[&::-moz-range-thumb]:rounded-full',
                '[&::-moz-range-thumb]:bg-primary-600',
                '[&::-moz-range-thumb]:border-0',
                '[&::-moz-range-thumb]:cursor-pointer'
              )}
              aria-label="Grid snap increment"
              aria-valuenow={settings.snapThreshold}
              aria-valuemin={GRID_SNAP_MIN}
              aria-valuemax={GRID_SNAP_MAX}
            />
            <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
              <span>{GRID_SNAP_MIN}</span>
              <span className="font-medium text-gray-900 dark:text-gray-100">
                {settings.snapThreshold} units
              </span>
              <span>{GRID_SNAP_MAX}</span>
            </div>
          </div>

          {/* Hint */}
          <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">
            Hold Alt while dragging to temporarily disable snapping.
          </p>
        </div>
      )}
    </div>
  );
}

export default AlignmentToolbar;
