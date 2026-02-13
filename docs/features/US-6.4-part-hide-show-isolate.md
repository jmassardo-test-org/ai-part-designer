# US-6.4: Part Hide/Show/Isolate — Design Specification

**Issue:** GitHub #69  
**Story Points:** 2  
**Status:** Design Complete  
**Date:** 2026-02-13

---

## 1. User Stories & Acceptance Criteria

### Story 1: Toggle Individual Part Visibility

> **As a** designer viewing an assembly,  
> **I want to** hide and show individual parts from the component list,  
> **so that** I can focus on specific areas of the assembly without visual clutter.

**Acceptance Criteria:**

| # | Given | When | Then |
|---|-------|------|------|
| 1.1 | A component list panel is open with all parts visible | I click the Eye icon on a component row | That component disappears from the 3D scene and the icon changes to EyeOff |
| 1.2 | A component is hidden (EyeOff icon shown) | I click the EyeOff icon on that row | The component reappears in the scene and icon reverts to Eye |
| 1.3 | One or more components are hidden | I look at the status bar (bottom-left) | It displays `N of M components visible` |
| 1.4 | A component is selected and visible | I press `H` | The selected component is hidden and selection clears |
| 1.5 | No component is selected | I press `H` | Nothing happens (no-op) |

---

### Story 2: Isolate Selected Part

> **As a** designer inspecting a specific part,  
> **I want to** isolate a selected component so only it is visible,  
> **so that** I can examine it without other parts obstructing the view.

**Acceptance Criteria:**

| # | Given | When | Then |
|---|-------|------|------|
| 2.1 | A component is selected | I press `I` or click "Isolate" in the component list header | All other components are hidden; only the selected component remains visible |
| 2.2 | Isolate mode is active (one part visible) | I press `I` on a *different* selected component | The previous isolate target is hidden and the new selection becomes the sole visible component |
| 2.3 | No component is selected | I press `I` | Nothing happens (no-op) |
| 2.4 | Isolate mode is active | I press `I` on the *same* already-isolated component | Isolate mode exits — all components return to their pre-isolate visibility state |
| 2.5 | Isolate mode is active | The component list panel shows an "Isolated" badge beside the isolated component name | The badge is visible and clearly indicates isolate mode |

---

### Story 3: Show All Parts

> **As a** designer who has hidden several parts,  
> **I want to** restore all parts to visible in one action,  
> **so that** I can quickly return to a full assembly view.

**Acceptance Criteria:**

| # | Given | When | Then |
|---|-------|------|------|
| 3.1 | One or more components are hidden | I press `Shift+H` or click "Show All" button | All components become visible; `hiddenComponents` is cleared |
| 3.2 | Isolate mode is active | I press `Shift+H` or click "Show All" | Isolate mode exits and all components become visible |
| 3.3 | All components are already visible | I press `Shift+H` | No visible change (idempotent) |
| 3.4 | "Show All" button in the component list header | Components are all visible | The button is disabled/grayed to indicate no action needed |

---

### Story 4: Persist Visibility State

> **As a** designer returning to an assembly,  
> **I want** the hidden/shown state of components to be remembered within my session,  
> **so that** I don't lose my visibility setup when navigating away and back.

**Acceptance Criteria:**

| # | Given | When | Then |
|---|-------|------|------|
| 4.1 | I have hidden components in assembly `X` | I navigate to another page and return to assembly `X` | The previously hidden components are still hidden |
| 4.2 | I have a visibility state saved | The assembly's component list changes (component added/removed) | Stale entries are pruned; new components default to visible |
| 4.3 | Session storage is used | I close the browser tab and reopen | Visibility state resets to all-visible (session scope, not persistent) |

---

## 2. UI/UX Design Specifications

### 2.1 Component List Panel Enhancements

The existing component list panel (top-right overlay, 264px wide) is enhanced:

```
┌─────────────────────────────────┐
│ Components              [actions]│  ← Header row
│  [Show All] [Isolate Selected]  │  ← New action buttons row
├─────────────────────────────────┤
│ ● Motor Housing       ×2   👁   │  ← Existing row + eye toggle
│ ● Drive Shaft              👁   │
│ ● Bearing Assembly    ×4   👁̶   │  ← Hidden (EyeOff, dimmed row)
│ ● Cover Plate              👁   │
│   ISOLATED 🔒                   │  ← Badge when in isolate mode
└─────────────────────────────────┘
```

**Header row changes:**
- Add a sub-row below the "Components" heading with two small action buttons:
  - **Show All** (`EyeIcon` + text) — enabled only when `hiddenComponents.size > 0`
  - **Isolate** (`Focus` icon + text) — enabled only when `selectedComponentId !== null`
- Buttons use `text-xs` size, ghost style, within the existing header area

**Component row changes:**
- Hidden components: the entire row gets `opacity-50` styling
- In isolate mode: the isolated component row gets a small `"ISOLATED"` text badge in `text-primary-500`, positioned after the component name

### 2.2 Toolbar Addition

No new top-level toolbar buttons. The visibility controls live within the component list panel header. This keeps the left toolbar focused on spatial manipulation (move, rotate, explode, camera) and avoids toolbar bloat.

