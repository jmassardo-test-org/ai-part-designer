# US-6.4 Part Hide/Show/Isolate — Technical Architecture

**Feature:** Visibility toggle per part, isolate mode, show-all, and session persistence  
**Scope:** Frontend-only, 2 SP  
**Author:** Architecture & Security Agent  
**Date:** 2026-02-13

---

## 1. New Hook: `useComponentVisibility`

### 1.1 TypeScript Interface

```typescript
// frontend/src/hooks/useComponentVisibility.ts

/** Configuration passed to the hook */
export interface UseComponentVisibilityOptions {
  /** All component IDs in the assembly (needed for isolate inverse logic) */
  componentIds: string[];
  /** Assembly ID for sessionStorage key scoping. Must be a valid UUID. */
  assemblyId?: string;
  /** Optional externally-controlled hidden set (overrides local state when provided) */
  externalHiddenComponents?: Set<string>;
}

/** Isolate mode metadata */
export interface IsolateState {
  /** Whether isolate mode is currently active */
  active: boolean;
  /** The component ID that is isolated (visible), null when not isolating */
  targetComponentId: string | null;
  /** Snapshot of hiddenComponents before entering isolate, used for exit-restore */
  preIsolateHidden: Set<string>;
}

/** Return value from the hook */
export interface UseComponentVisibilityReturn {
  /** The current set of hidden component IDs — pass directly to viewer */
  hiddenComponents: Set<string>;

  /** Toggle a single component's visibility (eye icon / H key) */
  toggleVisibility: (componentId: string) => void;
  /** Explicitly hide a component */
  hideComponent: (componentId: string) => void;
  /** Explicitly show a component */
  showComponent: (componentId: string) => void;

  /** Enter or exit isolate mode for a component (I key / button) */
  toggleIsolate: (componentId: string) => void;
  /** Show all components and exit isolate mode (Shift+H / button) */
  showAll: () => void;

  /** Current isolate state (for UI indicators) */
  isolateState: IsolateState;

  /** Whether any components are currently hidden */
  hasHiddenComponents: boolean;
  /** Count of hidden components */
  hiddenCount: number;
}
```

### 1.2 Internal State Management

The hook manages three core pieces of state:

| State | Type | Purpose |
|---|---|---|
| `hiddenComponents` | `Set<string>` | IDs of currently hidden components |
| `isolateState` | `IsolateState` | Tracks whether isolate is active, which component, and pre-isolate snapshot |
| `sessionKey` | `string` | Computed `visibility:${assemblyId}` key for sessionStorage |

**State transitions:**

```
                   toggleVisibility(id)
    ┌──────────┐  ────────────────────>  ┌──────────┐
    │  Visible  │                         │  Hidden   │
    └──────────┘  <────────────────────  └──────────┘
                   toggleVisibility(id)

                   toggleIsolate(id)
    ┌──────────┐  ────────────────────>  ┌──────────────┐
    │  Normal   │                         │  Isolated(id) │
    └──────────┘  <────────────────────  └──────────────┘
                   toggleIsolate(id)
                   OR showAll()
```

### 1.3 Behavior Specification

#### `toggleVisibility(componentId)`
- If isolate mode is active: no-op (prevent conflicting state).
- If `hiddenComponents` contains `componentId`: remove it (show).
- Else: add it (hide).
- Sync to sessionStorage.

#### `hideComponent(componentId)` / `showComponent(componentId)`
- Direct imperative set/delete. Used by context menu or programmatic call.
- Respects isolate guard (no-op if isolate active).

#### `toggleIsolate(componentId)`
- **Enter isolate** (isolate not active):
  1. Snapshot current `hiddenComponents` → `preIsolateHidden`.
  2. Set `hiddenComponents` to all component IDs **except** `componentId`.
  3. Set `isolateState = { active: true, targetComponentId: componentId, preIsolateHidden }`.
- **Exit isolate** (isolate active AND same `componentId`, or any call while active):
  1. Restore `hiddenComponents` from `preIsolateHidden`.
  2. Reset `isolateState = { active: false, targetComponentId: null, preIsolateHidden: new Set() }`.
- Sync to sessionStorage.

