/**
 * useComponentVisibility Hook Tests
 *
 * Comprehensive tests for hide/show/isolate/showAll behaviour
 * and sessionStorage persistence.
 */

import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useComponentVisibility } from './useComponentVisibility';

// =============================================================================
// Helpers
// =============================================================================

const COMPONENT_IDS = ['comp-1', 'comp-2', 'comp-3'];
const ASSEMBLY_ID = 'asm-test-123';

function storageKey(id: string): string {
  return `assembly-visibility:${id}`;
}

// =============================================================================
// Tests
// =============================================================================

describe('useComponentVisibility', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  afterEach(() => {
    sessionStorage.clear();
  });

  // ---------------------------------------------------------------------------
  // Initial state
  // ---------------------------------------------------------------------------

  describe('initial state', () => {
    it('starts with no hidden components', () => {
      const { result } = renderHook(() =>
        useComponentVisibility({ componentIds: COMPONENT_IDS }),
      );

      expect(result.current.hiddenComponents.size).toBe(0);
      expect(result.current.hiddenCount).toBe(0);
    });

    it('starts with isolate mode inactive', () => {
      const { result } = renderHook(() =>
        useComponentVisibility({ componentIds: COMPONENT_IDS }),
      );

      expect(result.current.isolateState.isActive).toBe(false);
      expect(result.current.isolateState.targetId).toBeNull();
    });

    it('uses externalHiddenComponents when provided', () => {
      const external = new Set(['comp-1']);
      const { result } = renderHook(() =>
        useComponentVisibility({
          componentIds: COMPONENT_IDS,
          externalHiddenComponents: external,
        }),
      );

      expect(result.current.hiddenComponents).toBe(external);
      expect(result.current.hiddenCount).toBe(1);
    });
  });

  // ---------------------------------------------------------------------------
  // toggleVisibility
  // ---------------------------------------------------------------------------

  describe('toggleVisibility', () => {
    it('hides a visible component', () => {
      const { result } = renderHook(() =>
        useComponentVisibility({ componentIds: COMPONENT_IDS }),
      );

      act(() => result.current.toggleVisibility('comp-1'));

      expect(result.current.isHidden('comp-1')).toBe(true);
      expect(result.current.hiddenCount).toBe(1);
    });

    it('shows a hidden component', () => {
      const { result } = renderHook(() =>
        useComponentVisibility({ componentIds: COMPONENT_IDS }),
      );

      act(() => result.current.toggleVisibility('comp-1'));
      expect(result.current.isHidden('comp-1')).toBe(true);

      act(() => result.current.toggleVisibility('comp-1'));
      expect(result.current.isHidden('comp-1')).toBe(false);
      expect(result.current.hiddenCount).toBe(0);
    });

    it('does nothing in external mode', () => {
      const external = new Set<string>();
      const { result } = renderHook(() =>
        useComponentVisibility({
          componentIds: COMPONENT_IDS,
          externalHiddenComponents: external,
        }),
      );

      act(() => result.current.toggleVisibility('comp-1'));
      expect(result.current.hiddenCount).toBe(0);
    });

    it('exits isolate mode when toggling while isolated', () => {
      const { result } = renderHook(() =>
        useComponentVisibility({ componentIds: COMPONENT_IDS }),
      );

      // Hide comp-1, then isolate comp-2
      act(() => result.current.hideComponent('comp-1'));
      act(() => result.current.isolateComponent('comp-2'));
      expect(result.current.isolateState.isActive).toBe(true);

      // Toggle comp-3 while isolated — should exit isolate
      act(() => result.current.toggleVisibility('comp-3'));

      expect(result.current.isolateState.isActive).toBe(false);
      // comp-1 was hidden pre-isolate, comp-3 gets toggled (was hidden in pre-isolate? no, it was visible → so now hidden)
      expect(result.current.isHidden('comp-1')).toBe(true);
      expect(result.current.isHidden('comp-3')).toBe(true);
      expect(result.current.isHidden('comp-2')).toBe(false);
    });
  });

  // ---------------------------------------------------------------------------
  // hideComponent / showComponent
  // ---------------------------------------------------------------------------

  describe('hideComponent', () => {
    it('hides a component', () => {
      const { result } = renderHook(() =>
        useComponentVisibility({ componentIds: COMPONENT_IDS }),
      );

      act(() => result.current.hideComponent('comp-2'));
      expect(result.current.isHidden('comp-2')).toBe(true);
    });

    it('is idempotent', () => {
      const { result } = renderHook(() =>
        useComponentVisibility({ componentIds: COMPONENT_IDS }),
      );

      act(() => result.current.hideComponent('comp-2'));
      act(() => result.current.hideComponent('comp-2'));
      expect(result.current.hiddenCount).toBe(1);
    });
  });

  describe('showComponent', () => {
    it('shows a hidden component', () => {
      const { result } = renderHook(() =>
        useComponentVisibility({ componentIds: COMPONENT_IDS }),
      );

      act(() => result.current.hideComponent('comp-2'));
      expect(result.current.isHidden('comp-2')).toBe(true);

      act(() => result.current.showComponent('comp-2'));
      expect(result.current.isHidden('comp-2')).toBe(false);
    });

    it('is idempotent on visible component', () => {
      const { result } = renderHook(() =>
        useComponentVisibility({ componentIds: COMPONENT_IDS }),
      );

      act(() => result.current.showComponent('comp-1'));
      expect(result.current.hiddenCount).toBe(0);
    });
  });

  // ---------------------------------------------------------------------------
  // isolateComponent
  // ---------------------------------------------------------------------------

  describe('isolateComponent', () => {
    it('isolates a component — all others hidden', () => {
      const { result } = renderHook(() =>
        useComponentVisibility({ componentIds: COMPONENT_IDS }),
      );

      act(() => result.current.isolateComponent('comp-2'));

      expect(result.current.isolateState.isActive).toBe(true);
      expect(result.current.isolateState.targetId).toBe('comp-2');
      expect(result.current.isHidden('comp-1')).toBe(true);
      expect(result.current.isHidden('comp-2')).toBe(false);
      expect(result.current.isHidden('comp-3')).toBe(true);
    });

    it('toggles off when same component is isolated again', () => {
      const { result } = renderHook(() =>
        useComponentVisibility({ componentIds: COMPONENT_IDS }),
      );

      act(() => result.current.isolateComponent('comp-2'));
      expect(result.current.isolateState.isActive).toBe(true);

      act(() => result.current.isolateComponent('comp-2'));
      expect(result.current.isolateState.isActive).toBe(false);
      // All should be visible (pre-isolate was empty)
      expect(result.current.hiddenCount).toBe(0);
    });

    it('restores pre-isolate state when exiting isolate', () => {
      const { result } = renderHook(() =>
        useComponentVisibility({ componentIds: COMPONENT_IDS }),
      );

      // Hide comp-1 first
      act(() => result.current.hideComponent('comp-1'));
      expect(result.current.isHidden('comp-1')).toBe(true);

      // Isolate comp-2
      act(() => result.current.isolateComponent('comp-2'));

      // Exit isolate by re-pressing
      act(() => result.current.isolateComponent('comp-2'));

      // comp-1 should still be hidden (restored from pre-isolate snapshot)
      expect(result.current.isHidden('comp-1')).toBe(true);
      expect(result.current.isHidden('comp-2')).toBe(false);
      expect(result.current.isHidden('comp-3')).toBe(false);
    });

    it('switches target when a different component is isolated', () => {
      const { result } = renderHook(() =>
        useComponentVisibility({ componentIds: COMPONENT_IDS }),
      );

      act(() => result.current.isolateComponent('comp-1'));
      expect(result.current.isolateState.targetId).toBe('comp-1');
      expect(result.current.isHidden('comp-2')).toBe(true);
      expect(result.current.isHidden('comp-3')).toBe(true);
      expect(result.current.isHidden('comp-1')).toBe(false);

      // Switch to comp-3
      act(() => result.current.isolateComponent('comp-3'));
      expect(result.current.isolateState.isActive).toBe(true);
      expect(result.current.isolateState.targetId).toBe('comp-3');
      expect(result.current.isHidden('comp-1')).toBe(true);
      expect(result.current.isHidden('comp-2')).toBe(true);
      expect(result.current.isHidden('comp-3')).toBe(false);
    });

    it('does nothing in external mode', () => {
      const external = new Set<string>();
      const { result } = renderHook(() =>
        useComponentVisibility({
          componentIds: COMPONENT_IDS,
          externalHiddenComponents: external,
        }),
      );

      act(() => result.current.isolateComponent('comp-1'));
      expect(result.current.isolateState.isActive).toBe(false);
    });
  });

  // ---------------------------------------------------------------------------
  // showAll
  // ---------------------------------------------------------------------------

  describe('showAll', () => {
    it('clears all hidden components', () => {
      const { result } = renderHook(() =>
        useComponentVisibility({ componentIds: COMPONENT_IDS }),
      );

      act(() => {
        result.current.hideComponent('comp-1');
        result.current.hideComponent('comp-2');
      });
      expect(result.current.hiddenCount).toBe(2);

      act(() => result.current.showAll());
      expect(result.current.hiddenCount).toBe(0);
    });

    it('exits isolate mode', () => {
      const { result } = renderHook(() =>
        useComponentVisibility({ componentIds: COMPONENT_IDS }),
      );

      act(() => result.current.isolateComponent('comp-1'));
      expect(result.current.isolateState.isActive).toBe(true);

      act(() => result.current.showAll());
      expect(result.current.isolateState.isActive).toBe(false);
      expect(result.current.hiddenCount).toBe(0);
    });

    it('does nothing in external mode', () => {
      const external = new Set(['comp-1']);
      const { result } = renderHook(() =>
        useComponentVisibility({
          componentIds: COMPONENT_IDS,
          externalHiddenComponents: external,
        }),
      );

      act(() => result.current.showAll());
      expect(result.current.hiddenCount).toBe(1);
    });
  });

  // ---------------------------------------------------------------------------
  // isHidden
  // ---------------------------------------------------------------------------

  describe('isHidden', () => {
    it('returns true for hidden components', () => {
      const { result } = renderHook(() =>
        useComponentVisibility({ componentIds: COMPONENT_IDS }),
      );

      act(() => result.current.hideComponent('comp-3'));
      expect(result.current.isHidden('comp-3')).toBe(true);
      expect(result.current.isHidden('comp-1')).toBe(false);
    });
  });

  // ---------------------------------------------------------------------------
  // hiddenCount
  // ---------------------------------------------------------------------------

  describe('hiddenCount', () => {
    it('reflects the number of hidden components', () => {
      const { result } = renderHook(() =>
        useComponentVisibility({ componentIds: COMPONENT_IDS }),
      );

      expect(result.current.hiddenCount).toBe(0);

      act(() => result.current.hideComponent('comp-1'));
      expect(result.current.hiddenCount).toBe(1);

      act(() => result.current.hideComponent('comp-2'));
      expect(result.current.hiddenCount).toBe(2);

      act(() => result.current.showComponent('comp-1'));
      expect(result.current.hiddenCount).toBe(1);
    });
  });

  // ---------------------------------------------------------------------------
  // sessionStorage persistence
  // ---------------------------------------------------------------------------

  describe('sessionStorage persistence', () => {
    it('persists hidden state to sessionStorage', () => {
      const { result } = renderHook(() =>
        useComponentVisibility({
          componentIds: COMPONENT_IDS,
          assemblyId: ASSEMBLY_ID,
        }),
      );

      act(() => result.current.hideComponent('comp-1'));

      const stored = JSON.parse(
        sessionStorage.getItem(storageKey(ASSEMBLY_ID)) || '{}',
      );
      expect(stored.version).toBe(1);
      expect(stored.hidden).toContain('comp-1');
    });

    it('restores hidden state from sessionStorage on mount', () => {
      // Pre-seed storage
      sessionStorage.setItem(
        storageKey(ASSEMBLY_ID),
        JSON.stringify({
          version: 1,
          hidden: ['comp-2'],
          isolate: { isActive: false, targetId: null },
        }),
      );

      const { result } = renderHook(() =>
        useComponentVisibility({
          componentIds: COMPONENT_IDS,
          assemblyId: ASSEMBLY_ID,
        }),
      );

      expect(result.current.isHidden('comp-2')).toBe(true);
      expect(result.current.hiddenCount).toBe(1);
    });

    it('filters out stale component IDs from storage', () => {
      sessionStorage.setItem(
        storageKey(ASSEMBLY_ID),
        JSON.stringify({
          version: 1,
          hidden: ['comp-2', 'stale-id'],
          isolate: { isActive: false, targetId: null },
        }),
      );

      const { result } = renderHook(() =>
        useComponentVisibility({
          componentIds: COMPONENT_IDS,
          assemblyId: ASSEMBLY_ID,
        }),
      );

      expect(result.current.isHidden('comp-2')).toBe(true);
      expect(result.current.hiddenCount).toBe(1);
    });

    it('ignores storage with wrong version', () => {
      sessionStorage.setItem(
        storageKey(ASSEMBLY_ID),
        JSON.stringify({
          version: 999,
          hidden: ['comp-1'],
          isolate: { isActive: false, targetId: null },
        }),
      );

      const { result } = renderHook(() =>
        useComponentVisibility({
          componentIds: COMPONENT_IDS,
          assemblyId: ASSEMBLY_ID,
        }),
      );

      expect(result.current.hiddenCount).toBe(0);
    });

    it('handles malformed JSON in sessionStorage gracefully', () => {
      sessionStorage.setItem(storageKey(ASSEMBLY_ID), 'not valid json');

      const { result } = renderHook(() =>
        useComponentVisibility({
          componentIds: COMPONENT_IDS,
          assemblyId: ASSEMBLY_ID,
        }),
      );

      expect(result.current.hiddenCount).toBe(0);
    });

    it('does not persist when assemblyId is not provided', () => {
      const { result } = renderHook(() =>
        useComponentVisibility({ componentIds: COMPONENT_IDS }),
      );

      act(() => result.current.hideComponent('comp-1'));

      expect(sessionStorage.getItem(storageKey(''))).toBeNull();
    });

    it('persists isolate state to sessionStorage', () => {
      const { result } = renderHook(() =>
        useComponentVisibility({
          componentIds: COMPONENT_IDS,
          assemblyId: ASSEMBLY_ID,
        }),
      );

      act(() => result.current.isolateComponent('comp-2'));

      const stored = JSON.parse(
        sessionStorage.getItem(storageKey(ASSEMBLY_ID)) || '{}',
      );
      expect(stored.isolate.isActive).toBe(true);
      expect(stored.isolate.targetId).toBe('comp-2');
    });

    it('restores isolate state from sessionStorage on mount', () => {
      sessionStorage.setItem(
        storageKey(ASSEMBLY_ID),
        JSON.stringify({
          version: 1,
          hidden: [],
          isolate: { isActive: true, targetId: 'comp-3' },
        }),
      );

      const { result } = renderHook(() =>
        useComponentVisibility({
          componentIds: COMPONENT_IDS,
          assemblyId: ASSEMBLY_ID,
        }),
      );

      expect(result.current.isolateState.isActive).toBe(true);
      expect(result.current.isolateState.targetId).toBe('comp-3');
      // Everything except comp-3 should be hidden
      expect(result.current.isHidden('comp-1')).toBe(true);
      expect(result.current.isHidden('comp-2')).toBe(true);
      expect(result.current.isHidden('comp-3')).toBe(false);
    });

    it('clears persisted state when showAll is called', () => {
      const { result } = renderHook(() =>
        useComponentVisibility({
          componentIds: COMPONENT_IDS,
          assemblyId: ASSEMBLY_ID,
        }),
      );

      act(() => result.current.hideComponent('comp-1'));
      act(() => result.current.showAll());

      const stored = JSON.parse(
        sessionStorage.getItem(storageKey(ASSEMBLY_ID)) || '{}',
      );
      expect(stored.hidden).toEqual([]);
      expect(stored.isolate.isActive).toBe(false);
    });
  });
});
