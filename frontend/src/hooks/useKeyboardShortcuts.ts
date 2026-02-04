/**
 * useKeyboardShortcuts Hook
 * 
 * Provides global keyboard shortcuts for power users.
 * Handles common actions like save, export, search, etc.
 */

import { useEffect, useCallback, useMemo } from 'react';

// =============================================================================
// Types
// =============================================================================

export interface KeyboardShortcut {
  /** Unique identifier for the shortcut */
  id: string;
  /** Key to press (e.g., 'k', 's', 'Enter') */
  key: string;
  /** Whether Ctrl (or Cmd on Mac) is required */
  ctrl?: boolean;
  /** Whether Shift is required */
  shift?: boolean;
  /** Whether Alt (or Option on Mac) is required */
  alt?: boolean;
  /** Description of what the shortcut does */
  description: string;
  /** Category for grouping in help dialog */
  category?: 'navigation' | 'actions' | 'editing' | 'view';
  /** Whether the shortcut is enabled */
  enabled?: boolean;
  /** Handler function */
  handler: () => void;
}

interface UseKeyboardShortcutsOptions {
  /** List of shortcuts to register */
  shortcuts: KeyboardShortcut[];
  /** Whether shortcuts are globally enabled */
  enabled?: boolean;
  /** Elements to ignore shortcuts in (e.g., inputs) */
  ignoreInputs?: boolean;
}

// =============================================================================
// Predefined Shortcut Configurations
// =============================================================================

export const SHORTCUT_KEYS = {
  // Navigation
  QUICK_SEARCH: { key: 'k', ctrl: true },
  TOGGLE_HISTORY: { key: 'h', ctrl: true },
  NEW_DESIGN: { key: 'n', ctrl: true },
  GO_TO_DASHBOARD: { key: 'd', ctrl: true, shift: true },
  
  // Actions
  SAVE: { key: 's', ctrl: true },
  EXPORT: { key: 'e', ctrl: true },
  UNDO: { key: 'z', ctrl: true },
  REDO: { key: 'z', ctrl: true, shift: true },
  
  // View
  TOGGLE_THEME: { key: 't', ctrl: true, shift: true },
  ZOOM_IN: { key: '=', ctrl: true },
  ZOOM_OUT: { key: '-', ctrl: true },
  RESET_VIEW: { key: '0', ctrl: true },
  
  // General
  CLOSE_MODAL: { key: 'Escape' },
  HELP: { key: '?', shift: true },
} as const;

// =============================================================================
// Hook
// =============================================================================

export function useKeyboardShortcuts(
  options: UseKeyboardShortcutsOptions
): void {
  const { shortcuts, enabled = true, ignoreInputs = true } = options;

  // Create a map of shortcuts for quick lookup
  const shortcutMap = useMemo(() => {
    const map = new Map<string, KeyboardShortcut>();
    
    for (const shortcut of shortcuts) {
      if (shortcut.enabled === false) continue;
      
      // Create a unique key for this shortcut combination
      const parts = [];
      if (shortcut.ctrl) parts.push('ctrl');
      if (shortcut.shift) parts.push('shift');
      if (shortcut.alt) parts.push('alt');
      parts.push(shortcut.key.toLowerCase());
      
      map.set(parts.join('+'), shortcut);
    }
    
    return map;
  }, [shortcuts]);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return;
      
      // Guard against missing event.key (can happen in some test environments)
      if (!event.key) return;

      // Ignore shortcuts when typing in inputs
      if (ignoreInputs) {
        const target = event.target as HTMLElement;
        const tagName = target.tagName?.toLowerCase() || '';
        const isInput =
          tagName === 'input' ||
          tagName === 'textarea' ||
          tagName === 'select' ||
          target.isContentEditable;
        
        // Allow Escape in inputs
        if (isInput && event.key !== 'Escape') {
          return;
        }
      }

      // Build the key combination string
      const parts = [];
      if (event.ctrlKey || event.metaKey) parts.push('ctrl');
      if (event.shiftKey) parts.push('shift');
      if (event.altKey) parts.push('alt');
      parts.push(event.key.toLowerCase());
      
      const keyCombo = parts.join('+');
      const shortcut = shortcutMap.get(keyCombo);

      if (shortcut) {
        event.preventDefault();
        shortcut.handler();
      }
    },
    [enabled, ignoreInputs, shortcutMap]
  );

  useEffect(() => {
    if (!enabled) return;

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [enabled, handleKeyDown]);
}