#### `showAll()`
- Clear `hiddenComponents` to empty set.
- If isolate active: exit isolate (do **not** restore pre-isolate hidden; user explicitly wants all visible).
- Reset `isolateState`.
- Sync to sessionStorage.

### 1.4 sessionStorage Serialization

**Key format:** `"assembly-visibility:{assemblyId}"`

**Stored shape (JSON string):**
```typescript
interface PersistedVisibilityState {
  /** Schema version for forward compatibility */
  version: 1;
  /** Array of hidden component IDs */
  hidden: string[];
  /** Isolate mode if active */
  isolate: {
    active: boolean;
    targetComponentId: string | null;
    preIsolateHidden: string[];
  } | null;
}
```

**Write** (debounced 300 ms via `useEffect`):
```typescript
useEffect(() => {
  if (!assemblyId) return;
  const timer = setTimeout(() => {
    const payload: PersistedVisibilityState = {
      version: 1,
      hidden: Array.from(hiddenComponents),
      isolate: isolateState.active
        ? {
            active: true,
            targetComponentId: isolateState.targetComponentId,
            preIsolateHidden: Array.from(isolateState.preIsolateHidden),
          }
        : null,
    };
    sessionStorage.setItem(
      `assembly-visibility:${assemblyId}`,
      JSON.stringify(payload)
    );
  }, 300);
  return () => clearTimeout(timer);
}, [hiddenComponents, isolateState, assemblyId]);
```

**Read** (on mount, inside `useState` initializer or single `useEffect`):
```typescript
function loadPersistedState(assemblyId: string, componentIds: string[]): { ... } | null {
  try {
    const raw = sessionStorage.getItem(`assembly-visibility:${assemblyId}`);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    // Validate schema
    if (parsed?.version !== 1) return null;
    if (!Array.isArray(parsed.hidden)) return null;
    // Filter out stale IDs not in current assembly
    const validIds = new Set(componentIds);
    const hidden = parsed.hidden.filter(
      (id: unknown) => typeof id === 'string' && validIds.has(id)
    );
    // ... similarly validate isolate
    return { hidden: new Set(hidden), isolate: ... };
  } catch {
    // Corrupted data — clear and return null
    sessionStorage.removeItem(`assembly-visibility:${assemblyId}`);
    return null;
  }
}
```

### 1.5 Hook Implementation Skeleton

```typescript
export function useComponentVisibility({
  componentIds,
  assemblyId,
  externalHiddenComponents,
}: UseComponentVisibilityOptions): UseComponentVisibilityReturn {
  // If caller passes externalHiddenComponents, it's controlled mode
  // (backward compat for props-driven usage). Hook becomes read-only.
  const isControlled = externalHiddenComponents !== undefined;

  const [hiddenComponents, setHiddenComponents] = useState<Set<string>>(() => {
    if (isControlled) return externalHiddenComponents;
    if (assemblyId) {
      const persisted = loadPersistedState(assemblyId, componentIds);
      if (persisted) return persisted.hidden;
    }
    return new Set();
  });

  const [isolateState, setIsolateState] = useState<IsolateState>(() => {
    // Load from session if available
    return { active: false, targetComponentId: null, preIsolateHidden: new Set() };
  });

  // ... callbacks (toggleVisibility, toggleIsolate, showAll)
  // ... sessionStorage sync effect
  // ... derived values (hasHiddenComponents, hiddenCount)

  return { hiddenComponents, toggleVisibility, hideComponent, showComponent,
           toggleIsolate, showAll, isolateState, hasHiddenComponents, hiddenCount };
}
```

---

## 2. Component Integration Plan

### 2.1 `AssemblyViewer.tsx` Changes

**Code to remove** (lines ~313–327 in current file):
```tsx
// DELETE: local hidden state
const [localHiddenComponents, setLocalHiddenComponents] = useState<Set<string>>(new Set());

// DELETE: local toggle function
const toggleComponentVisibility = useCallback((componentId: string) => { ... }, []);

// DELETE: fallback line
const hiddenComponents = externalHiddenComponents ?? localHiddenComponents;
```

