/**
 * useAnimatedValue Hook Tests
 *
 * Tests for the animated value hook including animation timing,
 * easing functions, reduced motion support, and mid-animation changes.
 */

import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useAnimatedValue, easeOutCubic, linear } from './useAnimatedValue';

// =============================================================================
// Helpers
// =============================================================================

/**
 * Mock matchMedia for testing prefers-reduced-motion.
 */
function mockMatchMedia(matches: boolean): void {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: query === '(prefers-reduced-motion: reduce)' ? matches : false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
}

// =============================================================================
// Tests
// =============================================================================

describe('useAnimatedValue', () => {
  let rafCallbacks: Array<(timestamp: number) => void> = [];
  let rafId = 0;
  let currentTime = 0;

  beforeEach(() => {
    rafCallbacks = [];
    rafId = 0;
    currentTime = 0;
    mockMatchMedia(false); // Default: reduced motion disabled

    // Mock requestAnimationFrame
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation(
      (callback: FrameRequestCallback): number => {
        rafId++;
        rafCallbacks.push(callback);
        return rafId;
      }
    );

    // Mock cancelAnimationFrame
    vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {
      rafCallbacks = [];
    });

    // Mock performance.now
    vi.spyOn(performance, 'now').mockImplementation(() => currentTime);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  /**
   * Advance time and trigger RAF callbacks.
   */
  function advanceTime(ms: number): void {
    currentTime += ms;
    const callbacks = [...rafCallbacks];
    rafCallbacks = [];
    callbacks.forEach((cb) => cb(currentTime));
  }

  // ---------------------------------------------------------------------------
  // Initial State
  // ---------------------------------------------------------------------------

  describe('initial state', () => {
    it('returns initial value', () => {
      const { result } = renderHook(() =>
        useAnimatedValue({ initialValue: 0, duration: 500 })
      );

      expect(result.current.value).toBe(0);
      expect(result.current.isAnimating).toBe(false);
    });

    it('accepts custom initial value', () => {
      const { result } = renderHook(() =>
        useAnimatedValue({ initialValue: 0.5, duration: 500 })
      );

      expect(result.current.value).toBe(0.5);
    });
  });

  // ---------------------------------------------------------------------------
  // animateTo
  // ---------------------------------------------------------------------------

  describe('animateTo', () => {
    it('animates from 0 to 1 over specified duration', () => {
      const { result } = renderHook(() =>
        useAnimatedValue({ initialValue: 0, duration: 500 })
      );

      act(() => {
        result.current.animateTo(1);
      });

      expect(result.current.isAnimating).toBe(true);

      // Halfway through animation
      act(() => {
        advanceTime(250);
      });

      // Value should be between 0 and 1 (eased)
      expect(result.current.value).toBeGreaterThan(0);
      expect(result.current.value).toBeLessThan(1);
      expect(result.current.isAnimating).toBe(true);

      // Complete animation
      act(() => {
        advanceTime(250);
      });

      expect(result.current.value).toBe(1);
      expect(result.current.isAnimating).toBe(false);
    });

    it('accepts custom duration via options', () => {
      const { result } = renderHook(() =>
        useAnimatedValue({ initialValue: 0, duration: 500 })
      );

      act(() => {
        result.current.animateTo(1, { duration: 200 });
      });

      // Should complete after 200ms, not 500ms
      act(() => {
        advanceTime(200);
      });

      expect(result.current.value).toBe(1);
      expect(result.current.isAnimating).toBe(false);
    });

    it('mid-animation target change works', () => {
      const { result } = renderHook(() =>
        useAnimatedValue({ initialValue: 0, duration: 500 })
      );

      // Start animating to 1
      act(() => {
        result.current.animateTo(1);
      });

      // Advance halfway
      act(() => {
        advanceTime(250);
      });

      const valueAtMidpoint = result.current.value;
      expect(valueAtMidpoint).toBeGreaterThan(0);

      // Change target to 0 (reverse)
      act(() => {
        result.current.animateTo(0);
      });

      // Continue animation
      act(() => {
        advanceTime(250);
      });

      // Should be animating back toward 0
      expect(result.current.value).toBeLessThan(valueAtMidpoint);

      // Complete animation
      act(() => {
        advanceTime(250);
      });

      expect(result.current.value).toBe(0);
      expect(result.current.isAnimating).toBe(false);
    });

    it('no-ops when already at target and not animating', () => {
      const { result } = renderHook(() =>
        useAnimatedValue({ initialValue: 1, duration: 500 })
      );

      act(() => {
        result.current.animateTo(1);
      });

      // Should not start animation
      expect(result.current.isAnimating).toBe(false);
      expect(window.requestAnimationFrame).not.toHaveBeenCalled();
    });
  });

  // ---------------------------------------------------------------------------
  // setImmediate
  // ---------------------------------------------------------------------------

  describe('setImmediate', () => {
    it('updates value instantly without animation', () => {
      const { result } = renderHook(() =>
        useAnimatedValue({ initialValue: 0, duration: 500 })
      );

      act(() => {
        result.current.setImmediate(1);
      });

      expect(result.current.value).toBe(1);
      expect(result.current.isAnimating).toBe(false);
    });

    it('cancels running animation', () => {
      const { result } = renderHook(() =>
        useAnimatedValue({ initialValue: 0, duration: 500 })
      );

      // Start animation
      act(() => {
        result.current.animateTo(1);
      });

      expect(result.current.isAnimating).toBe(true);

      // Set immediate value
      act(() => {
        result.current.setImmediate(0.5);
      });

      expect(result.current.value).toBe(0.5);
      expect(result.current.isAnimating).toBe(false);
      expect(window.cancelAnimationFrame).toHaveBeenCalled();
    });
  });

  // ---------------------------------------------------------------------------
  // Easing Functions
  // ---------------------------------------------------------------------------

  describe('easing functions', () => {
    it('calls easing function correctly', () => {
      const mockEasing = vi.fn((t: number) => t);

      const { result } = renderHook(() =>
        useAnimatedValue({ initialValue: 0, duration: 500, easing: mockEasing })
      );

      act(() => {
        result.current.animateTo(1);
      });

      // Trigger animation frame
      act(() => {
        advanceTime(250);
      });

      expect(mockEasing).toHaveBeenCalled();
      // Progress at 250ms out of 500ms = 0.5
      expect(mockEasing).toHaveBeenCalledWith(0.5);
    });

    it('uses default easeOutCubic easing', () => {
      const { result } = renderHook(() =>
        useAnimatedValue({ initialValue: 0, duration: 500 })
      );

      act(() => {
        result.current.animateTo(1);
      });

      // At 50% time with easeOutCubic, value should be > 0.5 (decelerating)
      act(() => {
        advanceTime(250);
      });

      // easeOutCubic(0.5) = 1 - (0.5)^3 = 1 - 0.125 = 0.875
      expect(result.current.value).toBeCloseTo(0.875, 2);
    });
  });

  // ---------------------------------------------------------------------------
  // Prefers Reduced Motion
  // ---------------------------------------------------------------------------

  describe('prefers-reduced-motion', () => {
    it('respects prefers-reduced-motion by setting value immediately', () => {
      mockMatchMedia(true); // Enable reduced motion

      const { result } = renderHook(() =>
        useAnimatedValue({ initialValue: 0, duration: 500 })
      );

      act(() => {
        result.current.animateTo(1);
      });

      // Should set immediately, no animation
      expect(result.current.value).toBe(1);
      expect(result.current.isAnimating).toBe(false);
    });
  });

  // ---------------------------------------------------------------------------
  // Cleanup
  // ---------------------------------------------------------------------------

  describe('cleanup', () => {
    it('cancels animation on unmount', () => {
      const { result, unmount } = renderHook(() =>
        useAnimatedValue({ initialValue: 0, duration: 500 })
      );

      act(() => {
        result.current.animateTo(1);
      });

      unmount();

      expect(window.cancelAnimationFrame).toHaveBeenCalled();
    });
  });
});

// =============================================================================
// Easing Function Unit Tests
// =============================================================================

describe('easeOutCubic', () => {
  it('returns 0 for input 0', () => {
    expect(easeOutCubic(0)).toBe(0);
  });

  it('returns 1 for input 1', () => {
    expect(easeOutCubic(1)).toBe(1);
  });

  it('returns value > progress for middle values (decelerating)', () => {
    expect(easeOutCubic(0.5)).toBe(0.875);
    expect(easeOutCubic(0.25)).toBeCloseTo(0.578, 2);
    expect(easeOutCubic(0.75)).toBeCloseTo(0.984, 2);
  });
});

describe('linear', () => {
  it('returns same value as input', () => {
    expect(linear(0)).toBe(0);
    expect(linear(0.5)).toBe(0.5);
    expect(linear(1)).toBe(1);
  });
});
