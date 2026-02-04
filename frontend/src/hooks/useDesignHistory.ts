/**
 * Design History Hook
 * 
 * Manages undo/redo state for design changes.
 * Uses a stack-based history pattern with combined state.
 */

import { useState, useCallback, useMemo } from 'react';

// =============================================================================
// Types
// =============================================================================

export interface DesignState {
  id: string;
  timestamp: Date;
  description: string;
  data: unknown;
}

export interface HistoryEntry {
  id: string;
  timestamp: Date;
  description: string;
  state: DesignState;
}

interface UseDesignHistoryOptions {
  maxHistory?: number;
  onStateChange?: (state: DesignState | null) => void;
}

interface HistoryState {
  entries: HistoryEntry[];
  index: number;
}

interface UseDesignHistoryReturn {
  // State
  currentState: DesignState | null;
  history: HistoryEntry[];
  historyIndex: number;
  
  // Capabilities
  canUndo: boolean;
  canRedo: boolean;
  
  // Actions
  pushState: (state: DesignState, description: string) => void;
  undo: () => DesignState | null;
  redo: () => DesignState | null;
  goToIndex: (index: number) => DesignState | null;
  clear: () => void;
  
  // Computed
  undoDescription: string | null;
  redoDescription: string | null;
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useDesignHistory(
  options: UseDesignHistoryOptions = {}
): UseDesignHistoryReturn {
  const { maxHistory = 50, onStateChange } = options;

  // Combined state to avoid sync issues between history and index
  const [state, setState] = useState<HistoryState>({
    entries: [],
    index: -1,
  });

  const history = state.entries;
  const historyIndex = state.index;

  const currentState = useMemo(() => {
    if (historyIndex >= 0 && historyIndex < history.length) {
      return history[historyIndex].state;
    }
    return null;
  }, [history, historyIndex]);

  const canUndo = historyIndex > 0;
  const canRedo = historyIndex >= 0 && historyIndex < history.length - 1;

  const undoDescription = useMemo(() => {
    if (canUndo && historyIndex >= 0 && history[historyIndex]) {
      return history[historyIndex].description;
    }
    return null;
  }, [canUndo, history, historyIndex]);

  const redoDescription = useMemo(() => {
    if (canRedo && history[historyIndex + 1]) {
      return history[historyIndex + 1].description;
    }
    return null;
  }, [canRedo, history, historyIndex]);

  const pushState = useCallback(
    (newState: DesignState, description: string) => {
      setState((prev) => {
        // Remove any "future" states if we're not at the end
        const newEntries = prev.entries.slice(0, prev.index + 1);

        // Add new entry
        const entry: HistoryEntry = {
          id: crypto.randomUUID(),
          timestamp: new Date(),
          description,
          state: newState,
        };

        newEntries.push(entry);

        // Trim to max history (remove from beginning)
        while (newEntries.length > maxHistory) {
          newEntries.shift();
        }

        return {
          entries: newEntries,
          index: newEntries.length - 1,
        };
      });

      onStateChange?.(newState);
    },
    [maxHistory, onStateChange]
  );

  const undo = useCallback((): DesignState | null => {
    if (!canUndo) return null;

    const newIndex = historyIndex - 1;
    const resultState = history[newIndex]?.state ?? null;
    
    setState((prev) => ({
      ...prev,
      index: newIndex,
    }));

    onStateChange?.(resultState);
    return resultState;
  }, [canUndo, history, historyIndex, onStateChange]);

  const redo = useCallback((): DesignState | null => {
    if (!canRedo) return null;

    const newIndex = historyIndex + 1;
    const resultState = history[newIndex]?.state ?? null;
    
    setState((prev) => ({
      ...prev,
      index: newIndex,
    }));

    onStateChange?.(resultState);
    return resultState;
  }, [canRedo, history, historyIndex, onStateChange]);

  const goToIndex = useCallback(
    (targetIndex: number): DesignState | null => {
      if (targetIndex < 0 || targetIndex >= history.length) return null;

      const resultState = history[targetIndex]?.state ?? null;
      
      setState((prev) => ({
        ...prev,
        index: targetIndex,
      }));

      onStateChange?.(resultState);
      return resultState;
    },
    [history, onStateChange]
  );

  const clear = useCallback(() => {
    setState({
      entries: [],
      index: -1,
    });
    onStateChange?.(null);
  }, [onStateChange]);

  return {
    currentState,
    history,
    historyIndex,
    canUndo,
    canRedo,
    pushState,
    undo,
    redo,
    goToIndex,
    clear,
    undoDescription,
    redoDescription,
  };
}

export default useDesignHistory;