**Code to add:**
```tsx
import { useComponentVisibility } from '../../hooks/useComponentVisibility';

// Inside AssemblyViewer:
const visibility = useComponentVisibility({
  componentIds: components.map((c) => c.id),
  assemblyId,   // NEW optional prop
  externalHiddenComponents: externalHiddenComponents,
});

// Replace `hiddenComponents` references with `visibility.hiddenComponents`
// Replace `toggleComponentVisibility(id)` with `visibility.toggleVisibility(id)`
```

**New props on `AssemblyViewerProps`:**
```typescript
interface AssemblyViewerProps {
  // ... existing ...
  /** Assembly ID for session-persisted visibility state */
  assemblyId?: string;
}
```

### 2.2 `InteractiveAssemblyViewer.tsx` Changes

Identical pattern — remove duplicated `localHiddenComponents` / `toggleComponentVisibility` and replace with `useComponentVisibility` hook. This viewer already has a `useEffect` for keyboard shortcuts; extend it with visibility keys (see §2.3).

**Code to remove** (lines ~428–438 in current file):
```tsx
const [localHiddenComponents, setLocalHiddenComponents] = useState<Set<string>>(new Set());
// ... toggleComponentVisibility callback ...
const hiddenComponents = externalHiddenComponents ?? localHiddenComponents;
```

**Code to add:**
```tsx
const visibility = useComponentVisibility({
  componentIds: components.map(c => c.id),
  assemblyId,
  externalHiddenComponents,
});
```

### 2.3 Keyboard Shortcut Wiring

Add to the existing `useEffect` keydown handler in **both** viewers (InteractiveAssemblyViewer already has one; AssemblyViewer needs a new one):

```tsx
// H — toggle selected component visibility
if (e.key === 'h' && !e.ctrlKey && !e.metaKey && !e.shiftKey) {
  if (selectedComponentId) {
    e.preventDefault();
    visibility.toggleVisibility(selectedComponentId);
  }
}
// I — isolate selected component
else if (e.key === 'i' && !e.ctrlKey && !e.metaKey && !e.shiftKey) {
  if (selectedComponentId) {
    e.preventDefault();
    visibility.toggleIsolate(selectedComponentId);
  }
}
// Shift+H — show all
else if (e.key === 'H' && e.shiftKey && !e.ctrlKey && !e.metaKey) {
  e.preventDefault();
  visibility.showAll();
}
```

**Input guard:** both viewers already guard against `HTMLInputElement` / `HTMLTextAreaElement` targets — no change needed.

### 2.4 Prop Threading to `AssemblyPage.tsx`

`AssemblyPage` already has `assemblyId` from `useParams()`. Thread it down:

```tsx
<AssemblyViewer
  components={viewerComponents}
  selectedComponentId={selectedComponentId}
  onSelectComponent={setSelectedComponentId}
  assemblyId={assemblyId}   // ← ADD
/>
```

---

## 3. UI Component Changes

### 3.1 Component List Panel Header

Current header (identical in both viewers):
```tsx
<div className="px-4 py-3 border-b dark:border-gray-700 bg-gray-50 dark:bg-gray-700">
  <h3 className="font-medium text-gray-900 dark:text-gray-100">Components</h3>
</div>
```

**New header with action buttons:**
```tsx
<div className="px-4 py-3 border-b dark:border-gray-700 bg-gray-50 dark:bg-gray-700">
  <div className="flex items-center justify-between">
    <h3 className="font-medium text-gray-900 dark:text-gray-100">
      Components
      {visibility.isolateState.active && (
        <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">
          Isolated
        </span>
      )}
    </h3>
    <div className="flex items-center gap-1">
      {/* Isolate button */}
      <button
        onClick={() => selectedComponentId && visibility.toggleIsolate(selectedComponentId)}
        disabled={!selectedComponentId}
        className={`p-1 rounded transition-colors ${
          visibility.isolateState.active
            ? 'bg-amber-500 text-white'
            : selectedComponentId
              ? 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-200'
              : 'text-gray-300 dark:text-gray-600 cursor-not-allowed'
        }`}
        title={visibility.isolateState.active ? 'Exit isolate (I)' : 'Isolate selected (I)'}
      >
        <Focus className="w-4 h-4" />
      </button>
      {/* Show All button */}
      <button
        onClick={visibility.showAll}
        disabled={!visibility.hasHiddenComponents && !visibility.isolateState.active}
        className={`p-1 rounded transition-colors ${
          visibility.hasHiddenComponents || visibility.isolateState.active
            ? 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-200'
            : 'text-gray-300 dark:text-gray-600 cursor-not-allowed'
        }`}
        title="Show all (Shift+H)"
      >
        <EyeIcon className="w-4 h-4" />
      </button>
    </div>
  </div>
</div>
```

