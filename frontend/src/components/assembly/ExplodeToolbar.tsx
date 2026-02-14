/**
 * ExplodeToolbar Component
 *
 * UI controls for exploded view with toggle button and distance slider popover.
 */

import { Expand, Shrink, Settings2 } from 'lucide-react';
import { useState, useRef, useCallback, useEffect } from 'react';
import { cn } from '@/lib/utils';
import {
  MIN_DISTANCE_MULTIPLIER,
  MAX_DISTANCE_MULTIPLIER,
  type ExplodeState,
} from '../../hooks/useExplodedView';

// =============================================================================
// Types
// =============================================================================

export interface ExplodeToolbarProps {
  /** Current state of the explode state machine. */
  state: ExplodeState;
  /** Whether an animation is currently in progress. */
  isAnimating: boolean;
  /** Current distance multiplier (0.5 to 3.0). */
  distanceMultiplier: number;
  /** Callback when explode is toggled. */
  onToggle: () => void;
  /** Callback when distance multiplier changes. */
  onDistanceChange: (value: number) => void;
  /** Optional class name for styling. */
  className?: string;
}

// =============================================================================
// Constants
// =============================================================================

/** Step size for the distance slider. */
const SLIDER_STEP = 0.25;

// =============================================================================
// Component
// =============================================================================

/**
 * Toolbar component for controlling exploded view.
 *
 * Features:
 * - Toggle button with expand/shrink icon
 * - Popover with distance multiplier slider
 * - Keyboard accessible (E key handled by parent)
 *
 * @example
 * ```tsx
 * <ExplodeToolbar
 *   state={explodeState}
 *   isAnimating={isAnimating}
 *   distanceMultiplier={distanceMultiplier}
 *   onToggle={toggle}
 *   onDistanceChange={setDistanceMultiplier}
 * />
 * ```
 */
export function ExplodeToolbar({
  state,
  isAnimating,
  distanceMultiplier,
  onToggle,
  onDistanceChange,
  className,
}: ExplodeToolbarProps): JSX.Element {
  const [showPopover, setShowPopover] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const isExploded = state === 'exploded' || state === 'exploding';
  const isActive = state !== 'collapsed';

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

  // Handle slider change
  const handleSliderChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = parseFloat(e.target.value);
      onDistanceChange(value);
    },
    [onDistanceChange]
  );

  // Format multiplier for display
  const formatMultiplier = (value: number): string => {
    return `${value.toFixed(2)}x`;
  };

  return (
    <div className={cn('relative', className)}>
      {/* Main button group */}
      <div className="flex items-center">
        {/* Explode toggle button */}
        <button
          ref={buttonRef}
          onClick={handleButtonClick}
          disabled={isAnimating}
          className={cn(
            'p-2 rounded-l transition-colors',
            isActive
              ? 'bg-primary-600 text-white'
              : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700',
            isAnimating && 'opacity-70 cursor-wait'
          )}
          title={isExploded ? 'Collapse view (E)' : 'Exploded view (E)'}
          aria-label={isExploded ? 'Collapse view' : 'Exploded view'}
          aria-pressed={isExploded}
        >
          {isExploded ? (
            <Shrink className="w-5 h-5" />
          ) : (
            <Expand className="w-5 h-5" />
          )}
        </button>

        {/* Settings button */}
        <button
          onClick={handleSettingsClick}
          className={cn(
            'p-2 rounded-r border-l transition-colors',
            isActive
              ? 'bg-primary-600 text-white border-primary-500'
              : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 border-gray-200 dark:border-gray-600'
          )}
          title="Explosion settings"
          aria-label="Explosion settings"
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
          aria-label="Explosion distance settings"
          className={cn(
            'absolute left-full top-0 ml-2 w-56 p-4',
            'bg-white dark:bg-gray-800 rounded-lg shadow-lg',
            'border border-gray-200 dark:border-gray-700',
            'z-50'
          )}
        >
          <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
            Explosion Distance
          </h4>

          {/* Slider */}
          <div className="space-y-2">
            <input
              type="range"
              min={MIN_DISTANCE_MULTIPLIER}
              max={MAX_DISTANCE_MULTIPLIER}
              step={SLIDER_STEP}
              value={distanceMultiplier}
              onChange={handleSliderChange}
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
              aria-label="Explosion distance multiplier"
              aria-valuenow={distanceMultiplier}
              aria-valuemin={MIN_DISTANCE_MULTIPLIER}
              aria-valuemax={MAX_DISTANCE_MULTIPLIER}
            />

            {/* Value labels */}
            <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
              <span>{formatMultiplier(MIN_DISTANCE_MULTIPLIER)}</span>
              <span className="font-medium text-gray-900 dark:text-gray-100">
                {formatMultiplier(distanceMultiplier)}
              </span>
              <span>{formatMultiplier(MAX_DISTANCE_MULTIPLIER)}</span>
            </div>
          </div>

          {/* Hint */}
          <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">
            Adjust how far apart parts spread in exploded view.
          </p>
        </div>
      )}
    </div>
  );
}

export default ExplodeToolbar;
