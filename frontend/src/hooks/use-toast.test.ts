import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useToast, toast, reducer } from './use-toast';

describe('use-toast', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('reducer', () => {
    it('handles ADD_TOAST action', () => {
      const initialState = { toasts: [] };
      const newToast = {
        id: '1',
        title: 'Test Toast',
        open: true,
        onOpenChange: vi.fn(),
      };

      const result = reducer(initialState, {
        type: 'ADD_TOAST',
        toast: newToast,
      });

      expect(result.toasts).toHaveLength(1);
      expect(result.toasts[0]).toEqual(newToast);
    });

    it('limits toasts to TOAST_LIMIT (5)', () => {
      let state = { toasts: [] };

      // Add 7 toasts
      for (let i = 0; i < 7; i++) {
        state = reducer(state, {
          type: 'ADD_TOAST',
          toast: {
            id: `${i}`,
            title: `Toast ${i}`,
            open: true,
            onOpenChange: vi.fn(),
          },
        });
      }

      expect(state.toasts).toHaveLength(5);
      // Most recent should be first
      expect(state.toasts[0].id).toBe('6');
    });

    it('handles UPDATE_TOAST action', () => {
      const initialState = {
        toasts: [
          { id: '1', title: 'Original', open: true, onOpenChange: vi.fn() },
        ],
      };

      const result = reducer(initialState, {
        type: 'UPDATE_TOAST',
        toast: { id: '1', title: 'Updated' },
      });

      expect(result.toasts[0].title).toBe('Updated');
      expect(result.toasts[0].open).toBe(true);
    });

    it('handles DISMISS_TOAST action for specific toast', () => {
      const initialState = {
        toasts: [
          { id: '1', title: 'Toast 1', open: true, onOpenChange: vi.fn() },
          { id: '2', title: 'Toast 2', open: true, onOpenChange: vi.fn() },
        ],
      };

      const result = reducer(initialState, {
        type: 'DISMISS_TOAST',
        toastId: '1',
      });

      expect(result.toasts[0].open).toBe(false);
      expect(result.toasts[1].open).toBe(true);
    });

    it('handles DISMISS_TOAST action without toastId (dismiss all)', () => {
      const initialState = {
        toasts: [
          { id: '1', title: 'Toast 1', open: true, onOpenChange: vi.fn() },
          { id: '2', title: 'Toast 2', open: true, onOpenChange: vi.fn() },
        ],
      };

      const result = reducer(initialState, {
        type: 'DISMISS_TOAST',
      });

      expect(result.toasts.every((t) => !t.open)).toBe(true);
    });

    it('handles REMOVE_TOAST action for specific toast', () => {
      const initialState = {
        toasts: [
          { id: '1', title: 'Toast 1', open: true, onOpenChange: vi.fn() },
          { id: '2', title: 'Toast 2', open: true, onOpenChange: vi.fn() },
        ],
      };

      const result = reducer(initialState, {
        type: 'REMOVE_TOAST',
        toastId: '1',
      });

      expect(result.toasts).toHaveLength(1);
      expect(result.toasts[0].id).toBe('2');
    });

    it('handles REMOVE_TOAST action without toastId (remove all)', () => {
      const initialState = {
        toasts: [
          { id: '1', title: 'Toast 1', open: true, onOpenChange: vi.fn() },
          { id: '2', title: 'Toast 2', open: true, onOpenChange: vi.fn() },
        ],
      };

      const result = reducer(initialState, {
        type: 'REMOVE_TOAST',
      });

      expect(result.toasts).toHaveLength(0);
    });
  });

  describe('toast function', () => {
    it('creates a toast with unique id', () => {
      const result1 = toast({ title: 'Toast 1' });
      const result2 = toast({ title: 'Toast 2' });

      expect(result1.id).toBeDefined();
      expect(result2.id).toBeDefined();
      expect(result1.id).not.toBe(result2.id);
    });

    it('returns dismiss and update functions', () => {
      const result = toast({ title: 'Test' });

      expect(typeof result.dismiss).toBe('function');
      expect(typeof result.update).toBe('function');
    });
  });

  describe('useToast hook', () => {
    it('returns toasts array and helper functions', () => {
      const { result } = renderHook(() => useToast());

      expect(result.current.toasts).toBeDefined();
      expect(Array.isArray(result.current.toasts)).toBe(true);
      expect(typeof result.current.toast).toBe('function');
      expect(typeof result.current.dismiss).toBe('function');
    });

    it('updates when toast is added', () => {
      const { result } = renderHook(() => useToast());

      act(() => {
        result.current.toast({ title: 'New Toast' });
      });

      expect(result.current.toasts.length).toBeGreaterThan(0);
    });

    it('can dismiss a toast by id', () => {
      const { result } = renderHook(() => useToast());

      let toastId: string;
      act(() => {
        const t = result.current.toast({ title: 'To Dismiss' });
        toastId = t.id;
      });

      act(() => {
        result.current.dismiss(toastId);
      });

      const dismissedToast = result.current.toasts.find((t) => t.id === toastId);
      expect(dismissedToast?.open).toBe(false);
    });

    it('can dismiss all toasts', () => {
      const { result } = renderHook(() => useToast());

      act(() => {
        result.current.toast({ title: 'Toast 1' });
        result.current.toast({ title: 'Toast 2' });
      });

      act(() => {
        result.current.dismiss();
      });

      expect(result.current.toasts.every((t) => !t.open)).toBe(true);
    });
  });
});