**New icon imports:**
```tsx
import { Focus } from 'lucide-react';  // for isolate
// Eye is already imported
```

### 3.2 Per-Row Eye Icon Enhancement

Current eye button per row remains unchanged. The only adjustment is swapping `toggleComponentVisibility` → `visibility.toggleVisibility`:

```tsx
<button
  onClick={(e) => {
    e.stopPropagation();
    visibility.toggleVisibility(component.id);
  }}
  disabled={visibility.isolateState.active}
  className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30 disabled:cursor-not-allowed"
>
  {visibility.hiddenComponents.has(component.id) ? (
    <EyeOff className="w-4 h-4" />
  ) : (
    <Eye className="w-4 h-4" />
  )}
</button>
```

Individual toggles are disabled during isolate mode to prevent confusing mixed state.

### 3.3 Status Bar Enhancement

Current component count badge already shows hidden count. Add isolate indicator:

```tsx
<div className="absolute bottom-4 left-4 bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm rounded-lg px-3 py-2 shadow-md">
  <span className="text-sm text-gray-600 dark:text-gray-300">
    {components.length} component{components.length !== 1 ? 's' : ''}
    {visibility.hiddenCount > 0 && ` (${visibility.hiddenCount} hidden)`}
    {visibility.isolateState.active && ' • Isolated'}
  </span>
</div>
```

### 3.4 Visual State Summary

| State | Isolate Button | Show All Button | Eye Toggles | Header Badge |
|---|---|---|---|---|
| Nothing selected | Disabled (gray) | Disabled (gray) | Enabled | None |
| Part selected, normal mode | Enabled (default) | Disabled (gray) | Enabled | None |
| Part selected, some hidden | Enabled (default) | Enabled (default) | Enabled | None |
| Isolate mode active | Active (amber bg) | Enabled | Disabled | "Isolated" badge |

---

## 4. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        AssemblyPage                             │
│  assemblyId (from useParams)                                    │
│  selectedComponentId (local state)                              │
│  components[] (fetched from API)                                │
│                                                                 │
│  ┌──────────────────────┐         ┌───────────────────────┐     │
│  │    AssemblyViewer     │   OR    │ InteractiveAssembly   │     │
│  │                       │         │      Viewer           │     │
│  │ ┌───────────────────┐ │         │ ┌───────────────────┐ │     │
│  │ │useComponentVisib- │ │         │ │useComponentVisib- │ │     │
│  │ │ility()            │ │         │ │ility()            │ │     │
│  │ │                   │ │         │ │                   │ │     │
│  │ │ hiddenComponents ─┼─┼────┐    │ │ hiddenComponents ─┼─┼──┐  │
│  │ │ isolateState     │ │    │    │ │ isolateState     │ │  │  │
│  │ │ toggleVisibility │ │    │    │ │ toggleVisibility │ │  │  │
│  │ │ toggleIsolate    │ │    │    │ │ toggleIsolate    │ │  │  │
│  │ │ showAll          │ │    │    │ │ showAll          │ │  │  │
│  │ └──────┬────────────┘ │    │    │ └──────┬────────────┘ │  │  │
│  │        │              │    │    │        │              │  │  │
│  │        │ sync (300ms) │    │    │        │ sync (300ms) │  │  │
│  │        ▼              │    │    │        ▼              │  │  │
│  │  sessionStorage      │    │    │  sessionStorage      │  │  │
│  │  "assembly-visibility│    │    │  "assembly-visibility│  │  │
│  │   :{assemblyId}"     │    │    │   :{assemblyId}"     │  │  │
│  └──────────────────────┘    │    └───────────────────────┘  │  │
│                              │                               │  │
│                              ▼                               ▼  │
│                     ┌──────────────────────┐                    │
│                     │   AssemblyScene        │                   │
│                     │   (R3F scene graph)    │                   │
│                     │                        │                   │
│                     │   components.map(c =>  │                   │
│                     │     <ComponentMesh     │                   │
│                     │       isHidden={       │                   │
│                     │         hidden.has(    │                   │
│                     │           c.id)}       │                   │
│                     │     />                 │                   │
│                     │   )                    │                   │
│                     └──────────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

