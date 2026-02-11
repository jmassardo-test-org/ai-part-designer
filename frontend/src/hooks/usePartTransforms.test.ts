/**
 * usePartTransforms Hook Tests
 */

import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { PartTransform } from '../components/viewer/PartTransformControls';
import { usePartTransforms } from './usePartTransforms';

describe('usePartTransforms', () => {
  const mockTransform: PartTransform = {
    position: { x: 10, y: 20, z: 30 },
    rotation: { rx: 0, ry: 45, rz: 0 },
    scale: { sx: 1, sy: 1, sz: 1 },
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('initializes with empty transforms by default', () => {
    const { result } = renderHook(() => usePartTransforms());
    expect(result.current.transforms).toEqual({});
  });

  it('initializes with provided transforms', () => {
    const initialTransforms = {
      'part-1': mockTransform,
    };
    const { result } = renderHook(() =>
      usePartTransforms({ initialTransforms })
    );
    expect(result.current.transforms).toEqual(initialTransforms);
  });

  it('updates transform for a part', () => {
    const { result } = renderHook(() => usePartTransforms());

    act(() => {
      result.current.updateTransform('part-1', mockTransform);
    });

    expect(result.current.transforms['part-1']).toEqual(mockTransform);
  });

  it('updates multiple part transforms', () => {
    const { result } = renderHook(() => usePartTransforms());
    const transform2: PartTransform = {
      position: { x: 50, y: 60, z: 70 },
      rotation: { rx: 90, ry: 0, rz: 0 },
      scale: { sx: 2, sy: 2, sz: 2 },
    };

    act(() => {
      result.current.updateTransform('part-1', mockTransform);
      result.current.updateTransform('part-2', transform2);
    });

    expect(result.current.transforms['part-1']).toEqual(mockTransform);
    expect(result.current.transforms['part-2']).toEqual(transform2);
  });

  it('calls onTransformUpdate callback when transform changes', () => {
    const onTransformUpdate = vi.fn();
    const { result } = renderHook(() =>
      usePartTransforms({ onTransformUpdate })
    );

    act(() => {
      result.current.updateTransform('part-1', mockTransform);
    });

    expect(onTransformUpdate).toHaveBeenCalledWith('part-1', mockTransform);
  });

  it('supports undo after transform update', () => {
    const { result } = renderHook(() => usePartTransforms());

    act(() => {
      result.current.updateTransform('part-1', mockTransform);
    });

    expect(result.current.canUndo).toBe(true);
    expect(result.current.transforms['part-1']).toEqual(mockTransform);

    act(() => {
      result.current.undo();
    });

    expect(result.current.transforms).toEqual({});
  });

  it('supports redo after undo', () => {
    const { result } = renderHook(() => usePartTransforms());

    act(() => {
      result.current.updateTransform('part-1', mockTransform);
    });

    act(() => {
      result.current.undo();
    });

    expect(result.current.canRedo).toBe(true);

    act(() => {
      result.current.redo();
    });

    expect(result.current.transforms['part-1']).toEqual(mockTransform);
  });

  it('cannot undo when no history', () => {
    const { result } = renderHook(() => usePartTransforms());
    expect(result.current.canUndo).toBe(false);
  });

  it('cannot redo when at latest state', () => {
    const { result } = renderHook(() => usePartTransforms());

    act(() => {
      result.current.updateTransform('part-1', mockTransform);
    });

    expect(result.current.canRedo).toBe(false);
  });

  it('resets single part transform', () => {
    const { result } = renderHook(() => usePartTransforms());

    act(() => {
      result.current.updateTransform('part-1', mockTransform);
      result.current.updateTransform('part-2', mockTransform);
    });

    expect(Object.keys(result.current.transforms)).toHaveLength(2);

    act(() => {
      result.current.resetTransform('part-1');
    });

    expect(result.current.transforms['part-1']).toBeUndefined();
    expect(result.current.transforms['part-2']).toEqual(mockTransform);
  });

  it('resets all transforms', () => {
    const { result } = renderHook(() => usePartTransforms());

    act(() => {
      result.current.updateTransform('part-1', mockTransform);
      result.current.updateTransform('part-2', mockTransform);
    });

    expect(Object.keys(result.current.transforms)).toHaveLength(2);

    act(() => {
      result.current.resetAllTransforms();
    });

    expect(result.current.transforms).toEqual({});
  });

  it('clears history', () => {
    const { result } = renderHook(() => usePartTransforms());

    act(() => {
      result.current.updateTransform('part-1', mockTransform);
    });

    expect(result.current.canUndo).toBe(true);

    act(() => {
      result.current.clearHistory();
    });

    expect(result.current.canUndo).toBe(false);
  });

  it('provides undo/redo descriptions', () => {
    const { result } = renderHook(() => usePartTransforms());

    act(() => {
      result.current.updateTransform('part-1', mockTransform, 'Move part-1');
    });

    expect(result.current.undoDescription).toBe('Move part-1');

    act(() => {
      result.current.undo();
    });

    expect(result.current.redoDescription).toBe('Move part-1');
  });

  it('respects maxHistory option', () => {
    const { result } = renderHook(() =>
      usePartTransforms({ maxHistory: 2 })
    );

    act(() => {
      result.current.updateTransform('part-1', mockTransform, 'Change 1');
      result.current.updateTransform('part-2', mockTransform, 'Change 2');
      result.current.updateTransform('part-3', mockTransform, 'Change 3');
    });

    // After 3 changes with maxHistory=2, oldest should be trimmed
    // We can still undo from current state
    expect(result.current.canUndo).toBe(true);
  });

  it('handles rapid sequential updates', () => {
    const { result } = renderHook(() => usePartTransforms());

    act(() => {
      for (let i = 0; i < 10; i++) {
        result.current.updateTransform('part-1', {
          ...mockTransform,
          position: { x: i, y: i, z: i },
        });
      }
    });

    expect(result.current.transforms['part-1'].position.x).toBe(9);
    expect(result.current.canUndo).toBe(true);
  });
});
