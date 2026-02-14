# US-6.2 & US-6.3: Part Alignment/Snap Tools & Exploded View Mode — Design Specification

**Issues:** GitHub #71 (US-6.2), GitHub #72 (US-6.3)  
**Story Points:** 3 SP each (6 SP total)  
**Status:** Design Complete  
**Date:** 2026-02-13

---

## Table of Contents

1. [US-6.2: Part Alignment/Snap Tools](#us-62-part-alignmentsnap-tools)
   - [User Stories & Acceptance Criteria](#1-user-stories--acceptance-criteria-us-62)
   - [UI/UX Design Specifications](#2-uiux-design-specifications-us-62)
   - [Interaction Design](#3-interaction-design-us-62)
   - [Component Specifications](#4-component-specifications-us-62)
2. [US-6.3: Exploded View Mode](#us-63-exploded-view-mode)
   - [User Stories & Acceptance Criteria](#5-user-stories--acceptance-criteria-us-63)
   - [UI/UX Design Specifications](#6-uiux-design-specifications-us-63)
   - [Interaction Design](#7-interaction-design-us-63)
   - [Component Specifications](#8-component-specifications-us-63)
3. [Shared Non-Functional Requirements](#9-non-functional-requirements)
4. [Implementation Summary](#10-implementation-summary)

---

# US-6.2: Part Alignment/Snap Tools

## 1. User Stories & Acceptance Criteria (US-6.2)

### Story 1: Snap to Grid During Movement

> **As a** designer moving parts in the 3D viewer,  
> **I want** parts to snap to a grid when I drag them,  
> **so that** I can position parts at precise increments without manual coordinate entry.

**Acceptance Criteria:**

| # | Given | When | Then |
|---|-------|------|------|
| 1.1 | Snapping is enabled (default) and a part is selected in translate mode | I drag the part | The part position snaps to the nearest grid increment (default 5 units) |
| 1.2 | Snapping is enabled | I hold `Alt` while dragging | Snapping is temporarily disabled (free movement) |
| 1.3 | Snapping is disabled via toggle | I drag the part | The part moves freely without snapping |
| 1.4 | Part is snapping to grid | I look at the 3D scene | Faint grid lines appear on the ground plane to visualize snap points |

**Edge Cases:**

- Parts at assembly boundaries should snap to the nearest valid grid point
- Very small parts should still respect snap increments (no minimum size threshold)
- When multiple parts are selected (future), all should snap together maintaining relative positions

---

### Story 2: Snap to Alignment Guides (Edges/Centers/Faces)

> **As a** designer aligning one part to another,  
> **I want** visual alignment guides to appear when edges, centers, or faces align,  
> **so that** I can precisely position parts relative to each other.

**Acceptance Criteria:**

| # | Given | When | Then |
|---|-------|------|------|
| 2.1 | A part is being dragged | The part's center approaches another part's center (within threshold) | A center alignment guide line appears connecting the centers |
| 2.2 | A part is being dragged | The part's edge aligns with another part's edge (within threshold) | An edge alignment guide line appears along the aligned edge |
| 2.3 | A part is being dragged | The part's face is coplanar with another part's face (within threshold) | A face alignment guide (plane highlight) appears |
| 2.4 | Alignment guide is visible and within snap threshold | I release the mouse | The part snaps to the exact aligned position |
| 2.5 | Multiple alignment guides are active | I look at the scene | All relevant guides are displayed simultaneously with distinct visual treatment |
| 2.6 | A part is being dragged | The part moves away from alignment | Guides fade out smoothly |

**Edge Cases:**

- Alignment guides should not appear for hidden components
- Guides should consider the current transform of both source and target parts
- Maximum 6 guides shown simultaneously (prioritize closest alignments)

---

### Story 3: Alignment Tool in Toolbar

> **As a** designer,  
> **I want** an alignment tool button in the toolbar,  
> **so that** I can toggle alignment guides and configure snap behavior.

**Acceptance Criteria:**

| # | Given | When | Then |
|---|-------|------|------|
| 3.1 | Toolbar is visible | I look at the view controls section | I see an alignment tool button (Magnet icon) |
| 3.2 | Alignment guides are enabled (default) | I click the alignment button | A popover appears with alignment options |
| 3.3 | Alignment popover is open | I toggle "Edge alignment" off | Edge guides no longer appear during drag |
| 3.4 | Alignment popover is open | I adjust "Snap distance" slider | The snap threshold changes immediately |
| 3.5 | I press `A` key | No input is focused | Alignment guides toggle on/off |

**Edge Cases:**

- Popover should close when clicking outside
- Settings should persist within the session
- Alignment tool state should be reflected in status bar hints

---

### Story 4: Visual Guides During Movement

> **As a** designer moving parts,  
> **I want** clear visual feedback showing potential snap points and alignments,  
> **so that** I understand where the part will land before releasing.

**Acceptance Criteria:**

| # | Given | When | Then |
|---|-------|------|------|
| 4.1 | Part is being dragged with snapping enabled | I drag near a snap point | A "ghost" preview shows where the part will snap to |
| 4.2 | Part is approaching alignment | Guides appear | Guides animate in (fade + scale) over 150ms |
| 4.3 | Part snaps to position | The snap occurs | A subtle pulse animation (scale 1.0 → 1.02 → 1.0) confirms the snap |
| 4.4 | Multiple alignment options exist | I drag between them | The nearest alignment is highlighted more prominently |

**Edge Cases:**

- Guides should not obstruct the view of the part being moved
- High-contrast mode should be supported (thicker/brighter guides)
- Guides should work correctly when camera is at extreme angles

---

## 2. UI/UX Design Specifications (US-6.2)

### 2.1 Toolbar Layout

The alignment tool is added to the existing "View controls" button group in the left toolbar:

```
┌─────────────────────────────────────────────────
│ Transform Mode Group    │
│ ┌─────┐                 │
│ │ Move│  ← G key        │
│ └─────┘                 │
│ ┌─────┐                 │
│ │ Rot │  ← R key        │
│ └─────┘                 │
├─────────────────────────│
│ Undo/Redo Group         │
│ ┌─────┐                 │
│ │Undo │  ← Ctrl+Z       │
│ └─────┘                 │
│ ┌─────┐                 │
│ │Redo │  ← Ctrl+Y       │
│ └─────┘                 │
├─────────────────────────│
│ View Controls Group     │
│ ┌─────┐                 │
│ │Grid │  ← S key (existing snap toggle)
│ └─────┘                 │
│ ┌─────┐                 │
│ │Align│  ← A key (NEW)  │  ← Magnet icon
│ └─────┘                 │
│ ┌─────┐                 │
│ │Explode│ ← E key       │
│ └─────┘                 │
│ ┌─────┐                 │
│ │Reset│  ← Camera reset │
│ └─────┘                 │
│ ┌─────┐                 │
│ │List │  ← Component list
│ └─────┘                 │
└─────────────────────────┘
```

### 2.2 Alignment Tool Button

**Icon:** `Magnet` from lucide-react  
**States:**
- **Default (guides enabled):** `bg-primary-600 text-white`
- **Disabled (guides off):** `text-gray-700 dark:text-gray-300 hover:bg-gray-100`
- **Hover:** Standard hover state per existing buttons

**Tooltip:** `Alignment Guides (A)`

### 2.3 Alignment Popover

When clicking the Magnet button, a popover appears:

```
┌─────────────────────────────────────┐
│ Alignment Guides                    │
├─────────────────────────────────────┤
│ ☑ Edge alignment                    │
│ ☑ Center alignment                  │
│ ☑ Face alignment                    │
├─────────────────────────────────────┤
│ Snap Distance                       │
│ ◀━━━━━━━●━━━━━━━▶  10 units        │
│   (range: 2-30, default: 10)        │
├─────────────────────────────────────┤
│ Grid Snap Increment                 │
│ ◀━━●━━━━━━━━━━━━▶  5 units         │
│   (range: 1-25, default: 5)         │
└─────────────────────────────────────┘
```

**Popover Specs:**
- Width: 240px
- Background: `bg-white dark:bg-gray-800`
- Border radius: 8px (rounded-lg)
- Shadow: `shadow-lg`
- Position: Right of button, vertically centered

### 2.4 Visual Guide Appearance

#### Edge Alignment Guide
- **Type:** Line
- **Color:** `#22c55e` (green-500) with 80% opacity
- **Width:** 2px (rendered via THREE.Line2 for consistent width)
- **Style:** Dashed (dash: 8px, gap: 4px)
- **Length:** Extends 20 units beyond both parts

#### Center Alignment Guide
- **Type:** Line connecting part centers
- **Color:** `#3b82f6` (blue-500) with 80% opacity
- **Width:** 2px
- **Style:** Solid
- **Endpoint markers:** Small spheres (radius 2) at each center

#### Face Alignment Guide
- **Type:** Plane highlight
- **Color:** `#f59e0b` (amber-500) with 20% opacity
- **Border:** Solid line around plane edge, 2px, amber-500 at 60% opacity
- **Size:** Matches the aligned face bounds + 10% padding

#### Snap Point Indicator
- **Type:** Small crosshair or plus icon
- **Color:** `#ef4444` (red-500) with 70% opacity
- **Size:** 6x6 units
- **Animation:** Gentle pulse when active (opacity 0.5 → 0.8)

### 2.5 Keyboard Shortcuts

| Key | Action | Condition |
|-----|--------|-----------|
| `A` | Toggle alignment guides on/off | No input focused |
| `Alt` (hold) | Temporarily disable snapping | While dragging |
| `Shift` (hold) | Constrain to single axis | While dragging |

---

## 3. Interaction Design (US-6.2)

### 3.1 Alignment Guide Appearance During Drag

**Detection Algorithm:**

1. On each frame during drag:
   - Calculate the bounding box of the dragged part at current position
   - For each visible (non-hidden) part:
     - Calculate distance between centers
     - Calculate distance between all 6 faces (near/far on each axis)
     - Calculate edge distances (12 edges per box = 144 comparisons, optimized)
   - Filter alignments within `snapDistance` threshold
   - Sort by distance, keep top 6
   - Render guides for remaining alignments

2. **Performance Optimization:**
   - Use spatial hash grid for O(1) neighbor lookup
   - Only check parts within `snapDistance * 2` radius
   - Cache bounding boxes, update only on transform

**Visual Guide Lifecycle:**

```
[Not aligned] ─── drag enters threshold ──→ [Guide fades in 150ms]
      ↑                                              │
      │                                              ▼
      └──── drag exits threshold ──────────── [Guide fades out 100ms]
```

### 3.2 Snap-To Behavior

**Threshold-Based Snapping:**

1. **Soft threshold (visual):** 10 units (default) — guides appear
2. **Hard threshold (snap):** 5 units — position snaps when released

**Snap Priority (highest to lowest):**
1. Face alignment (most useful for assembly)
2. Center alignment
3. Edge alignment
4. Grid snap

**Snap Execution:**
1. On mouse release, check if any alignment is within hard threshold
2. If yes, animate part to aligned position over 100ms (ease-out)
3. Fire `onTransformEnd` with final snapped position
4. Show snap confirmation animation (pulse)

### 3.3 Multi-Axis Constraint

When `Shift` is held:
- Detect primary axis of drag direction
- Constrain movement to that axis only
- Show axis indicator line through part center

---

## 4. Component Specifications (US-6.2)

### 4.1 New Components

#### `AlignmentGuides.tsx`

**Location:** `frontend/src/components/assembly/AlignmentGuides.tsx`

```typescript
export interface AlignmentGuide {
  id: string;
  type: 'edge' | 'center' | 'face';
  sourcePartId: string;
  targetPartId: string;
  axis: 'x' | 'y' | 'z';
  position: THREE.Vector3;
  // For edge/center: line endpoints
  startPoint?: THREE.Vector3;
  endPoint?: THREE.Vector3;
  // For face: plane definition
  planeNormal?: THREE.Vector3;
  planeSize?: { width: number; height: number };
  // Visual state
  strength: number; // 0-1, based on distance to threshold
}

export interface AlignmentGuidesProps {
  guides: AlignmentGuide[];
  visible: boolean;
  fadeIn?: boolean;
}

export function AlignmentGuides({ guides, visible, fadeIn }: AlignmentGuidesProps): JSX.Element;
```

#### `useAlignmentGuides.ts`

**Location:** `frontend/src/hooks/useAlignmentGuides.ts`

```typescript
export interface AlignmentSettings {
  enableEdgeAlignment: boolean;
  enableCenterAlignment: boolean;
  enableFaceAlignment: boolean;
  snapDistance: number;      // Visual threshold (default: 10)
  snapThreshold: number;     // Snap execution threshold (default: 5)
  maxGuides: number;         // Max simultaneous guides (default: 6)
}

export interface UseAlignmentGuidesOptions {
  /** All parts in the assembly (for calculating alignments). */
  parts: AssemblyComponent[];
  /** Currently dragged part ID (null if not dragging). */
  draggedPartId: string | null;
  /** Current position of dragged part. */
  dragPosition: THREE.Vector3 | null;
  /** Set of hidden part IDs (excluded from alignment). */
  hiddenParts: Set<string>;
  /** Alignment configuration. */
  settings: AlignmentSettings;
  /** Current part transforms (for accurate bounding boxes). */
  transforms: PartTransformState;
}

export interface UseAlignmentGuidesReturn {
  /** Active alignment guides to render. */
  guides: AlignmentGuide[];
  /** Suggested snap position if within threshold (null otherwise). */
  snapPosition: THREE.Vector3 | null;
  /** Whether any alignment is active. */
  hasActiveAlignment: boolean;
  /** Calculate final snap position on release. */
  calculateSnapPosition: (releasePosition: THREE.Vector3) => THREE.Vector3;
}

export function useAlignmentGuides(options: UseAlignmentGuidesOptions): UseAlignmentGuidesReturn;
```

#### `AlignmentToolbar.tsx`

**Location:** `frontend/src/components/assembly/AlignmentToolbar.tsx`

```typescript
export interface AlignmentToolbarProps {
  enabled: boolean;
  onToggle: () => void;
  settings: AlignmentSettings;
  onSettingsChange: (settings: Partial<AlignmentSettings>) => void;
}

export function AlignmentToolbar({
  enabled,
  onToggle,
  settings,
  onSettingsChange,
}: AlignmentToolbarProps): JSX.Element;
```

### 4.2 Modified Components

#### `InteractiveAssemblyViewer.tsx`

**Changes:**
1. Add `alignmentEnabled` state (default: `true`)
2. Add `alignmentSettings` state
3. Integrate `useAlignmentGuides` hook
4. Render `AlignmentGuides` component in scene
5. Add `AlignmentToolbar` to toolbar
6. Add `A` key handler to keyboard shortcuts
7. Modify `handleTransformEnd` to use snap position from alignment hook
8. Pass `draggedPartId` and `dragPosition` to alignment hook during transform

**New state:**
```typescript
const [alignmentEnabled, setAlignmentEnabled] = useState(true);
const [alignmentSettings, setAlignmentSettings] = useState<AlignmentSettings>({
  enableEdgeAlignment: true,
  enableCenterAlignment: true,
  enableFaceAlignment: true,
  snapDistance: 10,
  snapThreshold: 5,
  maxGuides: 6,
});
```

#### `PartTransformControls.tsx`

**Changes:**
1. Add `onDragPositionChange?: (position: THREE.Vector3) => void` prop
2. Emit drag position on each frame during transform (for alignment calculation)
3. Add `snapToPosition?: THREE.Vector3` prop to override final position

### 4.3 New Tests Required

| File | Test Cases |
|------|------------|
| `useAlignmentGuides.test.ts` | Detects center alignment within threshold |
| | Detects edge alignment within threshold |
| | Detects face alignment within threshold |
| | Respects hidden parts (excludes from calculation) |
| | Returns null snapPosition when outside threshold |
| | Prioritizes closest alignments |
| | Limits to maxGuides simultaneously |
| | Settings toggles disable specific guide types |
| `AlignmentGuides.test.tsx` | Renders edge guide correctly |
| | Renders center guide correctly |
| | Renders face guide correctly |
| | Applies correct colors per guide type |
| | Handles fade in/out transitions |
| `AlignmentToolbar.test.tsx` | Renders magnet button |
| | Opens popover on click |
| | Toggle checkboxes update settings |
| | Slider changes snap distance |
| `InteractiveAssemblyViewer.test.tsx` | A key toggles alignment |
| | Alignment guides appear during drag |
| | Part snaps to aligned position on release |

---

# US-6.3: Exploded View Mode

## 5. User Stories & Acceptance Criteria (US-6.3)

### Story 1: Animated Explosion Transition

> **As a** designer toggling exploded view,  
> **I want** parts to animate smoothly to their exploded positions,  
> **so that** the spatial relationship between parts is clear during the transition.

**Acceptance Criteria:**

| # | Given | When | Then |
|---|-------|------|------|
| 1.1 | Assembly is in normal view | I click the explode button or press `E` | Parts animate outward from assembly center over 500ms |
| 1.2 | Assembly is in exploded view | I click the explode button or press `E` | Parts animate back to original positions over 400ms |
| 1.3 | Animation is in progress | I look at the parts | Each part moves along a vector from assembly center through its position |
| 1.4 | Animation is in progress | I interact with the scene (rotate camera) | Animation continues uninterrupted |
| 1.5 | Animation is in progress | I click explode again | Animation reverses smoothly from current position |

**Edge Cases:**

- Parts at assembly center should still move outward (use fallback direction)
- Very large assemblies (50+ parts) should use staggered animation
- Hidden parts should not animate (maintain hidden state)

---

### Story 2: Adjustable Explosion Distance

> **As a** designer,  
> **I want** to control how far apart the parts spread,  
> **so that** I can see internal components at various levels of detail.

**Acceptance Criteria:**

| # | Given | When | Then |
|---|-------|------|------|
| 2.1 | Exploded view is active | I look at the toolbar | I see a distance slider/control |
| 2.2 | Distance slider is visible | I drag the slider | Parts smoothly animate to new positions in real-time |
| 2.3 | Distance is at minimum (0.5x) | Parts are slightly separated | I can still see part relationships |
| 2.4 | Distance is at maximum (3x) | Parts are widely spread | All internal parts are fully visible |
| 2.5 | I adjust distance | I release the slider | The new distance is persisted for this session |

**Edge Cases:**

- Distance changes should animate, not jump
- Keyboard users should be able to adjust via arrow keys when slider focused
- Touch users should be able to drag the slider easily

---

### Story 3: Explosion Direction Vectors

> **As a** designer,  
> **I want** parts to explode in logical directions based on assembly structure,  
> **so that** the exploded view maintains spatial understanding.

**Acceptance Criteria:**

| # | Given | When | Then |
|---|-------|------|------|
| 3.1 | Exploded view is triggered | Parts move | Each part moves radially outward from assembly centroid |
| 3.2 | A part is at the assembly center | It explodes | It moves along a default axis (positive Y/up) |
| 3.3 | Multiple parts share similar positions | They explode | They move in slightly offset directions to remain distinguishable |
| 3.4 | Part has custom explosion vector (future) | Explosion occurs | Part follows its custom vector instead of radial |

**Edge Cases:**

- Parts with zero-distance from center get fallback direction
- Overlapping parts separate to avoid collision
- Very far parts (outliers) use reduced explosion factor

---

### Story 4: Exploded View Toolbar Enhancement

> **As a** designer,  
> **I want** an enhanced explode control in the toolbar,  
> **so that** I can easily toggle and adjust the exploded view.

**Acceptance Criteria:**

| # | Given | When | Then |
|---|-------|------|------|
| 4.1 | Toolbar is visible | I see the explode button | Button shows Expand icon (normal) or Shrink icon (exploded) |
| 4.2 | Exploded view is off | I click the explode button | Exploded view activates with animation |
| 4.3 | Exploded view is on | I click the expand arrow on the button | Distance slider appears in popover |
| 4.4 | I press `E` key | Assembly is visible | Exploded view toggles |
| 4.5 | Popover is open | I click outside | Popover closes, current distance is saved |

**Edge Cases:**

- Button should be disabled during animation (prevent spamming)
- Mobile: long-press opens popover instead of double-tap

---

## 6. UI/UX Design Specifications (US-6.3)

### 6.1 Enhanced Explode Button

The existing explode button is enhanced with a popover for distance control:

**Button Appearance:**
- **Icon:** `Expand` (lucide-react) when collapsed, `Shrink` when exploded
- **Dropdown indicator:** Small chevron-down on the right side of button
- **Active state:** `bg-primary-600 text-white` when exploded

**Button Layout:**
```
┌─────────────────┐
│ [↔] [▼]        │  ← Icon + dropdown arrow
└─────────────────┘
   │
   ▼ (on dropdown click)
┌─────────────────────────────────┐
│ Explosion Distance              │
│ ◀━━━━━━━●━━━━━━━━━━▶  1.5x     │
│   Min 0.5x        Max 3.0x     │
├─────────────────────────────────┤
│ [Toggle Exploded View]          │  ← Alternative toggle button
└─────────────────────────────────┘
```

### 6.2 Distance Slider Specifications

**Slider Properties:**
- **Min value:** 0.5 (half of default explosion)
- **Max value:** 3.0 (triple the default explosion)
- **Default:** 1.0
- **Step:** 0.1
- **Width:** 200px
- **Track color:** `bg-gray-200 dark:bg-gray-600`
- **Fill color:** `bg-primary-500`
- **Thumb:** 16px circle, `bg-white border-2 border-primary-500`

**Value Display:**
- Shown to the right of slider: `1.5x`
- Updates in real-time as slider moves

### 6.3 Animation Specifications

#### Explosion Animation

| Property | Value |
|----------|-------|
| Duration (expand) | 500ms |
| Duration (collapse) | 400ms |
| Easing | `easeOutCubic` (fast start, slow end) |
| Stagger (large assemblies) | 20ms between parts (start in order from center) |

**Easing Function:**
```typescript
function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}
```

#### Slider Adjustment Animation

| Property | Value |
|----------|-------|
| Duration | 200ms |
| Easing | `easeOutQuad` |
| Trigger | On slider change (throttled to 60fps) |

### 6.4 Keyboard Shortcuts

| Key | Action | Condition |
|-----|--------|-----------|
| `E` | Toggle exploded view | No input focused |
| `Shift+E` | Open explosion distance popover | No input focused |
| `←`/`→` | Adjust distance by 0.1 | Slider focused |
| `Shift+←`/`Shift+→` | Adjust distance by 0.5 | Slider focused |

### 6.5 Explosion Vector Calculation

**Algorithm:**
```
1. Calculate assembly centroid:
   centroid = sum(part.position) / count(parts)

2. For each part:
   a. direction = normalize(part.position - centroid)
   b. If direction magnitude < 0.001:
      direction = Vector3(0, 1, 0) // Default up
   c. If duplicate direction (within 5°):
      Rotate direction by 15° around Y axis
   
3. Calculate exploded position:
   explodedPos = originalPos + (direction * explodeFactor * BASE_DISTANCE)
   where BASE_DISTANCE = 50 units
```

**Visual Representation:**

```
        Normal View                    Exploded View (1.0x)
        
            ┌───┐                           ┌───┐
            │ C │                           │ C │    ↗
            └───┘                           └───┘
         ┌───┬───┐                    ┌───┐     ┌───┐
         │ A │ B │        →           │ A │     │ B │
         └───┴───┘                    └───┘ ↙   └───┘ ↘
            │                               
         ┌──┴──┐                          ┌───┐
         │  D  │                          │ D │  ↓
         └─────┘                          └───┘
```

---

## 7. Interaction Design (US-6.3)

### 7.1 Explosion Animation Flow

```
┌────────────────────────────────────────────────────────────────────┐
│                       EXPLOSION STATE MACHINE                       │
└────────────────────────────────────────────────────────────────────┘

     ┌───────────┐      click/E key      ┌─────────────┐
     │ COLLAPSED │ ─────────────────────→│ EXPLODING   │
     │ factor=0  │                       │ 0 → target  │
     └───────────┘                       └──────┬──────┘
           ↑                                    │
           │         animation complete         │
           │         ┌─────────────────────────┘
           │         ↓
           │    ┌──────────┐
           │    │ EXPLODED │ ←──── slider adjusts target
           │    │ factor=X │       (animates to new target)
           │    └────┬─────┘
           │         │
           │   click/E key
           │         │
           │         ↓
           │   ┌─────────────┐
           └───│ COLLAPSING  │
               │ X → 0       │
               └─────────────┘
```

### 7.2 Real-Time Distance Adjustment

When the slider value changes during exploded view:

1. **Throttle input** to 60fps (16.67ms minimum between updates)
2. **Calculate new positions** for all visible parts
3. **Interpolate** from current position to new target over 200ms
4. **If user continues dragging**, interrupt interpolation and jump to new target
5. **When slider released**, ensure final animation completes

### 7.3 Touch Interaction

**Mobile/Tablet:**
- **Tap explode button:** Toggle exploded view
- **Long press (500ms):** Open distance popover
- **Swipe on slider:** Adjust distance
- **Pinch (future):** Alternative way to adjust explosion distance

### 7.4 Interruption Handling

| Current State | User Action | Behavior |
|---------------|-------------|----------|
| Exploding (0 → 1) | Click explode | Reverse from current position |
| Collapsing (1 → 0) | Click explode | Reverse from current position |
| Exploding | Adjust slider | Complete explosion, then animate to new factor |
| Exploded, slider animating | Toggle off | Immediate collapse animation |

---

## 8. Component Specifications (US-6.3)

### 8.1 New Components

#### `useExplodedView.ts`

**Location:** `frontend/src/hooks/useExplodedView.ts`

```typescript
export type ExplodeState = 'collapsed' | 'exploding' | 'exploded' | 'collapsing';

export interface ExplosionVector {
  partId: string;
  direction: THREE.Vector3;
  distance: number;
}

export interface UseExplodedViewOptions {
  /** Component positions (used to calculate centroid and vectors). */
  components: AssemblyComponent[];
  /** Current part transforms (to get actual positions). */
  transforms: PartTransformState;
  /** Hidden component IDs (excluded from centroid calculation). */
  hiddenComponents: Set<string>;
  /** Animation duration for expand (ms). */
  expandDuration?: number;
  /** Animation duration for collapse (ms). */
  collapseDuration?: number;
  /** Callback when explosion state changes. */
  onStateChange?: (state: ExplodeState) => void;
}

export interface UseExplodedViewReturn {
  /** Current explosion state. */
  state: ExplodeState;
  /** Current explosion factor (0-1 animated, can exceed 1 with distance multiplier). */
  factor: number;
  /** Current distance multiplier (0.5 - 3.0). */
  distanceMultiplier: number;
  /** Computed explosion vectors for each part. */
  explosionVectors: ExplosionVector[];
  /** Whether currently animating. */
  isAnimating: boolean;
  /** Toggle exploded view. */
  toggle: () => void;
  /** Set distance multiplier (animates to new value). */
  setDistanceMultiplier: (multiplier: number) => void;
  /** Get exploded position for a specific part. */
  getExplodedPosition: (partId: string, originalPosition: THREE.Vector3) => THREE.Vector3;
  /** Assembly centroid (for reference). */
  centroid: THREE.Vector3;
}

export function useExplodedView(options: UseExplodedViewOptions): UseExplodedViewReturn;
```

#### `ExplodeToolbar.tsx`

**Location:** `frontend/src/components/assembly/ExplodeToolbar.tsx`

```typescript
export interface ExplodeToolbarProps {
  /** Current explosion state. */
  state: ExplodeState;
  /** Whether animating. */
  isAnimating: boolean;
  /** Current distance multiplier. */
  distanceMultiplier: number;
  /** Callback to toggle exploded view. */
  onToggle: () => void;
  /** Callback when distance multiplier changes. */
  onDistanceChange: (multiplier: number) => void;
}

export function ExplodeToolbar({
  state,
  isAnimating,
  distanceMultiplier,
  onToggle,
  onDistanceChange,
}: ExplodeToolbarProps): JSX.Element;
```

#### `ExplosionLinesOverlay.tsx` (Optional Enhancement)

**Location:** `frontend/src/components/assembly/ExplosionLinesOverlay.tsx`

```typescript
export interface ExplosionLinesOverlayProps {
  /** Whether to show explosion direction lines. */
  visible: boolean;
  /** Centroid position. */
  centroid: THREE.Vector3;
  /** Part positions and their explosion vectors. */
  partVectors: Array<{
    partId: string;
    position: THREE.Vector3;
    direction: THREE.Vector3;
  }>;
}

/**
 * Renders dashed lines from centroid to each part showing explosion direction.
 * Visible only during exploded view.
 */
export function ExplosionLinesOverlay(props: ExplosionLinesOverlayProps): JSX.Element;
```

### 8.2 Modified Components

#### `InteractiveAssemblyViewer.tsx`

**Changes:**
1. Replace simple `explodeFactor` state with `useExplodedView` hook
2. Replace existing explode button with `ExplodeToolbar`
3. Add `E` key handler for toggle
4. Add `Shift+E` handler for popover
5. Update `ComponentMesh` to use animated positions from hook
6. Optionally render `ExplosionLinesOverlay`

**Updated state/hooks:**
```typescript
// Remove:
const [localExplodeFactor, setLocalExplodeFactor] = useState(0);

// Add:
const explodedView = useExplodedView({
  components,
  transforms: partTransforms.transforms,
  hiddenComponents,
  expandDuration: 500,
  collapseDuration: 400,
});
```

#### `ComponentMesh` (in InteractiveAssemblyViewer.tsx)

**Changes:**
1. Use `getExplodedPosition` from hook instead of direct calculation
2. Remove local `explodedPosition` useMemo
3. Accept `explodedPosition: THREE.Vector3` as prop

#### `AssemblyViewer.tsx`

**Changes:**
1. Apply same `useExplodedView` integration for consistency
2. Can use simplified version without toolbar controls (view-only)

### 8.3 Animation Utilities

#### `useAnimatedValue.ts`

**Location:** `frontend/src/hooks/useAnimatedValue.ts`

```typescript
export interface UseAnimatedValueOptions {
  /** Initial value. */
  initialValue: number;
  /** Animation duration in ms. */
  duration?: number;
  /** Easing function. */
  easing?: (t: number) => number;
  /** Callback when animation completes. */
  onComplete?: () => void;
}

export interface UseAnimatedValueReturn {
  /** Current animated value. */
  value: number;
  /** Target value. */
  targetValue: number;
  /** Whether currently animating. */
  isAnimating: boolean;
  /** Set new target (animates to it). */
  setTarget: (target: number) => void;
  /** Immediately set value without animation. */
  setValue: (value: number) => void;
}

export function useAnimatedValue(options: UseAnimatedValueOptions): UseAnimatedValueReturn;
```

**Easing presets to export:**
```typescript
export const easings = {
  linear: (t: number) => t,
  easeOutQuad: (t: number) => 1 - (1 - t) ** 2,
  easeOutCubic: (t: number) => 1 - (1 - t) ** 3,
  easeInOutCubic: (t: number) => 
    t < 0.5 ? 4 * t ** 3 : 1 - (-2 * t + 2) ** 3 / 2,
};
```

### 8.4 New Tests Required

| File | Test Cases |
|------|------------|
| `useExplodedView.test.ts` | Initial state is collapsed with factor 0 |
| | toggle() transitions to exploding state |
| | Animation completes and enters exploded state |
| | Second toggle() transitions to collapsing |
| | Calculates correct centroid from components |
| | Generates valid explosion vectors for all parts |
| | Parts at center get fallback direction |
| | setDistanceMultiplier updates factor |
| | Hidden components excluded from centroid |
| | getExplodedPosition returns correct values |
| `useAnimatedValue.test.ts` | Animates from initial to target |
| | Respects duration parameter |
| | Applies easing function correctly |
| | setValue immediately updates without animation |
| | Interrupt mid-animation works correctly |
| | onComplete fires after animation |
| `ExplodeToolbar.test.tsx` | Renders toggle button with correct icon |
| | Button click triggers onToggle |
| | Renders slider in popover |
| | Slider change triggers onDistanceChange |
| | Button disabled during animation |
| `InteractiveAssemblyViewer.test.tsx` | E key toggles exploded view |
| | Parts animate on explosion toggle |
| | Distance slider adjusts part positions |

---

# 9. Non-Functional Requirements

## 9.1 Performance

### Alignment Guides (US-6.2)

| Metric | Requirement |
|--------|-------------|
| Guide calculation | < 16ms for 50 parts (60fps) |
| Guide rendering | Max 6 simultaneous guides |
| Memory | < 5MB additional for alignment data structures |
| Spatial indexing | Required for assemblies > 20 parts |

**Optimization Strategies:**
1. Use spatial hash grid (cell size = snap distance)
2. Only calculate guides for parts within 2x snap distance
3. Cache bounding boxes per part (invalidate on transform)
4. Skip hidden parts entirely
5. Debounce guide calculation during rapid mouse movement

### Exploded View (US-6.3)

| Metric | Requirement |
|--------|-------------|
| Animation frame rate | 60fps minimum |
| Explosion calculation | < 5ms for 100 parts |
| Slider responsiveness | < 50ms perceived latency |
| Memory | No additional allocations during animation |

**Optimization Strategies:**
1. Pre-calculate explosion vectors on toggle (not per frame)
2. Use shader-based animation where possible
3. Throttle slider input to 60fps
4. Use object pooling for Vector3 instances

## 9.2 Accessibility

### Alignment Guides

| Requirement | Implementation |
|-------------|----------------|
| Screen reader announcement | Announce "Edge alignment available" when guide appears |
| High contrast mode | Guide colors should pass 4.5:1 contrast ratio |
| Keyboard alternative | Tab to part, use arrow keys with Shift for constrained movement |
| Focus indicators | Selected alignment shows visual focus ring |

### Exploded View

| Requirement | Implementation |
|-------------|----------------|
| Screen reader announcement | Announce "Exploded view activated" / "collapsed" |
| Motion sensitivity | Respect `prefers-reduced-motion` — instant transitions |
| Keyboard control | E key toggle, arrow keys for distance when focused |
| Slider accessibility | Proper ARIA labels, role="slider", aria-valuenow |

**Reduced Motion Implementation:**
```typescript
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const actualDuration = prefersReducedMotion ? 0 : duration;
```

## 9.3 Browser Compatibility

| Browser | Version | Support Level |
|---------|---------|---------------|
| Chrome | 90+ | Full |
| Firefox | 88+ | Full |
| Safari | 14+ | Full |
| Edge | 90+ | Full |
| Mobile Safari | 14+ | Full (touch) |
| Chrome Android | 90+ | Full (touch) |

**WebGL Requirements:**
- WebGL 2.0 required (all target browsers support)
- Line2 for consistent line width (drei dependency)
- No fragment shader complexity limits expected

## 9.4 Error Handling

### Alignment Guides

| Error Scenario | Handling |
|----------------|----------|
| Invalid part geometry | Skip part in alignment calculation |
| NaN in position | Log warning, use zero vector |
| Calculation timeout | Abort and show no guides for this frame |

### Exploded View

| Error Scenario | Handling |
|----------------|----------|
| Zero-length explosion vector | Use default up vector (0, 1, 0) |
| Animation frame drop | Skip to next keyframe |
| Invalid distance multiplier | Clamp to valid range (0.5-3.0) |

---

# 10. Implementation Summary

## 10.1 File Changes Matrix

| File Path | US-6.2 | US-6.3 | Change Type |
|-----------|--------|--------|-------------|
| `frontend/src/hooks/useAlignmentGuides.ts` | ✅ | | New |
| `frontend/src/hooks/useAlignmentGuides.test.ts` | ✅ | | New |
| `frontend/src/hooks/useExplodedView.ts` | | ✅ | New |
| `frontend/src/hooks/useExplodedView.test.ts` | | ✅ | New |
| `frontend/src/hooks/useAnimatedValue.ts` | | ✅ | New |
| `frontend/src/hooks/useAnimatedValue.test.ts` | | ✅ | New |
| `frontend/src/components/assembly/AlignmentGuides.tsx` | ✅ | | New |
| `frontend/src/components/assembly/AlignmentGuides.test.tsx` | ✅ | | New |
| `frontend/src/components/assembly/AlignmentToolbar.tsx` | ✅ | | New |
| `frontend/src/components/assembly/AlignmentToolbar.test.tsx` | ✅ | | New |
| `frontend/src/components/assembly/ExplodeToolbar.tsx` | | ✅ | New |
| `frontend/src/components/assembly/ExplodeToolbar.test.tsx` | | ✅ | New |
| `frontend/src/components/assembly/InteractiveAssemblyViewer.tsx` | ✅ | ✅ | Modify |
| `frontend/src/components/assembly/InteractiveAssemblyViewer.test.tsx` | ✅ | ✅ | Modify |
| `frontend/src/components/assembly/AssemblyViewer.tsx` | | ✅ | Modify |
| `frontend/src/components/assembly/AssemblyViewer.test.tsx` | | ✅ | Modify |
| `frontend/src/components/viewer/PartTransformControls.tsx` | ✅ | | Modify |
| `frontend/src/components/assembly/index.ts` | ✅ | ✅ | Modify |

## 10.2 Implementation Order

**Phase 1: Foundation (US-6.3 - Exploded View)**
1. `useAnimatedValue` hook
2. `useExplodedView` hook
3. `ExplodeToolbar` component
4. Integrate into `InteractiveAssemblyViewer`
5. Tests

**Phase 2: Alignment System (US-6.2)**
1. `useAlignmentGuides` hook
2. `AlignmentGuides` Three.js component
3. `AlignmentToolbar` component
4. Integrate into `InteractiveAssemblyViewer`
5. Update `PartTransformControls`
6. Tests

## 10.3 Definition of Done

- [ ] All acceptance criteria verified
- [ ] Unit tests passing (≥80% coverage)
- [ ] E2E tests for critical paths
- [ ] Accessibility audit passed
- [ ] Performance benchmarks met
- [ ] Code review approved
- [ ] Documentation updated
- [ ] No console errors or warnings

---

## Appendix A: Keyboard Shortcuts Summary

| Key | US-6.2 (Alignment) | US-6.3 (Explode) | Existing |
|-----|-------------------|------------------|----------|
| `G` | | | Move mode |
| `R` | | | Rotate mode |
| `S` | | | Toggle grid snap |
| `H` | | | Hide selected |
| `Shift+H` | | | Show all |
| `I` | | | Isolate selected |
| `A` | Toggle alignment guides | | |
| `Alt` (hold) | Disable snap while dragging | | |
| `Shift` (hold) | Constrain to axis | | |
| `E` | | Toggle exploded view | |
| `Shift+E` | | Open distance popover | |
| `Ctrl+Z` | | | Undo |
| `Ctrl+Y` | | | Redo |

---

## Appendix B: Color Palette Reference

| Element | Light Theme | Dark Theme | Opacity |
|---------|-------------|------------|---------|
| Edge alignment guide | `#22c55e` | `#22c55e` | 80% |
| Center alignment guide | `#3b82f6` | `#3b82f6` | 80% |
| Face alignment guide | `#f59e0b` | `#f59e0b` | 20% fill, 60% border |
| Snap point indicator | `#ef4444` | `#ef4444` | 70% |
| Explosion line | `#9ca3af` | `#6b7280` | 50% |
| Active button | `bg-primary-600` | `bg-primary-600` | 100% |

---

*End of Design Specification*