### 2.3 Status Bar (Bottom-Left) Enhancement

Currently displays: `5 components (2 hidden)`

Change to: `3 of 5 visible` when components are hidden, or just `5 components` when all are visible. In isolate mode, add: `3 of 5 visible · Isolated`

### 2.4 Keyboard Shortcuts

| Key | Action | Condition |
|-----|--------|-----------|
| `H` | Hide selected component | Requires selection; no modifier keys |
| `I` | Isolate selected / toggle isolate off | Requires selection; no modifier keys |
| `Shift+H` | Show all components | Always available |

These are registered in `InteractiveAssemblyViewer`'s existing `handleKeyDown` effect (alongside `G`, `R`, `S` shortcuts). They are **also** wired into the `useComponentVisibility` hook so both viewers can use them.

**Conflict check:** `H` and `I` are not used by existing shortcuts (`G`=translate, `R`=rotate, `S`=snap toggle, `Ctrl+Z`/`Ctrl+Y`=undo/redo). No conflicts.

### 2.5 Ghost / Transparency Mode (Nice-to-Have — Deferred)

**Out of scope for 2 SP.** Hidden parts currently `return null` (fully removed from scene). Implementing ghost/wireframe rendering requires material swapping and performance considerations. The current full-hide behavior is acceptable and matches user expectation. This can be a follow-up enhancement (US-6.4.1).

### 2.6 Context Menu (Nice-to-Have — Deferred)

**Out of scope for 2 SP.** Right-click context menu on 3D meshes would require a new `ContextMenu` component and `onContextMenu` event handling in the Canvas. Deferred to a separate story. The keyboard shortcuts and panel buttons provide sufficient interaction.

---

## 3. Interaction Patterns

### 3.1 Isolate Mode Behavior

Isolate mode is a **stateful toggle**, not a simple filter:

```
State: { isIsolateMode: boolean, isolatedComponentId: string | null, preIsolateHidden: Set<string> }
```

**Enter isolate:**
1. Save current `hiddenComponents` as `preIsolateHidden`
2. Set `hiddenComponents` = all component IDs **except** the selected one
3. Set `isIsolateMode = true`, `isolatedComponentId = selectedComponentId`

**Exit isolate (same component pressed again, or Show All):**
1. Restore `hiddenComponents` from `preIsolateHidden`
2. Set `isIsolateMode = false`, `isolatedComponentId = null`

**Switch isolate target (different component selected + `I`):**
1. Keep `preIsolateHidden` (original pre-isolate state)
2. Update `hiddenComponents` = all IDs except new selection
3. Update `isolatedComponentId` to new selection

### 3.2 Show All + Isolate Interaction

`Show All` **always exits isolate mode** and clears all hidden components. It does NOT restore `preIsolateHidden`. The mental model: "Show All = clean slate."

### 3.3 Hide During Isolate