// =============================================================================
// Helper Hook for Common Shortcuts
// =============================================================================

interface UseCommonShortcutsOptions {
  onSave?: () => void;
  onExport?: () => void;
  onUndo?: () => void;
  onRedo?: () => void;
  onNewDesign?: () => void;
  onToggleHistory?: () => void;
  onQuickSearch?: () => void;
  onHelp?: () => void;
  enabled?: boolean;
}

export function useCommonShortcuts(options: UseCommonShortcutsOptions): void {
  const {
    onSave,
    onExport,
    onUndo,
    onRedo,
    onNewDesign,
    onToggleHistory,
    onQuickSearch,
    onHelp,
    enabled = true,
  } = options;

  const shortcuts = useMemo<KeyboardShortcut[]>(() => {
    const list: KeyboardShortcut[] = [];

    if (onSave) {
      list.push({
        id: 'save',
        ...SHORTCUT_KEYS.SAVE,
        description: 'Save current design',
        category: 'actions',
        handler: onSave,
      });
    }

    if (onExport) {
      list.push({
        id: 'export',
        ...SHORTCUT_KEYS.EXPORT,
        description: 'Export design',
        category: 'actions',
        handler: onExport,
      });
    }

    if (onUndo) {
      list.push({
        id: 'undo',
        ...SHORTCUT_KEYS.UNDO,
        description: 'Undo last action',
        category: 'editing',
        handler: onUndo,
      });
    }

    if (onRedo) {
      list.push({
        id: 'redo',
        ...SHORTCUT_KEYS.REDO,
        description: 'Redo last action',
        category: 'editing',
        handler: onRedo,
      });
    }

    if (onNewDesign) {
      list.push({
        id: 'new-design',
        ...SHORTCUT_KEYS.NEW_DESIGN,
        description: 'Create new design',
        category: 'navigation',
        handler: onNewDesign,
      });
    }

    if (onToggleHistory) {
      list.push({
        id: 'toggle-history',
        ...SHORTCUT_KEYS.TOGGLE_HISTORY,
        description: 'Toggle history panel',
        category: 'navigation',
        handler: onToggleHistory,
      });
    }

    if (onQuickSearch) {
      list.push({
        id: 'quick-search',
        ...SHORTCUT_KEYS.QUICK_SEARCH,
        description: 'Open quick search',
        category: 'navigation',
        handler: onQuickSearch,
      });
    }

    if (onHelp) {
      list.push({
        id: 'help',
        ...SHORTCUT_KEYS.HELP,
        description: 'Show keyboard shortcuts',
        category: 'view',
        handler: onHelp,
      });
    }

    return list;
  }, [onSave, onExport, onUndo, onRedo, onNewDesign, onToggleHistory, onQuickSearch, onHelp]);

  useKeyboardShortcuts({ shortcuts, enabled });
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Format a shortcut for display (e.g., "⌘K" or "Ctrl+K")
 */
export function formatShortcut(shortcut: Partial<KeyboardShortcut>): string {
  const isMac =
    typeof navigator !== 'undefined' &&
    navigator.platform.toLowerCase().includes('mac');

  const parts: string[] = [];

  if (shortcut.ctrl) {
    parts.push(isMac ? '⌘' : 'Ctrl');
  }
  if (shortcut.shift) {
    parts.push(isMac ? '⇧' : 'Shift');
  }
  if (shortcut.alt) {
    parts.push(isMac ? '⌥' : 'Alt');
  }

  // Format the key
  let key = shortcut.key || '';
  if (key === 'Escape') key = 'Esc';
  if (key === ' ') key = 'Space';
  if (key.length === 1) key = key.toUpperCase();

  parts.push(key);

  return isMac ? parts.join('') : parts.join('+');
}

/**
 * Get all registered shortcuts grouped by category
 */
export function groupShortcutsByCategory(
  shortcuts: KeyboardShortcut[]
): Record<string, KeyboardShortcut[]> {
  const groups: Record<string, KeyboardShortcut[]> = {
    navigation: [],
    actions: [],
    editing: [],
    view: [],
  };

  for (const shortcut of shortcuts) {
    const category = shortcut.category || 'actions';
    if (!groups[category]) groups[category] = [];
    groups[category].push(shortcut);
  }

  return groups;
}

export default useKeyboardShortcuts;
