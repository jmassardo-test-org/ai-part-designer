/**
 * Tests for useHistoryPanel Hook
 */

import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useHistoryPanel } from '../useHistoryPanel';

describe('useHistoryPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    // Clean up any event listeners
  });

  describe('initial state', () => {
    it('starts with panel closed', () => {
      const { result } = renderHook(() => useHistoryPanel());
      expect(result.current.isOpen).toBe(false);
    });
  });

  describe('open', () => {
    it('opens the panel', () => {
      const { result } = renderHook(() => useHistoryPanel());

      act(() => {
        result.current.open();
      });

      expect(result.current.isOpen).toBe(true);
    });
  });

  describe('close', () => {
    it('closes the panel', () => {
      const { result } = renderHook(() => useHistoryPanel());

      act(() => {
        result.current.open();
      });

      expect(result.current.isOpen).toBe(true);

      act(() => {
        result.current.close();
      });

      expect(result.current.isOpen).toBe(false);
    });
  });

  describe('toggle', () => {
    it('toggles from closed to open', () => {
      const { result } = renderHook(() => useHistoryPanel());

      act(() => {
        result.current.toggle();
      });

      expect(result.current.isOpen).toBe(true);
    });

    it('toggles from open to closed', () => {
      const { result } = renderHook(() => useHistoryPanel());

      act(() => {
        result.current.open();
      });

      act(() => {
        result.current.toggle();
      });

      expect(result.current.isOpen).toBe(false);
    });
  });

  describe('keyboard shortcut', () => {
    it('opens panel on Ctrl+H', () => {
      const { result } = renderHook(() => useHistoryPanel({ enableShortcut: true }));

      act(() => {
        const event = new KeyboardEvent('keydown', {
          key: 'h',
          ctrlKey: true,
          bubbles: true,
        });
        document.dispatchEvent(event);
      });

      expect(result.current.isOpen).toBe(true);
    });

    it('closes panel on Ctrl+H when open', () => {
      const { result } = renderHook(() => useHistoryPanel({ enableShortcut: true }));

      act(() => {
        result.current.open();
      });

      act(() => {
        const event = new KeyboardEvent('keydown', {
          key: 'h',
          ctrlKey: true,
          bubbles: true,
        });
        document.dispatchEvent(event);
      });

      expect(result.current.isOpen).toBe(false);
    });

    it('opens panel on Cmd+H (Mac)', () => {
      const { result } = renderHook(() => useHistoryPanel({ enableShortcut: true }));

      act(() => {
        const event = new KeyboardEvent('keydown', {
          key: 'h',
          metaKey: true,
          bubbles: true,
        });
        document.dispatchEvent(event);
      });

      expect(result.current.isOpen).toBe(true);
    });

    it('does not respond to shortcut when disabled', () => {
      const { result } = renderHook(() =>
        useHistoryPanel({ enableShortcut: false })
      );

      act(() => {
        const event = new KeyboardEvent('keydown', {
          key: 'h',
          ctrlKey: true,
          bubbles: true,
        });
        document.dispatchEvent(event);
      });

      expect(result.current.isOpen).toBe(false);
    });

    it('does not respond to H without modifier', () => {
      const { result } = renderHook(() => useHistoryPanel({ enableShortcut: true }));

      act(() => {
        const event = new KeyboardEvent('keydown', {
          key: 'h',
          bubbles: true,
        });
        document.dispatchEvent(event);
      });

      expect(result.current.isOpen).toBe(false);
    });
  });

  describe('cleanup', () => {
    it('removes event listener on unmount', () => {
      const removeEventListenerSpy = vi.spyOn(document, 'removeEventListener');
      
      const { unmount } = renderHook(() =>
        useHistoryPanel({ enableShortcut: true })
      );

      unmount();

      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        'keydown',
        expect.any(Function)
      );

      removeEventListenerSpy.mockRestore();
    });
  });
});