### 4.1 Keyboard Event Flow

```
  window 'keydown' event
        │
        ▼
  useEffect listener (in viewer component)
        │
        ├── target is <input>/<textarea>? → ignore
        │
        ├── key === 'h' (no modifiers) && selectedComponentId?
        │       → visibility.toggleVisibility(selectedComponentId)
        │
        ├── key === 'i' (no modifiers) && selectedComponentId?
        │       → visibility.toggleIsolate(selectedComponentId)
        │
        ├── key === 'H' (Shift) ?
        │       → visibility.showAll()
        │
        └── (other keys handled by existing shortcuts)
```

### 4.2 sessionStorage Sync Flow

```
  State change (toggle/isolate/showAll)
        │
        ▼
  setState(new Set / new IsolateState)
        │
        ▼
  useEffect fires (deps: [hiddenComponents, isolateState])
        │
        ▼
  setTimeout 300ms (debounce)
        │
        ▼
  sessionStorage.setItem("assembly-visibility:{id}", JSON.stringify(...))


  Component mount (useState initializer)
        │
        ▼
  sessionStorage.getItem("assembly-visibility:{id}")
        │
        ├── null → empty Set
        │
        └── string → JSON.parse → validate → filter stale IDs → Set
```

---

## 5. Security Considerations

### 5.1 sessionStorage Data Validation

All data read from sessionStorage is **untrusted input**. The `loadPersistedState` function enforces:

| Check | Mitigation |
|---|---|
| JSON.parse failure | `try/catch` → clear key, return `null` |
| Missing `version` field | Reject if `version !== 1` |
| `hidden` is not an array | Reject, return `null` |
| Individual IDs not strings | Filter with `typeof id === 'string'` |
| IDs not in current assembly | Filter against `componentIds` set (prevents stale/injected IDs from leaking into state) |
| Isolate `targetComponentId` invalid | Validate against `componentIds`; if invalid, skip isolate restore |

**Corrupted state is never propagated** — on any validation failure the sessionStorage key is removed and the hook starts fresh.

### 5.2 XSS Concerns

- **Component IDs are UUIDs** generated server-side and never rendered as HTML. They are only used as `Set` keys and R3F `key` props — neither creates an injection vector.
- **sessionStorage is same-origin scoped.** A different origin cannot read or write the stored data.
- **No `dangerouslySetInnerHTML`** is used anywhere in the visibility UI. All text rendering uses React's JSX escaping.
- **The stored JSON is never eval'd** — only `JSON.parse` is used, which does not execute code.

### 5.3 No Sensitive Data

The stored payload contains:
- A schema version integer (`1`)
- An array of component ID strings (UUIDs)
- An isolate flag and target ID

**None of these are sensitive.** No user tokens, PII, or access credentials are stored. The data is scoped to the browser tab session and cleared when the tab closes (sessionStorage behavior).

### 5.4 Input Sanitization for `assemblyId`

The `assemblyId` is used as part of the sessionStorage key. To prevent key pollution:

```typescript
const ASSEMBLY_ID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function getSessionKey(assemblyId: string): string | null {
  if (!ASSEMBLY_ID_PATTERN.test(assemblyId)) return null;
  return `assembly-visibility:${assemblyId}`;
}
```

If the ID doesn't match UUID format, persistence is silently skipped — no error thrown, just no sessionStorage interaction.

### 5.5 Rate / Size Considerations

- sessionStorage has a ~5 MB per-origin limit. Each visibility entry is < 1 KB. Even 1000 assemblies would use < 1 MB.
- Debounce (300 ms) prevents excessive writes during rapid toggling.
- No network requests are made — this is entirely client-side.

---

## 6. File Change List

### New Files

| File | Description |
|---|---|
| `frontend/src/hooks/useComponentVisibility.ts` | New shared hook with all visibility/isolate/persist logic |
| `frontend/src/hooks/useComponentVisibility.test.ts` | Unit tests: toggle, isolate enter/exit, showAll, sessionStorage round-trip, validation, edge cases |

