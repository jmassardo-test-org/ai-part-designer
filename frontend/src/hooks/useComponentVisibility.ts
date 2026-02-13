/**
 * useComponentVisibility Hook
 *
 * Manages component visibility state for assembly viewers including
 * hide/show toggling, isolate mode, show-all, and optional
 * sessionStorage persistence keyed by assembly ID.
 */

import { useState, useCallback, useEffect, useMemo } from 'react';

// =============================================================================
// Types
// =============================================================================

/** Options for configuring the useComponentVisibility hook. */
export interface UseComponentVisibilityOptions {
  /** Component IDs available in the assembly. */
  componentIds: string[];
  /** Assembly ID for sessionStorage persistence (optional). */
  assemblyId?: string;
  /** Externally controlled hidden components (overrides local state). */
  externalHiddenComponents?: Set<string>;
}

/** Tracks whether isolate mode is active and its context. */
export interface IsolateState {
  /** Whether isolate mode is active. */
  isActive: boolean;
  /** The component ID being isolated. */
  targetId: string | null;
  /** Snapshot of hidden components before isolate was activated (for restore). */
  preIsolateHidden: Set<string>;
}

/** Return value of the useComponentVisibility hook. */
export interface UseComponentVisibilityReturn {
  /** Set of currently hidden component IDs. */
  hiddenComponents: Set<string>;
  /** Current isolate state. */
  isolateState: IsolateState;
  /** Toggle visibility of a single component. */
  toggleVisibility: (componentId: string) => void;
  /** Hide a specific component. */
  hideComponent: (componentId: string) => void;
  /** Show a specific component. */
  showComponent: (componentId: string) => void;
  /** Isolate a component (show only it, hide all others). Toggle behavior. */
  isolateComponent: (componentId: string) => void;
  /** Show all components and exit isolate mode. */
  showAll: () => void;
  /** Check if a specific component is hidden. */
  isHidden: (componentId: string) => boolean;
  /** Number of hidden components. */
  hiddenCount: number;
}

// =============================================================================
// Storage helpers
// =============================================================================

/** Current storage schema version. */
const STORAGE_VERSION = 1;

interface StorageData {
  version: number;
  hidden: string[];
  isolate: {
    isActive: boolean;
    targetId: string | null;
  };
}

/**
 * Build a sessionStorage key for the given assembly ID.
 *
 * @param assemblyId - The assembly identifier.
 * @returns The storage key string.
 */
function storageKey(assemblyId: string): string {
  return `assembly-visibility:${assemblyId}`;
}

/**
 * Load persisted visibility state from sessionStorage.
 *
 * @param assemblyId - The assembly identifier.
 * @param validIds - Set of valid component IDs to filter stale entries.
 * @returns The parsed storage data or null when absent/invalid.
 */
function loadFromStorage(
  assemblyId: string,
  validIds: Set<string>,
): StorageData | null {
  try {
    const raw = sessionStorage.getItem(storageKey(assemblyId));
    if (!raw) return null;

    const parsed: unknown = JSON.parse(raw);
    if (
      typeof parsed !== 'object' ||
      parsed === null ||
      !('version' in parsed)
    ) {
      return null;
    }

    const data = parsed as StorageData;
    if (data.version !== STORAGE_VERSION) return null;

    // Filter out stale IDs that no longer exist in the assembly
    const filteredHidden = (data.hidden ?? []).filter((id) => validIds.has(id));

    const isolateTargetValid =
      data.isolate?.targetId != null && validIds.has(data.isolate.targetId);

    return {
      version: STORAGE_VERSION,
      hidden: filteredHidden,
      isolate: {
        isActive: isolateTargetValid ? (data.isolate?.isActive ?? false) : false,
        targetId: isolateTargetValid ? data.isolate.targetId : null,
      },
    };
  } catch {
    return null;
  }
}

/**
 * Persist visibility state to sessionStorage.
 *
 * @param assemblyId - The assembly identifier.
 * @param hidden - Currently hidden component IDs.
 * @param isolate - Current isolate state (active flag and target).
 */
function saveToStorage(
  assemblyId: string,
  hidden: Set<string>,
  isolate: { isActive: boolean; targetId: string | null },
): void {
  try {
    const data: StorageData = {
      version: STORAGE_VERSION,
      hidden: Array.from(hidden),
      isolate: {
        isActive: isolate.isActive,
        targetId: isolate.targetId,
      },
    };
    sessionStorage.setItem(storageKey(assemblyId), JSON.stringify(data));
  } catch {
    // Silently ignore storage errors (quota exceeded, etc.)
  }
}

// =============================================================================
// Default isolate state
// =============================================================================

const DEFAULT_ISOLATE_STATE: IsolateState = {
  isActive: false,
  targetId: null,
  preIsolateHidden: new Set(),
};

// =============================================================================
// Hook
// =============================================================================

/**
 * Manages component visibility for assembly viewers.
 *
 * Supports toggling individual components, isolating a single component,
 * showing all, and optionally persisting state to sessionStorage.
 *
 * @param options - Configuration options for the hook.
 * @returns Visibility state and control functions.
 */
