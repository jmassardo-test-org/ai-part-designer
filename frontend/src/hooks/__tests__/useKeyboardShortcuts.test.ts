/**
 * Tests for useKeyboardShortcuts Hook
 */

import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  useKeyboardShortcuts,
  useCommonShortcuts,
  formatShortcut,
  groupShortcutsByCategory,
  KeyboardShortcut,
} from '../useKeyboardShortcuts';

describe('useKeyboardShortcuts', () => {
  const createShortcut = (overrides: Partial<KeyboardShortcut> = {}): KeyboardShortcut => ({
    id: 'test',
    key: 's',
    ctrl: true,
    description: 'Test shortcut',
    handler: vi.fn(),
    ...overrides,
  });

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('basic functionality', () => {
    it('calls handler when shortcut is pressed', () => {
      const handler = vi.fn();
      const shortcut = createShortcut({ handler });

      renderHook(() =>
        useKeyboardShortcuts({ shortcuts: [shortcut] })
      );

      act(() => {
        const event = new KeyboardEvent('keydown', {
          key: 's',
          ctrlKey: true,
          bubbles: true,
        });
        document.dispatchEvent(event);
      });

      expect(handler).toHaveBeenCalled();
    });

    it('does not call handler when wrong key is pressed', () => {
      const handler = vi.fn();
      const shortcut = createShortcut({ key: 's', handler });

      renderHook(() =>
        useKeyboardShortcuts({ shortcuts: [shortcut] })
      );

      act(() => {
        const event = new KeyboardEvent('keydown', {
          key: 'k',
          ctrlKey: true,
          bubbles: true,
        });
        document.dispatchEvent(event);
      });

      expect(handler).not.toHaveBeenCalled();
    });

    it('does not call handler when modifier is missing', () => {
      const handler = vi.fn();
      const shortcut = createShortcut({ key: 's', ctrl: true, handler });

      renderHook(() =>
        useKeyboardShortcuts({ shortcuts: [shortcut] })
      );

      act(() => {
        const event = new KeyboardEvent('keydown', {
          key: 's',
          ctrlKey: false,
          bubbles: true,
        });
        document.dispatchEvent(event);
      });

      expect(handler).not.toHaveBeenCalled();
    });

    it('handles multiple shortcuts', () => {
      const handler1 = vi.fn();
      const handler2 = vi.fn();

      const shortcuts = [
        createShortcut({ id: '1', key: 's', ctrl: true, handler: handler1 }),
        createShortcut({ id: '2', key: 'e', ctrl: true, handler: handler2 }),
      ];

      renderHook(() =>
        useKeyboardShortcuts({ shortcuts })
      );

      act(() => {
        document.dispatchEvent(
          new KeyboardEvent('keydown', { key: 's', ctrlKey: true, bubbles: true })
        );
      });

      expect(handler1).toHaveBeenCalled();
      expect(handler2).not.toHaveBeenCalled();

      act(() => {
        document.dispatchEvent(
          new KeyboardEvent('keydown', { key: 'e', ctrlKey: true, bubbles: true })
        );
      });

      expect(handler2).toHaveBeenCalled();
    });
  });

  describe('modifier keys', () => {
    it('handles Ctrl modifier', () => {
      const handler = vi.fn();
      const shortcut = createShortcut({ key: 's', ctrl: true, handler });

      renderHook(() => useKeyboardShortcuts({ shortcuts: [shortcut] }));

      act(() => {
        document.dispatchEvent(
          new KeyboardEvent('keydown', { key: 's', ctrlKey: true, bubbles: true })
        );
      });

      expect(handler).toHaveBeenCalled();
    });

    it('handles Shift modifier', () => {
      const handler = vi.fn();
      const shortcut = createShortcut({ key: 'z', ctrl: true, shift: true, handler });

      renderHook(() => useKeyboardShortcuts({ shortcuts: [shortcut] }));

      act(() => {
        document.dispatchEvent(
          new KeyboardEvent('keydown', {
            key: 'z',
            ctrlKey: true,
            shiftKey: true,
            bubbles: true,
          })
        );
      });

      expect(handler).toHaveBeenCalled();
    });

    it('handles Alt modifier', () => {
      const handler = vi.fn();
      const shortcut = createShortcut({ key: 'a', ctrl: false, alt: true, handler });

      renderHook(() => useKeyboardShortcuts({ shortcuts: [shortcut] }));

      act(() => {
        document.dispatchEvent(
          new KeyboardEvent('keydown', { key: 'a', altKey: true, bubbles: true })
        );
      });

      expect(handler).toHaveBeenCalled();
    });

    it('handles Meta key (Cmd on Mac)', () => {
      const handler = vi.fn();
      const shortcut = createShortcut({ key: 's', ctrl: true, handler });

      renderHook(() => useKeyboardShortcuts({ shortcuts: [shortcut] }));

      act(() => {
        document.dispatchEvent(
          new KeyboardEvent('keydown', { key: 's', metaKey: true, bubbles: true })
        );
      });

      expect(handler).toHaveBeenCalled();
    });
  });

  describe('enabled option', () => {
    it('ignores shortcuts when disabled', () => {
      const handler = vi.fn();
      const shortcut = createShortcut({ handler });

      renderHook(() =>
        useKeyboardShortcuts({ shortcuts: [shortcut], enabled: false })
      );

      act(() => {
        document.dispatchEvent(
          new KeyboardEvent('keydown', { key: 's', ctrlKey: true, bubbles: true })
        );
      });

      expect(handler).not.toHaveBeenCalled();
    });
  });

  describe('ignoreInputs option', () => {
    it('allows Escape in inputs when ignoreInputs is true', () => {
      const handler = vi.fn();
      const shortcut = createShortcut({ key: 'Escape', ctrl: false, handler });

      renderHook(() =>
        useKeyboardShortcuts({ shortcuts: [shortcut], ignoreInputs: true })
      );

      // Create an input element
      const input = document.createElement('input');
      document.body.appendChild(input);
      input.focus();

      act(() => {
        const event = new KeyboardEvent('keydown', {
          key: 'Escape',
          bubbles: true,
        });
        input.dispatchEvent(event);
      });

      expect(handler).toHaveBeenCalled();

      document.body.removeChild(input);
    });
  });

  describe('shortcut.enabled option', () => {
    it('ignores disabled shortcuts', () => {
      const handler = vi.fn();
      const shortcut = createShortcut({ handler, enabled: false });

      renderHook(() => useKeyboardShortcuts({ shortcuts: [shortcut] }));

      act(() => {
        document.dispatchEvent(
          new KeyboardEvent('keydown', { key: 's', ctrlKey: true, bubbles: true })
        );
      });

      expect(handler).not.toHaveBeenCalled();
    });
  });

  describe('cleanup', () => {
    it('removes event listener on unmount', () => {
      const removeEventListenerSpy = vi.spyOn(document, 'removeEventListener');
      const shortcut = createShortcut();

      const { unmount } = renderHook(() =>
        useKeyboardShortcuts({ shortcuts: [shortcut] })
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

describe('useCommonShortcuts', () => {
  it('registers save shortcut', () => {
    const onSave = vi.fn();

    renderHook(() => useCommonShortcuts({ onSave }));

    act(() => {
      document.dispatchEvent(
        new KeyboardEvent('keydown', { key: 's', ctrlKey: true, bubbles: true })
      );
    });

    expect(onSave).toHaveBeenCalled();
  });

  it('registers export shortcut', () => {
    const onExport = vi.fn();

    renderHook(() => useCommonShortcuts({ onExport }));

    act(() => {
      document.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'e', ctrlKey: true, bubbles: true })
      );
    });

    expect(onExport).toHaveBeenCalled();
  });

  it('registers undo shortcut', () => {
    const onUndo = vi.fn();

    renderHook(() => useCommonShortcuts({ onUndo }));

    act(() => {
      document.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'z', ctrlKey: true, bubbles: true })
      );
    });

    expect(onUndo).toHaveBeenCalled();
  });

  it('registers redo shortcut', () => {
    const onRedo = vi.fn();

    renderHook(() => useCommonShortcuts({ onRedo }));

    act(() => {
      document.dispatchEvent(
        new KeyboardEvent('keydown', {
          key: 'z',
          ctrlKey: true,
          shiftKey: true,
          bubbles: true,
        })
      );
    });

    expect(onRedo).toHaveBeenCalled();
  });
});

describe('formatShortcut', () => {
  // Mock navigator for Mac detection
  const originalPlatform = Object.getOwnPropertyDescriptor(navigator, 'platform');

  afterEach(() => {
    if (originalPlatform) {
      Object.defineProperty(navigator, 'platform', originalPlatform);
    }
  });

  it('formats Ctrl+S correctly', () => {
    Object.defineProperty(navigator, 'platform', {
      value: 'Win32',
      configurable: true,
    });

    const result = formatShortcut({ key: 's', ctrl: true });
    expect(result).toBe('Ctrl+S');
  });

  it('formats Ctrl+Shift+Z correctly', () => {
    Object.defineProperty(navigator, 'platform', {
      value: 'Win32',
      configurable: true,
    });

    const result = formatShortcut({ key: 'z', ctrl: true, shift: true });
    expect(result).toBe('Ctrl+Shift+Z');
  });

  it('formats Escape correctly', () => {
    const result = formatShortcut({ key: 'Escape' });
    expect(result).toBe('Esc');
  });
});

describe('groupShortcutsByCategory', () => {
  it('groups shortcuts by category', () => {
    const shortcuts: KeyboardShortcut[] = [
      {
        id: '1',
        key: 's',
        ctrl: true,
        description: 'Save',
        category: 'actions',
        handler: vi.fn(),
      },
      {
        id: '2',
        key: 'z',
        ctrl: true,
        description: 'Undo',
        category: 'editing',
        handler: vi.fn(),
      },
      {
        id: '3',
        key: 'h',
        ctrl: true,
        description: 'History',
        category: 'navigation',
        handler: vi.fn(),
      },
    ];

    const groups = groupShortcutsByCategory(shortcuts);

    expect(groups.actions).toHaveLength(1);
    expect(groups.editing).toHaveLength(1);
    expect(groups.navigation).toHaveLength(1);
    expect(groups.view).toHaveLength(0);
  });

  it('defaults to actions category', () => {
    const shortcuts: KeyboardShortcut[] = [
      {
        id: '1',
        key: 's',
        ctrl: true,
        description: 'Save',
        handler: vi.fn(),
      },
    ];

    const groups = groupShortcutsByCategory(shortcuts);

    expect(groups.actions).toHaveLength(1);
  });
});