### Modified Files

| File | Changes |
|---|---|
| `frontend/src/components/assembly/AssemblyViewer.tsx` | Remove duplicated `localHiddenComponents` state + `toggleComponentVisibility` callback. Import and use `useComponentVisibility` hook. Add `assemblyId` prop. Add keyboard `useEffect` for `H`/`I`/`Shift+H`. Update component list panel header with Show All + Isolate buttons. Import `Focus` from lucide-react. |
| `frontend/src/components/assembly/InteractiveAssemblyViewer.tsx` | Same extraction as AssemblyViewer. Add `assemblyId` prop. Extend existing `keydown` handler with `H`/`I`/`Shift+H` cases. Update component list panel header with Show All + Isolate buttons. |
| `frontend/src/components/assembly/AssemblyViewer.test.tsx` | Add tests for: keyboard shortcut firing, Show All button, Isolate button disabled state, isolate badge rendering. |
| `frontend/src/components/assembly/InteractiveAssemblyViewer.test.tsx` | Mirror new tests from AssemblyViewer tests. |
| `frontend/src/pages/AssemblyPage.tsx` | Pass `assemblyId` prop to `<AssemblyViewer>`. |
| `frontend/src/components/assembly/index.ts` | No change needed (AssemblyViewer already exported). |

### Files NOT Changed

| File | Reason |
|---|---|
| Backend (`backend/**`) | Purely frontend feature |
| `frontend/src/types/*` | No new shared types needed; hook exports its own interfaces |
| `frontend/src/hooks/useKeyboardShortcuts.ts` | Not used — viewer-local `useEffect` is simpler and avoids coupling to the global shortcut system (these shortcuts are context-specific to the 3D viewer focus) |

---

## 7. Testing Strategy

### 7.1 `useComponentVisibility.test.ts` — Unit Tests

```
describe('useComponentVisibility')
  describe('toggleVisibility')
    ✓ hides a visible component
    ✓ shows a hidden component
    ✓ is a no-op when isolate is active
  describe('toggleIsolate')
    ✓ entering isolate hides all except target
    ✓ exiting isolate restores pre-isolate hidden set
    ✓ toggling same component exits isolate
    ✓ toggling different component switches isolate target
  describe('showAll')
    ✓ clears all hidden components
    ✓ exits isolate mode without restoring pre-isolate
    ✓ is idempotent when nothing is hidden
  describe('sessionStorage')
    ✓ persists hidden set on change
    ✓ restores hidden set on mount
    ✓ filters stale component IDs on restore
    ✓ handles corrupted JSON gracefully
    ✓ handles missing version field
    ✓ skips persistence when assemblyId is undefined
    ✓ rejects non-UUID assemblyId
  describe('derived state')
    ✓ hasHiddenComponents is true when set is non-empty
    ✓ hiddenCount reflects set size
```

### 7.2 Viewer Component Tests

Test keyboard shortcuts and button interactions via `fireEvent.keyDown(window, { key: 'h' })` and button clicks on the panel header actions. Validate that the mock hook functions are called with the correct arguments.

### 7.3 Testing Utilities

Use `renderHook` from `@testing-library/react` for hook unit tests. Mock `sessionStorage` with:
```typescript
const mockStorage: Record<string, string> = {};
vi.spyOn(Storage.prototype, 'getItem').mockImplementation((key) => mockStorage[key] ?? null);
vi.spyOn(Storage.prototype, 'setItem').mockImplementation((key, val) => { mockStorage[key] = val; });
vi.spyOn(Storage.prototype, 'removeItem').mockImplementation((key) => { delete mockStorage[key]; });
```

---

## 8. Migration / Backward Compatibility

- The `hiddenComponents` external prop on both viewers continues to work. When provided, the hook operates in **controlled mode** and defers to the external set (sessionStorage persistence is skipped in controlled mode).
- The `assemblyId` prop is optional. When omitted, the hook works identically to the current implementation but without persistence.
- No API changes, no database changes, no deployment considerations.
- Feature can be shipped behind no feature flag — it's additive behavior with no breaking changes.
