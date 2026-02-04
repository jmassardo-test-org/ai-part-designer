/**
 * Tests for useDesignHistory hook
 */

import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useDesignHistory, DesignState } from '../useDesignHistory';

// Helper to create a design state
function createState(id: string, data: unknown = {}): DesignState {
  return {
    id,
    timestamp: new Date(),
    description: `State ${id}`,
    data,
  };
}

describe('useDesignHistory', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('initial state', () => {
    it('starts with empty history', () => {
      const { result } = renderHook(() => useDesignHistory());

      expect(result.current.history).toHaveLength(0);
      expect(result.current.historyIndex).toBe(-1);
      expect(result.current.currentState).toBeNull();
    });

    it('starts with undo/redo disabled', () => {
      const { result } = renderHook(() => useDesignHistory());

      expect(result.current.canUndo).toBe(false);
      expect(result.current.canRedo).toBe(false);
    });
  });

  describe('pushState', () => {
    it('adds state to history', () => {
      const { result } = renderHook(() => useDesignHistory());
      const state = createState('1');

      act(() => {
        result.current.pushState(state, 'Add first state');
      });

      expect(result.current.history).toHaveLength(1);
      expect(result.current.historyIndex).toBe(0);
      expect(result.current.currentState).toBe(state);
    });

    it('adds multiple states sequentially', () => {
      const { result } = renderHook(() => useDesignHistory());
      const state1 = createState('1');
      const state2 = createState('2');
      const state3 = createState('3');

      act(() => {
        result.current.pushState(state1, 'First');
        result.current.pushState(state2, 'Second');
        result.current.pushState(state3, 'Third');
      });

      expect(result.current.history).toHaveLength(3);
      expect(result.current.historyIndex).toBe(2);
      expect(result.current.currentState).toBe(state3);
    });

    it('calls onStateChange callback', () => {
      const onStateChange = vi.fn();
      const { result } = renderHook(() =>
        useDesignHistory({ onStateChange })
      );
      const state = createState('1');

      act(() => {
        result.current.pushState(state, 'Add state');
      });

      expect(onStateChange).toHaveBeenCalledWith(state);
    });

    it('respects maxHistory limit', () => {
      const { result } = renderHook(() => useDesignHistory({ maxHistory: 3 }));

      act(() => {
        for (let i = 1; i <= 5; i++) {
          result.current.pushState(createState(`${i}`), `State ${i}`);
        }
      });

      expect(result.current.history).toHaveLength(3);
      // Should have kept the last 3 states
      expect(result.current.history[0].state.id).toBe('3');
      expect(result.current.history[2].state.id).toBe('5');
    });

    it('clears redo stack when pushing new state after undo', () => {
      const { result } = renderHook(() => useDesignHistory());
      const state1 = createState('1');
      const state2 = createState('2');
      const state3 = createState('3');
      const state4 = createState('4');

      act(() => {
        result.current.pushState(state1, 'First');
        result.current.pushState(state2, 'Second');
        result.current.pushState(state3, 'Third');
      });

      // Undo to state2
      act(() => {
        result.current.undo();
      });

      // Push new state - should clear state3 from future
      act(() => {
        result.current.pushState(state4, 'Fourth');
      });

      expect(result.current.history).toHaveLength(3);
      expect(result.current.history[2].state).toBe(state4);
      expect(result.current.canRedo).toBe(false);
    });
  });

  describe('undo', () => {
    it('returns null when nothing to undo', () => {
      const { result } = renderHook(() => useDesignHistory());

      let returnValue;
      act(() => {
        returnValue = result.current.undo();
      });

      expect(returnValue).toBeNull();
    });

    it('goes back to previous state', () => {
      const { result } = renderHook(() => useDesignHistory());
      const state1 = createState('1');
      const state2 = createState('2');

      act(() => {
        result.current.pushState(state1, 'First');
        result.current.pushState(state2, 'Second');
      });

      let returnValue;
      act(() => {
        returnValue = result.current.undo();
      });

      expect(returnValue).toBe(state1);
      expect(result.current.currentState).toBe(state1);
      expect(result.current.historyIndex).toBe(0);
    });

    it('enables redo after undo', () => {
      const { result } = renderHook(() => useDesignHistory());

      act(() => {
        result.current.pushState(createState('1'), 'First');
        result.current.pushState(createState('2'), 'Second');
      });

      expect(result.current.canRedo).toBe(false);

      act(() => {
        result.current.undo();
      });

      expect(result.current.canRedo).toBe(true);
    });

    it('disables undo at first state', () => {
      const { result } = renderHook(() => useDesignHistory());

      act(() => {
        result.current.pushState(createState('1'), 'First');
        result.current.pushState(createState('2'), 'Second');
      });

      act(() => {
        result.current.undo();
      });

      expect(result.current.canUndo).toBe(false);
    });

    it('calls onStateChange callback', () => {
      const onStateChange = vi.fn();
      const { result } = renderHook(() =>
        useDesignHistory({ onStateChange })
      );
      const state1 = createState('1');

      act(() => {
        result.current.pushState(state1, 'First');
        result.current.pushState(createState('2'), 'Second');
      });

      onStateChange.mockClear();

      act(() => {
        result.current.undo();
      });

      expect(onStateChange).toHaveBeenCalledWith(state1);
    });
  });

  describe('redo', () => {
    it('returns null when nothing to redo', () => {
      const { result } = renderHook(() => useDesignHistory());

      act(() => {
        result.current.pushState(createState('1'), 'First');
      });

      let returnValue;
      act(() => {
        returnValue = result.current.redo();
      });

      expect(returnValue).toBeNull();
    });

    it('goes forward to next state', () => {
      const { result } = renderHook(() => useDesignHistory());
      const state1 = createState('1');
      const state2 = createState('2');

      act(() => {
        result.current.pushState(state1, 'First');
        result.current.pushState(state2, 'Second');
      });
      
      // First undo
      act(() => {
        result.current.undo();
      });
      
      expect(result.current.canRedo).toBe(true);

      // Then redo
      let returnValue;
      act(() => {
        returnValue = result.current.redo();
      });

      expect(returnValue).toBe(state2);
      expect(result.current.currentState).toBe(state2);
    });

    it('calls onStateChange callback', () => {
      const onStateChange = vi.fn();
      const { result } = renderHook(() =>
        useDesignHistory({ onStateChange })
      );
      const state2 = createState('2');

      act(() => {
        result.current.pushState(createState('1'), 'First');
        result.current.pushState(state2, 'Second');
      });
      
      act(() => {
        result.current.undo();
      });

      onStateChange.mockClear();

      act(() => {
        result.current.redo();
      });

      expect(onStateChange).toHaveBeenCalledWith(state2);
    });
  });

  describe('goToIndex', () => {
    it('returns null for invalid index', () => {
      const { result } = renderHook(() => useDesignHistory());

      let returnValue;
      act(() => {
        returnValue = result.current.goToIndex(5);
      });

      expect(returnValue).toBeNull();
    });

    it('jumps to specific history index', () => {
      const { result } = renderHook(() => useDesignHistory());
      const state1 = createState('1');
      const state2 = createState('2');
      const state3 = createState('3');

      act(() => {
        result.current.pushState(state1, 'First');
        result.current.pushState(state2, 'Second');
        result.current.pushState(state3, 'Third');
      });

      let returnValue;
      act(() => {
        returnValue = result.current.goToIndex(0);
      });

      expect(returnValue).toBe(state1);
      expect(result.current.currentState).toBe(state1);
      expect(result.current.historyIndex).toBe(0);
    });
  });

  describe('clear', () => {
    it('resets all history', () => {
      const { result } = renderHook(() => useDesignHistory());

      act(() => {
        result.current.pushState(createState('1'), 'First');
        result.current.pushState(createState('2'), 'Second');
        result.current.clear();
      });

      expect(result.current.history).toHaveLength(0);
      expect(result.current.historyIndex).toBe(-1);
      expect(result.current.currentState).toBeNull();
    });

    it('calls onStateChange with null', () => {
      const onStateChange = vi.fn();
      const { result } = renderHook(() =>
        useDesignHistory({ onStateChange })
      );

      act(() => {
        result.current.pushState(createState('1'), 'First');
      });

      onStateChange.mockClear();

      act(() => {
        result.current.clear();
      });

      expect(onStateChange).toHaveBeenCalledWith(null);
    });
  });

  describe('computed values', () => {
    it('provides undoDescription for current state', () => {
      const { result } = renderHook(() => useDesignHistory());

      act(() => {
        result.current.pushState(createState('1'), 'Add widget');
        result.current.pushState(createState('2'), 'Resize box');
      });

      expect(result.current.undoDescription).toBe('Resize box');
    });

    it('provides redoDescription for next state', () => {
      const { result } = renderHook(() => useDesignHistory());

      act(() => {
        result.current.pushState(createState('1'), 'Add widget');
        result.current.pushState(createState('2'), 'Resize box');
      });
      
      act(() => {
        result.current.undo();
      });

      expect(result.current.redoDescription).toBe('Resize box');
    });

    it('returns null descriptions when not applicable', () => {
      const { result } = renderHook(() => useDesignHistory());

      expect(result.current.undoDescription).toBeNull();
      expect(result.current.redoDescription).toBeNull();

      act(() => {
        result.current.pushState(createState('1'), 'First');
      });

      expect(result.current.undoDescription).toBeNull();
      expect(result.current.redoDescription).toBeNull();
    });
  });
});
