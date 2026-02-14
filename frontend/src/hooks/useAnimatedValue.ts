/**
 * useAnimatedValue Hook
 *
 * Generic hook for animating numeric values with easing functions.
 * Supports smooth animations via requestAnimationFrame, respects
 * prefers-reduced-motion, and allows mid-animation target changes.
 */

import { useState, useRef, useCallback, useEffect } from 'react';

// =============================================================================
// Types
// =============================================================================

/** Options for configuring the useAnimatedValue hook. */
export interface UseAnimatedValueOptions {
  /** Starting value for the animation. */
  initialValue: number;
  /** Default animation duration in milliseconds. */
  duration: number;
  /** Easing function: maps progress (0-1) to eased value (0-1). */
  easing?: (t: number) => number;
}

/** Return value of the useAnimatedValue hook. */
export interface UseAnimatedValueReturn {
  /** Current animated value. */
  value: number;
  /** Whether an animation is currently in progress. */
  isAnimating: boolean;
  /** Animate to a target value over specified duration. */
  animateTo: (target: number, options?: { duration?: number }) => void;
  /** Set value immediately without animation. */
  setImmediate: (value: number) => void;
}

// =============================================================================
// Easing Functions
// =============================================================================

/**
 * Ease-out cubic easing function.
 * Starts fast and decelerates toward the end.
 *
 * @param t - Progress value from 0 to 1.
 * @returns Eased value from 0 to 1.
 */
export function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}

/**
 * Linear easing function (no easing).
 *
 * @param t - Progress value from 0 to 1.
 * @returns Same value (linear progress).
 */
export function linear(t: number): number {
  return t;
}

// =============================================================================
// Reduced Motion Detection
// =============================================================================

/**
 * Check if the user prefers reduced motion.
 *
 * @returns True if prefers-reduced-motion is set to 'reduce'.
 */
function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined') return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook for animating numeric values with easing.
 *
 * @param options - Configuration options for the animated value.
 * @returns Object containing current value, animation state, and control functions.
 *
 * @example
 * ```tsx
 * const { value, isAnimating, animateTo } = useAnimatedValue({
 *   initialValue: 0,
 *   duration: 500,
 *   easing: easeOutCubic,
 * });
 *
 * // Animate to 1 over 500ms
 * animateTo(1);
 *
 * // Use value in render (0 → 1 animated)
 * <mesh scale={[1 + value, 1 + value, 1 + value]} />
 * ```
 */
export function useAnimatedValue({
  initialValue,
  duration,
  easing = easeOutCubic,
}: UseAnimatedValueOptions): UseAnimatedValueReturn {
  const [value, setValue] = useState(initialValue);
  const [isAnimating, setIsAnimating] = useState(false);

  // Animation state refs (persist across renders without causing re-renders)
  const animationRef = useRef<number | null>(null);
  const startTimeRef = useRef<number>(0);
  const startValueRef = useRef<number>(initialValue);
  const targetValueRef = useRef<number>(initialValue);
  const durationRef = useRef<number>(duration);
  const easingRef = useRef<(t: number) => number>(easing);

  // Keep easing ref updated
  useEffect(() => {
    easingRef.current = easing;
  }, [easing]);

  // Cancel any running animation
  const cancelAnimation = useCallback(() => {
    if (animationRef.current !== null) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }
  }, []);

  // Animation frame callback
  const animate = useCallback((timestamp: number) => {
    const elapsed = timestamp - startTimeRef.current;
    const progress = Math.min(elapsed / durationRef.current, 1);
    const easedProgress = easingRef.current(progress);

    const currentValue =
      startValueRef.current +
      (targetValueRef.current - startValueRef.current) * easedProgress;

    setValue(currentValue);

    if (progress < 1) {
      animationRef.current = requestAnimationFrame(animate);
    } else {
      // Animation complete
      setValue(targetValueRef.current);
      setIsAnimating(false);
      animationRef.current = null;
    }
  }, []);

  // Animate to a target value
  const animateTo = useCallback(
    (target: number, options?: { duration?: number }) => {
      // Cancel any existing animation
      cancelAnimation();

      // If reduced motion is preferred, set immediately
      if (prefersReducedMotion()) {
        setValue(target);
        setIsAnimating(false);
        targetValueRef.current = target;
        return;
      }

      // If already at target, no-op
      if (target === value && !isAnimating) {
        return;
      }

      // Set up animation
      startValueRef.current = value;
      targetValueRef.current = target;
      durationRef.current = options?.duration ?? duration;
      startTimeRef.current = performance.now();
      setIsAnimating(true);

      // Start animation loop
      animationRef.current = requestAnimationFrame(animate);
    },
    [value, isAnimating, duration, cancelAnimation, animate]
  );

  // Set value immediately (no animation)
  const setImmediate = useCallback(
    (newValue: number) => {
      cancelAnimation();
      setValue(newValue);
      setIsAnimating(false);
      startValueRef.current = newValue;
      targetValueRef.current = newValue;
    },
    [cancelAnimation]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cancelAnimation();
    };
  }, [cancelAnimation]);

  return {
    value,
    isAnimating,
    animateTo,
    setImmediate,
  };
}

export default useAnimatedValue;
