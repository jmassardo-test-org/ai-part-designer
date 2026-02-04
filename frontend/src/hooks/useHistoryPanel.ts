/**
 * useHistoryPanel Hook
 * 
 * Manages state for the history panel including opening/closing
 * and keyboard shortcuts.
 */

import { useState, useCallback, useEffect } from 'react';

interface UseHistoryPanelOptions {
  /** Enable Ctrl+H keyboard shortcut */
  enableShortcut?: boolean;
}

interface UseHistoryPanelReturn {
  /** Whether the panel is open */
  isOpen: boolean;
  /** Open the panel */
  open: () => void;
  /** Close the panel */
  close: () => void;
  /** Toggle the panel */
  toggle: () => void;
}

export function useHistoryPanel(
  options: UseHistoryPanelOptions = {}
): UseHistoryPanelReturn {
  const { enableShortcut = true } = options;
  const [isOpen, setIsOpen] = useState(false);

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);

  // Handle Ctrl+H keyboard shortcut
  useEffect(() => {
    if (!enableShortcut) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl+H or Cmd+H to toggle history
      if ((e.ctrlKey || e.metaKey) && e.key === 'h') {
        e.preventDefault();
        toggle();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [enableShortcut, toggle]);

  return { isOpen, open, close, toggle };
}

export default useHistoryPanel;
