/**
 * useExplodedView Hook
 *
 * State machine for managing exploded view animation with configurable
 * expansion/collapse durations and distance multiplier.
 */

import { useState, useCallback, useMemo } from 'react';
import { useAnimatedValue, easeOutCubic } from './useAnimatedValue';

// =============================================================================
// Types
// =============================================================================

/** State machine states for exploded view. */
export type ExplodeState = 'collapsed' | 'exploding' | 'exploded' | 'collapsing';

/** Options for configuring the useExplodedView hook. */
export interface UseExplodedViewOptions {
  /** Duration for expand animation in milliseconds. Default: 500ms. */
  expandDuration?: number;
  /** Duration for collapse animation in milliseconds. Default: 400ms. */
  collapseDuration?: number;
  /** Initial distance multiplier. Default: 1.0. */
  initialDistanceMultiplier?: number;
}

/** Return value of the useExplodedView hook. */
export interface UseExplodedViewReturn {
  /** Current state of the explode state machine. */
  explodeState: ExplodeState;
  /** Animated explode factor from 0 (collapsed) to 1 (exploded). */
  explodeFactor: number;
  /** Distance multiplier for explosion (0.5 to 3.0). */
  distanceMultiplier: number;
  /** Whether an animation is currently in progress. */
  isAnimating: boolean;
  /** Toggle between exploded and collapsed states. */
  toggle: () => void;
  /** Set the distance multiplier (clamped to 0.5-3.0). */
  setDistanceMultiplier: (value: number) => void;
}

// =============================================================================
// Constants
// =============================================================================

/** Minimum distance multiplier value. */
export const MIN_DISTANCE_MULTIPLIER = 0.5;

/** Maximum distance multiplier value. */
export const MAX_DISTANCE_MULTIPLIER = 3.0;

/** Default expand animation duration in milliseconds. */
export const DEFAULT_EXPAND_DURATION = 500;

/** Default collapse animation duration in milliseconds. */
export const DEFAULT_COLLAPSE_DURATION = 400;

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook for managing exploded view state with smooth animations.
 *
 * Implements a state machine:
 * - collapsed → exploding → exploded
 * - exploded → collapsing → collapsed
 * - Can reverse mid-animation (exploding ↔ collapsing)
 *
 * @param options - Configuration options for the exploded view.
 * @returns Object containing state, animated values, and control functions.
 *
 * @example
 * ```tsx
 * const {
 *   explodeState,
 *   explodeFactor,
 *   distanceMultiplier,
 *   toggle,
 *   setDistanceMultiplier,
 * } = useExplodedView({ expandDuration: 500, collapseDuration: 400 });
 *
 * // In render: use explodeFactor * distanceMultiplier for explosion distance
 * const explodeDistance = explodeFactor * distanceMultiplier * 50;
 * ```
 */
export function useExplodedView({
  expandDuration = DEFAULT_EXPAND_DURATION,
  collapseDuration = DEFAULT_COLLAPSE_DURATION,
  initialDistanceMultiplier = 1.0,
}: UseExplodedViewOptions = {}): UseExplodedViewReturn {
  // Distance multiplier state (user setting, not animated)
  const [distanceMultiplier, setDistanceMultiplierState] = useState(
    clampMultiplier(initialDistanceMultiplier)
  );

  // Explicit state tracking for the state machine
  const [explodeState, setExplodeState] = useState<ExplodeState>('collapsed');

  // Animated explode factor (0 = collapsed, 1 = exploded)
  const animated = useAnimatedValue({
    initialValue: 0,
    duration: expandDuration,
    easing: easeOutCubic,
  });

  // Derive isAnimating from explicit state
  const isAnimating = useMemo(
    () => explodeState === 'exploding' || explodeState === 'collapsing',
    [explodeState]
  );

  // Update state when animation completes
  // We track this by checking if animated.isAnimating changed to false
  // and updating our state accordingly
  const handleAnimationComplete = useCallback(
    (targetState: 'exploded' | 'collapsed') => {
      setExplodeState(targetState);
    },
    []
  );

  // Toggle between exploded and collapsed states
  const toggle = useCallback(() => {
    switch (explodeState) {
      case 'collapsed':
        // Start exploding
        setExplodeState('exploding');
        animated.animateTo(1, { duration: expandDuration });
        // Monitor for completion
        monitorAnimation(animated, 1, () => handleAnimationComplete('exploded'));
        break;

      case 'exploded':
        // Start collapsing
        setExplodeState('collapsing');
        animated.animateTo(0, { duration: collapseDuration });
        // Monitor for completion
        monitorAnimation(animated, 0, () => handleAnimationComplete('collapsed'));
        break;

      case 'exploding':
        // Reverse to collapsing (mid-animation)
        setExplodeState('collapsing');
        animated.animateTo(0, { duration: collapseDuration });
        monitorAnimation(animated, 0, () => handleAnimationComplete('collapsed'));
        break;

      case 'collapsing':
        // Reverse to exploding (mid-animation)
        setExplodeState('exploding');
        animated.animateTo(1, { duration: expandDuration });
        monitorAnimation(animated, 1, () => handleAnimationComplete('exploded'));
        break;
    }
  }, [explodeState, animated, expandDuration, collapseDuration, handleAnimationComplete]);

  // Set distance multiplier with clamping
  const setDistanceMultiplier = useCallback((value: number) => {
    setDistanceMultiplierState(clampMultiplier(value));
  }, []);

  return {
    explodeState,
    explodeFactor: animated.value,
    distanceMultiplier,
    isAnimating,
    toggle,
    setDistanceMultiplier,
  };
}

// =============================================================================
// Helpers
// =============================================================================

/**
 * Clamp distance multiplier to valid range.
 *
 * @param value - Raw multiplier value.
 * @returns Clamped value between MIN and MAX.
 */
function clampMultiplier(value: number): number {
  return Math.max(MIN_DISTANCE_MULTIPLIER, Math.min(MAX_DISTANCE_MULTIPLIER, value));
}

/**
 * Monitor animated value and call callback when target is reached.
 * Uses requestAnimationFrame polling since we can't directly observe completion.
 *
 * @param animated - The animated value return object.
 * @param target - Target value to watch for.
 * @param onComplete - Callback when animation completes.
 */
function monitorAnimation(
  animated: { value: number; isAnimating: boolean },
  target: number,
  onComplete: () => void
): void {
  const checkComplete = () => {
    // Check if animation completed (value reached target and not animating)
    if (Math.abs(animated.value - target) < 0.001 && !animated.isAnimating) {
      onComplete();
      return;
    }
    // If still animating, check again next frame
    if (animated.isAnimating) {
      requestAnimationFrame(checkComplete);
    }
  };
  // Start checking after a small delay to allow animation to start
  requestAnimationFrame(checkComplete);
}

export default useExplodedView;