export function useComponentVisibility({
  componentIds,
  assemblyId,
  externalHiddenComponents,
}: UseComponentVisibilityOptions): UseComponentVisibilityReturn {
  // ── Local state ──────────────────────────────────────────────────────
  const [localHiddenComponents, setLocalHiddenComponents] = useState<Set<string>>(() => {
    // Attempt to restore from sessionStorage on mount
    if (assemblyId) {
      const validIds = new Set(componentIds);
      const stored = loadFromStorage(assemblyId, validIds);
      if (stored) {
        return new Set(stored.hidden);
      }
    }
    return new Set();
  });

  const [isolateState, setIsolateState] = useState<IsolateState>(() => {
    if (assemblyId) {
      const validIds = new Set(componentIds);
      const stored = loadFromStorage(assemblyId, validIds);
      if (stored && stored.isolate.isActive && stored.isolate.targetId) {
        return {
          isActive: true,
          targetId: stored.isolate.targetId,
          // Use the stored hidden list as pre-isolate snapshot
          preIsolateHidden: new Set(stored.hidden),
        };
        // We also need to set localHiddenComponents to allExceptTarget — handled below
      }
    }
    return DEFAULT_ISOLATE_STATE;
  });

  // If we restored an isolate state, ensure the hidden set reflects it
  useEffect(() => {
    if (isolateState.isActive && isolateState.targetId && !externalHiddenComponents) {
      const allExceptTarget = new Set(
        componentIds.filter((id) => id !== isolateState.targetId),
      );
      setLocalHiddenComponents(allExceptTarget);
    }
    // Only run on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Resolved hidden components ───────────────────────────────────────
  const hiddenComponents = externalHiddenComponents ?? localHiddenComponents;

  // ── Persist to sessionStorage ────────────────────────────────────────
  useEffect(() => {
    if (!assemblyId) return;

    // When persisting, store the pre-isolate hidden set if in isolate mode
    // so we can restore properly. Otherwise store current hidden.
    const hiddenToStore = isolateState.isActive
      ? isolateState.preIsolateHidden
      : hiddenComponents;

    saveToStorage(assemblyId, hiddenToStore, {
      isActive: isolateState.isActive,
      targetId: isolateState.targetId,
    });
  }, [assemblyId, hiddenComponents, isolateState]);

  // ── Actions ──────────────────────────────────────────────────────────

  /** Toggle visibility of a single component. Exits isolate mode first if active. */
  const toggleVisibility = useCallback(
    (componentId: string) => {
      if (externalHiddenComponents) return; // Controlled mode — no local mutations

      // If in isolate mode, exit it first then toggle
      if (isolateState.isActive) {
        setIsolateState(DEFAULT_ISOLATE_STATE);
        setLocalHiddenComponents((_prev) => {
          // Restore pre-isolate then toggle
          const restored = new Set(isolateState.preIsolateHidden);
          if (restored.has(componentId)) {
            restored.delete(componentId);
          } else {
            restored.add(componentId);
          }
          return restored;
        });
        return;
      }

      setLocalHiddenComponents((prev) => {
        const next = new Set(prev);
        if (next.has(componentId)) {
          next.delete(componentId);
        } else {
          next.add(componentId);
        }
        return next;
      });
    },
    [externalHiddenComponents, isolateState],
  );

  /** Hide a specific component. */
  const hideComponent = useCallback(
    (componentId: string) => {
      if (externalHiddenComponents) return;
      setLocalHiddenComponents((prev) => {
        const next = new Set(prev);
        next.add(componentId);
        return next;
      });
    },
    [externalHiddenComponents],
  );

  /** Show a specific component. */
  const showComponent = useCallback(
    (componentId: string) => {
      if (externalHiddenComponents) return;
      setLocalHiddenComponents((prev) => {
        const next = new Set(prev);
        next.delete(componentId);
        return next;
      });
    },
    [externalHiddenComponents],
  );

  /**
   * Isolate a component — show only it, hide all others.
   *
   * - If already isolated on same ID → exit isolate, restore pre-isolate state.
   * - If already isolated on different ID → switch target.
   * - If not isolated → snapshot current hidden, hide all except target.
   */
  const isolateComponent = useCallback(
    (componentId: string) => {
      if (externalHiddenComponents) return;

      setIsolateState((prev) => {
        if (prev.isActive) {
          if (prev.targetId === componentId) {
            // Toggle off — restore pre-isolate hidden
            setLocalHiddenComponents(new Set(prev.preIsolateHidden));
            return DEFAULT_ISOLATE_STATE;
          } else {
            // Switch target — keep preIsolateHidden, update hidden
            const allExceptNew = new Set(
              componentIds.filter((id) => id !== componentId),
            );
            setLocalHiddenComponents(allExceptNew);
            return {
              ...prev,
              targetId: componentId,
            };
          }
        }

        // Not isolated — enter isolate mode
        const snapshot = new Set(localHiddenComponents);
        const allExceptTarget = new Set(
          componentIds.filter((id) => id !== componentId),
        );
        setLocalHiddenComponents(allExceptTarget);

        return {
          isActive: true,
          targetId: componentId,
          preIsolateHidden: snapshot,
        };
      });
    },
    [externalHiddenComponents, componentIds, localHiddenComponents],
  );

  /** Show all components and exit isolate mode. */
  const showAll = useCallback(() => {
    if (externalHiddenComponents) return;
    setLocalHiddenComponents(new Set());
    setIsolateState(DEFAULT_ISOLATE_STATE);
  }, [externalHiddenComponents]);

  /** Check if a specific component is hidden. */
  const isHidden = useCallback(
    (componentId: string): boolean => hiddenComponents.has(componentId),
    [hiddenComponents],
  );

  /** Number of hidden components. */
  const hiddenCount = useMemo(() => hiddenComponents.size, [hiddenComponents]);

  return {
    hiddenComponents,
    isolateState,
    toggleVisibility,
    hideComponent,
    showComponent,
    isolateComponent,
    showAll,
    isHidden,
    hiddenCount,
  };
}