If the user manually hides the isolated component (presses `H` while it's the sole visible part):
- The component is hidden → 0 visible components
- Isolate mode **auto-exits** (since the isolated target is now hidden)
- `preIsolateHidden` is discarded

### 3.4 Edge Cases

| Scenario | Behavior |
|----------|----------|
| Single-component assembly + Isolate | No-op (it's already the only one) |
| All components hidden + any click in scene | No selection possible; user must use Show All or toggle in panel |
| Component hidden + user clicks it in component list | Selects it (selection highlight on row) but does NOT auto-show it |
| Tab away and return | `sessionStorage` restores visibility state keyed by assembly ID |
| Assembly components change after persistence | Stale IDs in persisted set are ignored; new components default visible |

---

## 4. Technical Design

### 4.1 New Hook: `useComponentVisibility`

Extract shared visibility logic from both viewers into:

```
frontend/src/hooks/useComponentVisibility.ts
```

**Interface:**

```typescript
interface UseComponentVisibilityOptions {
  /** All component IDs in the assembly */
  componentIds: string[];
  /** Assembly ID for sessionStorage key */
  assemblyId?: string;
  /** Currently selected component ID */
  selectedComponentId: string | null;
  /** External hidden components (if controlled) */
  externalHiddenComponents?: Set<string>;
}

interface UseComponentVisibilityReturn {
  /** Set of currently hidden component IDs */
  hiddenComponents: Set<string>;
  /** Whether isolate mode is active */
  isIsolateMode: boolean;
  /** The isolated component ID (if in isolate mode) */
  isolatedComponentId: string | null;
  /** Toggle visibility of a single component */
  toggleVisibility: (componentId: string) => void;
  /** Hide the currently selected component */
  hideSelected: () => void;
  /** Isolate the currently selected component (or toggle off) */
  isolateSelected: () => void;
  /** Show all components and exit isolate mode */
  showAll: () => void;
  /** Number of visible components */
  visibleCount: number;
  /** Whether any components are hidden */
  hasHidden: boolean;
}
```

**Persistence:** Uses `sessionStorage` with key `assembly-visibility-${assemblyId}`. Serializes the `hiddenComponents` set as a JSON array. Reads on mount, writes on change (debounced 300ms). If no `assemblyId` is provided, persistence is skipped.

### 4.2 Integration Points

Both `AssemblyViewer` and `InteractiveAssemblyViewer` replace their inline `hiddenComponents` state and `toggleComponentVisibility` with this hook. The hook also registers keyboard shortcuts internally (using `useEffect` on `window.keydown`), gated by `ignoreInputs` checks matching the existing pattern.

### 4.3 Files to Create

| File | Purpose |
|------|---------|
| `frontend/src/hooks/useComponentVisibility.ts` | Shared visibility hook |
| `frontend/src/hooks/useComponentVisibility.test.ts` | Unit tests for the hook |

### 4.4 Files to Modify

| File | Changes |
|------|---------|
| `frontend/src/components/assembly/AssemblyViewer.tsx` | Replace inline visibility state with `useComponentVisibility`; add Show All / Isolate buttons to panel header; update status bar text |
| `frontend/src/components/assembly/InteractiveAssemblyViewer.tsx` | Same as above; add `H`, `I`, `Shift+H` to keyboard handler |
| `frontend/src/components/assembly/AssemblyViewer.test.tsx` | Add tests for new UI elements and keyboard interactions |
| `frontend/src/components/assembly/InteractiveAssemblyViewer.test.tsx` | Add tests for new UI elements and keyboard interactions |

---

## 5. Accessibility Requirements

| Requirement | Implementation |
|-------------|----------------|
| Eye toggle buttons have accessible labels | `aria-label="Hide {name}"` / `aria-label="Show {name}"` |
| Show All button labeled | `aria-label="Show all components"` |
| Isolate button labeled | `aria-label="Isolate selected component"` |
| Keyboard shortcuts are discoverable | Add shortcut hints to `title` attributes: `"Hide selected (H)"`, `"Isolate selected (I)"`, `"Show all (Shift+H)"` |
| Hidden component rows are distinguishable | `opacity-50` plus `aria-label` includes `"(hidden)"` suffix |
| Isolate mode announced | Status bar text updated to include "Isolated" — screen readers pick up `aria-live="polite"` on the status region |
| Focus management | Show All / Isolate buttons are focusable; keyboard shortcuts work when viewer has focus and no input is active |

---

## 6. Testing Strategy

### 6.1 Unit Tests — `useComponentVisibility` Hook

| Test Case | Category |
|-----------|----------|
| `toggleVisibility` adds/removes component IDs | Core |
| `hideSelected` hides selected component and is no-op when no selection | Core |
| `isolateSelected` hides all except selected | Core |
| `isolateSelected` toggles off when called on same component | Core |
| `isolateSelected` switches target when called on different component | Core |
| `showAll` clears hidden set and exits isolate mode | Core |
| `showAll` is idempotent when nothing is hidden | Edge |
| Hide during isolate auto-exits isolate mode | Edge |
| Persistence writes to sessionStorage on change | Persistence |
| Persistence reads from sessionStorage on mount | Persistence |
| Stale IDs in storage are pruned on mount | Persistence |
| No persistence when assemblyId is undefined | Persistence |

### 6.2 Component Tests — Viewer Updates

| Test Case | Component |
|-----------|-----------|
| Show All button renders in component list header | AssemblyViewer |
| Show All button is disabled when nothing is hidden | AssemblyViewer |
| Clicking Show All unhides all components | AssemblyViewer |
| Isolate button renders and is disabled without selection | AssemblyViewer |
| Clicking Isolate hides other components | InteractiveAssemblyViewer |
| Status bar shows "N of M visible" when parts hidden | Both |
| Status bar shows "Isolated" in isolate mode | Both |
| Eye toggle button has correct aria-label | Both |
| `H` key hides selected component | InteractiveAssemblyViewer |
| `I` key isolates selected component | InteractiveAssemblyViewer |
| `Shift+H` shows all | InteractiveAssemblyViewer |
| Keyboard shortcuts are no-op in input fields | InteractiveAssemblyViewer |

### 6.3 E2E Tests (Playwright — if time permits)

| Scenario |
|----------|
| Open assembly → hide component via panel → verify it disappears from canvas → show all → verify it reappears |
| Open assembly → select component → press `I` → verify only that component renders → press `Shift+H` → all visible |

### 6.4 Test Counts Estimate

- ~12 unit tests for `useComponentVisibility`
- ~10 component-level tests across both viewers
- ~2 E2E tests (stretch)

---

## 7. Scope Summary

| Item | In Scope | Notes |
|------|----------|-------|
| Per-part visibility toggle (eye icon) | ✅ | Already exists — enhance with hook extraction |
| Show All button | ✅ | New UI in component list panel header |
| Isolate mode | ✅ | New state + UI |
| Keyboard shortcuts (H, I, Shift+H) | ✅ | Added to viewer keydown handler |
| `useComponentVisibility` hook | ✅ | New shared hook |
| Session-scoped persistence | ✅ | sessionStorage |
| Ghost/transparent wireframe rendering | ❌ | Deferred — follow-up story |
| Right-click context menu | ❌ | Deferred — follow-up story |
| Backend model changes | ❌ | Not needed — frontend-only feature |
