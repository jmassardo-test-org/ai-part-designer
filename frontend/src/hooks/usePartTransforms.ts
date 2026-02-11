/**
 * Part Transforms Hook
 * 
 * Manages part transformations with undo/redo support.
 */

import { useState, useCallback, useEffect } from 'react';
import type { PartTransform } from '../components/viewer/PartTransformControls';
import { useDesignHistory, type DesignState } from './useDesignHistory';

// =============================================================================
// Types
// =============================================================================

export interface PartTransformState {
  [partId: string]: PartTransform;
}

export interface UsePartTransformsOptions {
  initialTransforms?: PartTransformState;
  onTransformUpdate?: (partId: string, transform: PartTransform) => void;
  maxHistory?: number;
}

export interface UsePartTransformsReturn {
  // Current transforms
  transforms: PartTransformState;
  
  // Transform operations
  updateTransform: (partId: string, transform: PartTransform, description?: string) => void;
  resetTransform: (partId: string, description?: string) => void;
  resetAllTransforms: (description?: string) => void;
  
  // Undo/redo
  canUndo: boolean;
  canRedo: boolean;
  undo: () => void;
  redo: () => void;
  undoDescription: string | null;
  redoDescription: string | null;
  
  // History
  clearHistory: () => void;
}

// =============================================================================
// Helper Functions
// =============================================================================

function createDesignState(
  transforms: PartTransformState,
  description: string
): DesignState {
  return {
    id: crypto.randomUUID(),
    timestamp: new Date(),
    description,
    data: transforms,
  };
}

// =============================================================================
// Hook
// =============================================================================

export function usePartTransforms({
  initialTransforms = {},
  onTransformUpdate,
  maxHistory = 50,
}: UsePartTransformsOptions = {}): UsePartTransformsReturn {
  const [transforms, setTransforms] = useState<PartTransformState>(initialTransforms);
  const [isInitialized, setIsInitialized] = useState(false);

  const history = useDesignHistory({
    maxHistory,
    onStateChange: (state) => {
      if (state && state.data) {
        setTransforms(state.data as PartTransformState);
      }
    },
  });

  // Push initial state on mount
  useEffect(() => {
    if (!isInitialized) {
      history.pushState(
        createDesignState(initialTransforms, 'Initial state'),
        'Initial state'
      );
      setIsInitialized(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const updateTransform = useCallback(
    (partId: string, transform: PartTransform, description?: string) => {
      setTransforms((prev) => {
        const next = {
          ...prev,
          [partId]: transform,
        };

        // Push to history
        const desc = description || `Move ${partId}`;
        history.pushState(createDesignState(next, desc), desc);

        // Notify parent
        onTransformUpdate?.(partId, transform);

        return next;
      });
    },
    [history, onTransformUpdate]
  );

  const resetTransform = useCallback(
    (partId: string, description?: string) => {
      setTransforms((prev) => {
        const next = { ...prev };
        delete next[partId];

        // Push to history
        const desc = description || `Reset ${partId}`;
        history.pushState(createDesignState(next, desc), desc);

        return next;
      });
    },
    [history]
  );

  const resetAllTransforms = useCallback(
    (description?: string) => {
      setTransforms({});
      const desc = description || 'Reset all transforms';
      history.pushState(createDesignState({}, desc), desc);
    },
    [history]
  );

  const undo = useCallback(() => {
    const state = history.undo();
    if (state && state.data) {
      setTransforms(state.data as PartTransformState);
    }
  }, [history]);

  const redo = useCallback(() => {
    const state = history.redo();
    if (state && state.data) {
      setTransforms(state.data as PartTransformState);
    }
  }, [history]);

  const clearHistory = useCallback(() => {
    history.clear();
  }, [history]);

  return {
    transforms,
    updateTransform,
    resetTransform,
    resetAllTransforms,
    canUndo: history.canUndo,
    canRedo: history.canRedo,
    undo,
    redo,
    undoDescription: history.undoDescription,
    redoDescription: history.redoDescription,
    clearHistory,
  };
}

export default usePartTransforms;
