# US-6.2 & US-6.3: Technical Architecture Document

**Features:** Part Alignment/Snap Tools (US-6.2), Exploded View Mode (US-6.3)  
**Status:** Architecture Complete  
**Date:** 2026-02-13  
**Author:** Architecture & Security Agent

---

## Table of Contents

1. [Component Architecture](#1-component-architecture)
2. [State Management Design](#2-state-management-design)
3. [Performance Architecture](#3-performance-architecture)
4. [Integration Points](#4-integration-points)
5. [Testing Architecture](#5-testing-architecture)
6. [Security Considerations](#6-security-considerations)
7. [Technical Specifications](#7-technical-specifications)

---

## 1. Component Architecture

### 1.1 React Component Tree

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      InteractiveAssemblyViewer (Smart)                       │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                           <Canvas>                                     │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │  │
│  │  │                    AssemblyScene (Smart)                          │ │  │
│  │  │                                                                   │ │  │
│  │  │  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐   │ │  │
│  │  │  │ ComponentMesh  │  │ ComponentMesh  │  │  ComponentMesh   │   │ │  │
│  │  │  │ (Presentational)│  │ (Presentational)│  │ (Presentational) │   │ │  │
│  │  │  └────────────────┘  └────────────────┘  └──────────────────┘   │ │  │
│  │  │                                                                   │ │  │
│  │  │  ┌─────────────────────────┐  ┌────────────────────────────┐    │ │  │
│  │  │  │ PartTransformControls   │  │   AlignmentGuides (NEW)     │    │ │  │
│  │  │  │ (Smart - drei wrapper)  │  │   (Presentational)          │    │ │  │
│  │  │  └─────────────────────────┘  └────────────────────────────┘    │ │  │
│  │  │                                                                   │ │  │
│  │  │  ┌────────────────────────────┐                                  │ │  │
│  │  │  │ ExplosionLinesOverlay (NEW)│ (Optional, Presentational)       │ │  │
│  │  │  └────────────────────────────┘                                  │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                           UI Overlay                                   │  │
│  │                                                                        │  │
│  │  ┌─────────────────┐  ┌──────────────────┐  ┌───────────────────────┐ │  │
│  │  │  MainToolbar    │  │ AlignmentToolbar │  │    ExplodeToolbar     │ │  │
│  │  │  (Existing)     │  │ (NEW - Smart)    │  │    (NEW - Smart)      │ │  │
│  │  │                 │  │                  │  │                       │ │  │
│  │  │ ┌─Move──────┐   │  │ ┌──Popover────┐  │  │ ┌───Popover────────┐  │ │  │
│  │  │ │ Rotate    │   │  │ │ Checkboxes  │  │  │ │ Distance Slider  │  │ │  │
│  │  │ │ Undo/Redo │   │  │ │ Sliders     │  │  │ │                  │  │ │  │
│  │  │ │ Snap      │   │  │ └─────────────┘  │  │ └──────────────────┘  │ │  │
│  │  │ └───────────┘   │  └──────────────────┘  └───────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Component Classification

| Component | Type | Responsibilities |
|-----------|------|------------------|
| `InteractiveAssemblyViewer` | **Smart** | State orchestration, hook composition, keyboard handlers |
| `AssemblyScene` | **Smart** | Scene management, Three.js context, transform handling |
| `ComponentMesh` | **Presentational** | Render single part mesh with props-driven position |
| `PartTransformControls` | **Smart** | Drei wrapper, snapping logic, drag events |
| `AlignmentGuides` (NEW) | **Presentational** | Render guide lines/planes from `guides` prop |
| `AlignmentToolbar` (NEW) | **Smart** | Popover state, settings form, keyboard toggle |
| `ExplodeToolbar` (NEW) | **Smart** | Popover state, slider interaction, animation control |
| `ExplosionLinesOverlay` (NEW) | **Presentational** | Render dashed lines from centroid to parts |

### 1.3 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA FLOW (Props ↓, Callbacks ↑)                    │
└─────────────────────────────────────────────────────────────────────────────┘

                     ┌───────────────────────────────────┐
                     │    InteractiveAssemblyViewer      │
                     │                                   │
                     │  State:                           │
                     │  ├─ alignmentEnabled              │
                     │  ├─ alignmentSettings             │
                     │  ├─ draggedPartId                 │
                     │  └─ dragPosition                  │
                     │                                   │
                     │  Hooks:                           │
                     │  ├─ usePartTransforms()           │
                     │  ├─ useComponentVisibility()      │
                     │  ├─ useAlignmentGuides() (NEW)    │
                     │  └─ useExplodedView() (NEW)       │
                     └────────────┬──────────────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
          ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│ AssemblyScene   │    │ AlignmentToolbar    │    │ ExplodeToolbar      │
│                 │    │                     │    │                     │
│ Props ↓:        │    │ Props ↓:            │    │ Props ↓:            │
│ ├─ components   │    │ ├─ enabled          │    │ ├─ state            │
│ ├─ transforms   │    │ ├─ settings         │    │ ├─ isAnimating      │
│ ├─ explodedPositions │    │                     │    │ ├─ distanceMultiplier
│ ├─ guides       │    │ Callbacks ↑:        │    │                     │
│ └─ snapPosition │    │ ├─ onToggle         │    │ Callbacks ↑:        │
│                 │    │ └─ onSettingsChange │    │ ├─ onToggle         │
│ Callbacks ↑:    │    └─────────────────────┘    │ └─ onDistanceChange │
│ ├─ onDragStart  │                               └─────────────────────┘
│ ├─ onDragMove   │
│ └─ onDragEnd    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Child Components                                │
├────────────────────┬────────────────────┬────────────────────────────────────┤
│ ComponentMesh      │ AlignmentGuides    │ PartTransformControls             │
│ (×N parts)         │                    │                                   │
│                    │                    │                                   │
│ Props:             │ Props:             │ Props (extended):                 │
│ ├─ explodedPosition│ ├─ guides[]        │ ├─ onDragPositionChange (NEW)     │
│ ├─ isHidden        │ ├─ visible         │ └─ snapToPosition (NEW)           │
│ └─ transform       │ └─ fadeIn          │                                   │
└────────────────────┴────────────────────┴────────────────────────────────────┘
```

---

## 2. State Management Design

### 2.1 State Location Strategy

| State | Location | Reason |
|-------|----------|--------|
| `alignmentEnabled` | Local (`useState`) | UI toggle, no external consumers |
| `alignmentSettings` | Local (`useState`) | Session-scoped, persisted via sessionStorage |
| `draggedPartId` | Local (`useState`) | Transient drag state |
| `dragPosition` | Local (`useRef`) | High-frequency updates (60fps), no re-render needed |
| `guides[]` | Derived (hook return) | Computed from drag position + settings |
| `explodeState` | Hook-managed (`useExplodedView`) | Complex state machine with animation |
| `explosionVectors` | Derived (hook return) | Computed once on toggle |
| `transforms` | External hook (`usePartTransforms`) | Shared with undo/redo system |
| `hiddenComponents` | External hook (`useComponentVisibility`) | Shared with component list |

### 2.2 Alignment State Shape

```typescript
// ─────────────────────────────────────────────────────────────────────────────
// ALIGNMENT STATE (US-6.2)
// ─────────────────────────────────────────────────────────────────────────────

interface AlignmentState {
  // UI State
  enabled: boolean;                    // Master toggle (A key)
  popoverOpen: boolean;                // Toolbar popover visibility
  
  // Settings (persisted to sessionStorage)
  settings: AlignmentSettings;
  
  // Runtime State (transient)
  draggedPartId: string | null;        // Currently dragging part
  dragPosition: THREE.Vector3 | null;  // Current drag position (in ref)
  
  // Derived/Computed (from useAlignmentGuides hook)
  activeGuides: AlignmentGuide[];      // Currently visible guides (max 6)
  snapPosition: THREE.Vector3 | null;  // Suggested snap target
  hasActiveAlignment: boolean;         // Any guide within threshold
}

interface AlignmentSettings {
  enableEdgeAlignment: boolean;        // Default: true
  enableCenterAlignment: boolean;      // Default: true
  enableFaceAlignment: boolean;        // Default: true
  snapDistance: number;                // Visual threshold (default: 10)
  snapThreshold: number;               // Execution threshold (default: 5)
  gridSnapIncrement: number;           // Grid snap size (default: 5)
  maxGuides: number;                   // Limit (default: 6)
}

interface AlignmentGuide {
  id: string;                          // Unique ID for React key
  type: 'edge' | 'center' | 'face';
  sourcePartId: string;                // Part being dragged
  targetPartId: string;                // Part aligned to
  axis: 'x' | 'y' | 'z';
  position: THREE.Vector3;             // Guide position in world space
  startPoint?: THREE.Vector3;          // Line start (edge/center)
  endPoint?: THREE.Vector3;            // Line end (edge/center)
  planeNormal?: THREE.Vector3;         // Face alignment plane normal
  planeSize?: { width: number; height: number };
  strength: number;                    // 0-1, for opacity/thickness
  distance: number;                    // Distance to alignment (for sorting)
}
```

### 2.3 Exploded View State Shape

```typescript
// ─────────────────────────────────────────────────────────────────────────────
// EXPLODED VIEW STATE (US-6.3)
// ─────────────────────────────────────────────────────────────────────────────

type ExplodeState = 'collapsed' | 'exploding' | 'exploded' | 'collapsing';

interface ExplodedViewState {
  // State Machine
  state: ExplodeState;                 // Current animation state
  
  // Animation Values
  factor: number;                      // Current animated factor (0-1)
  targetFactor: number;                // Target factor (0 or 1)
  distanceMultiplier: number;          // User-controlled multiplier (0.5-3.0)
  
  // Computed Geometry
  centroid: THREE.Vector3;             // Assembly center point
  explosionVectors: ExplosionVector[]; // Pre-computed per-part vectors
  
  // Animation State
  isAnimating: boolean;                // Currently animating
  animationStartTime: number | null;   // For frame interpolation
  animationDuration: number;           // Current animation duration
}

interface ExplosionVector {
  partId: string;
  direction: THREE.Vector3;            // Normalized direction from centroid
  baseDistance: number;                // Distance to move at factor=1
  originalPosition: THREE.Vector3;     // Position before explosion
}

// Animation durations (respects prefers-reduced-motion)
const EXPAND_DURATION = 500;           // ms
const COLLAPSE_DURATION = 400;         // ms
const SLIDER_ADJUST_DURATION = 200;    // ms
```

### 2.4 State Flow Between Hooks

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           HOOK COMPOSITION FLOW                              │
└─────────────────────────────────────────────────────────────────────────────┘

InteractiveAssemblyViewer
        │
        ├─► usePartTransforms()
        │       │
        │       └─► Returns: transforms, updateTransform, undo, redo
        │                           │
        ├─► useComponentVisibility()│
        │       │                   │
        │       └─► Returns: hiddenComponents, toggleVisibility
        │                           │
        │           ┌───────────────┘
        │           ▼
        ├─► useExplodedView({
        │       components,
        │       transforms,          ◄── From usePartTransforms
        │       hiddenComponents,    ◄── From useComponentVisibility
        │   })
        │       │
        │       └─► Returns: state, factor, distanceMultiplier,
        │                    getExplodedPosition, toggle
        │                           │
        │           ┌───────────────┘
        │           ▼
        └─► useAlignmentGuides({
                parts,
                draggedPartId,       ◄── From local state
                dragPosition,        ◄── From PartTransformControls callback
                hiddenParts,         ◄── From useComponentVisibility
                transforms,          ◄── From usePartTransforms
                settings,            ◄── From local alignment state
            })
                │
                └─► Returns: guides, snapPosition, calculateSnapPosition
```

---

## 3. Performance Architecture

### 3.1 Spatial Hash Grid for Alignment (US-6.2)

The spatial hash grid enables O(1) lookup of nearby parts for alignment calculation.

```typescript
// ─────────────────────────────────────────────────────────────────────────────
// SPATIAL HASH GRID IMPLEMENTATION
// ─────────────────────────────────────────────────────────────────────────────

interface SpatialHashGrid<T> {
  cellSize: number;
  cells: Map<string, T[]>;
}

/**
 * Hash function: converts 3D position to cell key.
 * Cell size should be >= snapDistance for efficient lookups.
 */
function positionToCell(pos: THREE.Vector3, cellSize: number): string {
  const x = Math.floor(pos.x / cellSize);
  const y = Math.floor(pos.y / cellSize);
  const z = Math.floor(pos.z / cellSize);
  return `${x},${y},${z}`;
}

/**
 * Get all cells within radius of a position.
 * For snapDistance=10, cellSize=10: checks 27 cells (3³)
 */
function getCellsInRadius(
  pos: THREE.Vector3,
  radius: number,
  cellSize: number
): string[] {
  const cells: string[] = [];
  const cellRadius = Math.ceil(radius / cellSize);
  
  const cx = Math.floor(pos.x / cellSize);
  const cy = Math.floor(pos.y / cellSize);
  const cz = Math.floor(pos.z / cellSize);
  
  for (let x = cx - cellRadius; x <= cx + cellRadius; x++) {
    for (let y = cy - cellRadius; y <= cy + cellRadius; y++) {
      for (let z = cz - cellRadius; z <= cz + cellRadius; z++) {
        cells.push(`${x},${y},${z}`);
      }
    }
  }
  return cells;
}

// Usage in useAlignmentGuides hook:
class PartSpatialIndex {
  private grid: SpatialHashGrid<string>;  // Maps cell -> partId[]
  private boundingBoxes: Map<string, THREE.Box3>;
  
  constructor(cellSize: number = 20) {
    this.grid = { cellSize, cells: new Map() };
    this.boundingBoxes = new Map();
  }
  
  /**
   * Rebuild index when parts change.
   * Called once on mount and when parts array changes.
   */
  rebuild(parts: Part[], transforms: PartTransformState): void {
    this.grid.cells.clear();
    this.boundingBoxes.clear();
    
    for (const part of parts) {
      const transform = transforms[part.id];
      const position = transform?.position ?? part.position;
      const pos = new THREE.Vector3(position.x, position.y, position.z);
      
      // Calculate and cache bounding box
      const bbox = this.calculateBoundingBox(part, transform);
      this.boundingBoxes.set(part.id, bbox);
      
      // Insert into grid
      const cellKey = positionToCell(pos, this.grid.cellSize);
      const cell = this.grid.cells.get(cellKey) || [];
      cell.push(part.id);
      this.grid.cells.set(cellKey, cell);
    }
  }
  
  /**
   * Get candidate parts for alignment check.
   * O(1) lookup + O(k) where k = parts in nearby cells.
   */
  getNearbyParts(position: THREE.Vector3, radius: number): string[] {
    const cells = getCellsInRadius(position, radius, this.grid.cellSize);
    const candidates = new Set<string>();
    
    for (const cellKey of cells) {
      const cell = this.grid.cells.get(cellKey);
      if (cell) {
        cell.forEach(id => candidates.add(id));
      }
    }
    
    return Array.from(candidates);
  }
  
  getBoundingBox(partId: string): THREE.Box3 | undefined {
    return this.boundingBoxes.get(partId);
  }
}
```

### 3.2 Memoization Strategy

```typescript
// ─────────────────────────────────────────────────────────────────────────────
// MEMOIZATION GUIDELINES
// ─────────────────────────────────────────────────────────────────────────────

// ✅ USE useMemo FOR:
// 1. Expensive geometry calculations
// 2. Large array transformations
// 3. Creating THREE.js objects that shouldn't be recreated

// In AssemblyScene:
const assemblyCenter = useMemo(() => {
  // Only recalculate when components or transforms change
  const center = new THREE.Vector3();
  components.forEach(c => {
    const pos = transforms[c.id]?.position ?? c.position;
    center.add(new THREE.Vector3(pos.x, pos.y, pos.z));
  });
  return center.divideScalar(components.length);
}, [components, transforms]);

// In useExplodedView:
const explosionVectors = useMemo(() => {
  // Only recalculate when components change (not on every factor change)
  return components.map(c => calculateExplosionVector(c, centroid));
}, [components, centroid]);

// ✅ USE useCallback FOR:
// 1. Event handlers passed to children
// 2. Functions referenced in useEffect dependencies
// 3. Callbacks that would cause child re-renders

// In InteractiveAssemblyViewer:
const handleDragPositionChange = useCallback((position: THREE.Vector3) => {
  // Update ref (no re-render) for high-frequency updates
  dragPositionRef.current = position;
  // Trigger alignment calculation (throttled internally)
  calculateAlignments();
}, [calculateAlignments]);

// ❌ AVOID useMemo/useCallback FOR:
// 1. Simple calculations (overhead > benefit)
// 2. Primitive values
// 3. Objects that change every render anyway

// ❌ Bad - unnecessary memoization
const isHidden = useMemo(() => 
  hiddenComponents.has(part.id), 
  [hiddenComponents, part.id]
); // Just inline this!

// ✅ Good - inline simple checks
const isHidden = hiddenComponents.has(part.id);
```

### 3.3 Animation Frame Budget Allocation

```typescript
// ─────────────────────────────────────────────────────────────────────────────
// FRAME BUDGET: 16.67ms at 60fps
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Frame time budget allocation:
 * 
 * ┌────────────────────────────────────────────────────────────────┐
 * │                     16.67ms FRAME BUDGET                       │
 * ├────────────────────┬───────────────────────────────────────────┤
 * │ Three.js Render    │  8-10ms (fixed, R3F managed)              │
 * ├────────────────────┼───────────────────────────────────────────┤
 * │ React Reconcile    │  2-3ms (minimal updates during animation) │
 * ├────────────────────┼───────────────────────────────────────────┤
 * │ Alignment Calc     │  2-3ms (US-6.2) - spatial hash critical   │
 * ├────────────────────┼───────────────────────────────────────────┤
 * │ Explosion Interp   │  <1ms (US-6.3) - pre-computed vectors     │
 * ├────────────────────┼───────────────────────────────────────────┤
 * │ Buffer             │  2-3ms (GC, browser, fluctuation)         │
 * └────────────────────┴───────────────────────────────────────────┘
 */

// Alignment calculation budget enforcement
const MAX_ALIGNMENT_CALC_TIME = 3; // ms

function calculateAlignmentsWithBudget(
  draggedPart: Part,
  candidateParts: Part[],
  settings: AlignmentSettings,
  startTime: number
): AlignmentGuide[] {
  const guides: AlignmentGuide[] = [];
  
  for (const targetPart of candidateParts) {
    // Check time budget
    if (performance.now() - startTime > MAX_ALIGNMENT_CALC_TIME) {
      console.warn('Alignment calculation exceeded budget, returning partial results');
      break;
    }
    
    // Calculate alignments for this pair
    const pairGuides = calculatePairAlignments(draggedPart, targetPart, settings);
    guides.push(...pairGuides);
  }
  
  // Sort by distance, keep top N
  return guides
    .sort((a, b) => a.distance - b.distance)
    .slice(0, settings.maxGuides);
}

// Explosion interpolation - O(n) but with pre-computed vectors
function interpolateExplosion(
  vectors: ExplosionVector[],
  factor: number,
  distanceMultiplier: number
): Map<string, THREE.Vector3> {
  const positions = new Map<string, THREE.Vector3>();
  
  // Simple linear interpolation - ~0.01ms per part
  for (const vec of vectors) {
    const offset = vec.direction
      .clone()
      .multiplyScalar(vec.baseDistance * factor * distanceMultiplier);
    positions.set(vec.partId, vec.originalPosition.clone().add(offset));
  }
  
  return positions;
}
```

### 3.4 React Three Fiber Optimizations

```typescript
// ─────────────────────────────────────────────────────────────────────────────
// R3F PERFORMANCE PATTERNS
// ─────────────────────────────────────────────────────────────────────────────

// 1. Use refs for high-frequency updates (not state)
function AlignmentGuides({ guides }: { guides: AlignmentGuide[] }) {
  const linesRef = useRef<THREE.Group>(null);
  
  // Update line positions directly, no React re-render
  useFrame(() => {
    if (!linesRef.current) return;
    // Direct Three.js manipulation...
  });
  
  return <group ref={linesRef}>{/* ... */}</group>;
}

// 2. Use instancedMesh for many similar objects
function SnapPointIndicators({ points }: { points: THREE.Vector3[] }) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const tempMatrix = useMemo(() => new THREE.Matrix4(), []);
  
  useEffect(() => {
    if (!meshRef.current) return;
    
    points.forEach((point, i) => {
      tempMatrix.setPosition(point);
      meshRef.current!.setMatrixAt(i, tempMatrix);
    });
    meshRef.current.instanceMatrix.needsUpdate = true;
  }, [points, tempMatrix]);
  
  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, points.length]}>
      <sphereGeometry args={[2, 8, 8]} />
      <meshBasicMaterial color="#ef4444" transparent opacity={0.7} />
    </instancedMesh>
  );
}

// 3. Dispose geometries and materials properly
function ComponentMesh({ geometry }: { geometry: THREE.BufferGeometry }) {
  useEffect(() => {
    return () => {
      geometry.dispose(); // Clean up on unmount
    };
  }, [geometry]);
  // ...
}

// 4. Use suspense boundaries for async loading
function AssemblyScene() {
  return (
    <Suspense fallback={<LoadingIndicator />}>
      <AsyncComponentMeshes />
    </Suspense>
  );
}
```

---

## 4. Integration Points

### 4.1 Integration with InteractiveAssemblyViewer

```typescript
// ─────────────────────────────────────────────────────────────────────────────
// INTEGRATION CHANGES TO InteractiveAssemblyViewer.tsx
// ─────────────────────────────────────────────────────────────────────────────

export function InteractiveAssemblyViewer({
  components,
  selectedComponentId,
  // ... existing props
}: InteractiveAssemblyViewerProps) {
  // ═══════════════════════════════════════════════════════════════════════════
  // EXISTING HOOKS (unchanged)
  // ═══════════════════════════════════════════════════════════════════════════
  const {
    hiddenComponents,
    // ... existing visibility hook
  } = useComponentVisibility({ componentIds, assemblyId });

  const partTransforms = usePartTransforms({
    onTransformUpdate: onComponentTransform,
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // NEW: Alignment State & Hook (US-6.2)
  // ═══════════════════════════════════════════════════════════════════════════
  const [alignmentEnabled, setAlignmentEnabled] = useState(true);
  const [alignmentSettings, setAlignmentSettings] = useState<AlignmentSettings>(
    loadAlignmentSettings() // From sessionStorage or defaults
  );
  
  // Drag state for alignment calculation
  const [draggedPartId, setDraggedPartId] = useState<string | null>(null);
  const dragPositionRef = useRef<THREE.Vector3 | null>(null);

  const alignment = useAlignmentGuides({
    parts: components,
    draggedPartId,
    dragPosition: dragPositionRef.current,
    hiddenParts: hiddenComponents,
    settings: alignmentSettings,
    transforms: partTransforms.transforms,
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // NEW: Exploded View Hook (US-6.3)
  // ═══════════════════════════════════════════════════════════════════════════
  const explodedView = useExplodedView({
    components,
    transforms: partTransforms.transforms,
    hiddenComponents,
    expandDuration: prefersReducedMotion ? 0 : 500,
    collapseDuration: prefersReducedMotion ? 0 : 400,
    onStateChange: (state) => {
      // Optional: announce to screen readers
      announceToScreenReader(
        state === 'exploded' ? 'Exploded view activated' : 'Collapsed view'
      );
    },
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // MODIFIED: Transform Handlers (to support alignment snap)
  // ═══════════════════════════════════════════════════════════════════════════
  const handleDragStart = useCallback((partId: string) => {
    setDraggedPartId(partId);
  }, []);

  const handleDragPositionChange = useCallback((position: THREE.Vector3) => {
    dragPositionRef.current = position;
    // Force alignment recalculation
    // (useAlignmentGuides uses useFrame internally for throttling)
  }, []);

  const handleTransformEnd = useCallback(
    (partId: string, transform: PartTransform) => {
      // Apply snap position if alignment is active
      const finalTransform = alignmentEnabled && alignment.snapPosition
        ? { ...transform, position: alignment.calculateSnapPosition(
            new THREE.Vector3(transform.position.x, transform.position.y, transform.position.z)
          )}
        : transform;

      partTransforms.updateTransform(
        partId,
        finalTransform,
        `${transformMode === 'translate' ? 'Move' : 'Rotate'} ${
          components.find(c => c.id === partId)?.name || partId
        }`
      );
      
      // Clear drag state
      setDraggedPartId(null);
      dragPositionRef.current = null;
    },
    [alignmentEnabled, alignment, partTransforms, transformMode, components]
  );

  // ═══════════════════════════════════════════════════════════════════════════
  // MODIFIED: Keyboard Shortcuts (add A, E, Shift+E)
  // ═══════════════════════════════════════════════════════════════════════════
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      // ... existing shortcuts ...

      // NEW: Alignment toggle (A)
      if (e.key === 'a' || e.key === 'A') {
        e.preventDefault();
        setAlignmentEnabled(prev => !prev);
      }
      // NEW: Exploded view toggle (E)
      else if ((e.key === 'e' || e.key === 'E') && !e.shiftKey) {
        e.preventDefault();
        explodedView.toggle();
      }
      // NEW: Explode distance popover (Shift+E)
      else if ((e.key === 'e' || e.key === 'E') && e.shiftKey) {
        e.preventDefault();
        setExplodePopoverOpen(true);
      }
      // NEW: Temporary snap disable (Alt during drag)
      // Handled in PartTransformControls via altKey check
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [/* dependencies */]);

  // ═══════════════════════════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════════════════════════
  return (
    <div ref={containerRef} className={/* ... */}>
      <Canvas shadows dpr={[1, 2]}>
        {/* ... existing setup ... */}
        
        <AssemblyScene
          // ... existing props ...
          
          // NEW: Pass exploded positions from hook
          getExplodedPosition={explodedView.getExplodedPosition}
          
          // NEW: Pass alignment data
          alignmentEnabled={alignmentEnabled}
          alignmentGuides={alignment.guides}
          snapPosition={alignment.snapPosition}
          
          // NEW: Drag handlers for alignment
          onDragStart={handleDragStart}
          onDragPositionChange={handleDragPositionChange}
        />
        
        {/* NEW: Alignment Guides Overlay (US-6.2) */}
        {alignmentEnabled && draggedPartId && (
          <AlignmentGuides
            guides={alignment.guides}
            visible={alignment.hasActiveAlignment}
            fadeIn
          />
        )}
        
        {/* NEW: Explosion Lines (optional, US-6.3) */}
        {explodedView.state !== 'collapsed' && (
          <ExplosionLinesOverlay
            visible
            centroid={explodedView.centroid}
            partVectors={/* ... */}
          />
        )}
      </Canvas>

      {/* Toolbar - add new buttons */}
      <div className="absolute top-4 left-4 flex flex-col gap-2">
        {/* ... existing toolbar groups ... */}
        
        {/* View Controls - MODIFIED */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-1 flex flex-col gap-1">
          {/* Existing: Grid Snap */}
          <button /* ... */ />
          
          {/* NEW: Alignment Toolbar (US-6.2) */}
          <AlignmentToolbar
            enabled={alignmentEnabled}
            onToggle={() => setAlignmentEnabled(prev => !prev)}
            settings={alignmentSettings}
            onSettingsChange={(updates) => {
              setAlignmentSettings(prev => ({ ...prev, ...updates }));
              saveAlignmentSettings({ ...alignmentSettings, ...updates });
            }}
          />
          
          {/* NEW: Explode Toolbar (US-6.3) - replaces simple button */}
          <ExplodeToolbar
            state={explodedView.state}
            isAnimating={explodedView.isAnimating}
            distanceMultiplier={explodedView.distanceMultiplier}
            onToggle={explodedView.toggle}
            onDistanceChange={explodedView.setDistanceMultiplier}
          />
          
          {/* Existing: Reset Camera, Component List */}
          <button /* ... */ />
          <button /* ... */ />
        </div>
      </div>
    </div>
  );
}
```

### 4.2 Hook Composition Pattern

```typescript
// ─────────────────────────────────────────────────────────────────────────────
// HOOK COMPOSITION PATTERN
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Pattern: Hooks return state + actions, parent orchestrates.
 * 
 * ✅ Good: Hooks are independent, can be tested in isolation
 * ✅ Good: Parent component controls data flow
 * ✅ Good: Easy to add new hooks without changing existing ones
 */

// Example: useAlignmentGuides doesn't know about useExplodedView
// The parent coordinates them by passing the right data

function InteractiveAssemblyViewer() {
  // Hook 1: Source of truth for transforms
  const partTransforms = usePartTransforms();
  
  // Hook 2: Source of truth for visibility
  const visibility = useComponentVisibility();
  
  // Hook 3: Consumes data from hooks 1 & 2
  const explodedView = useExplodedView({
    transforms: partTransforms.transforms,      // From hook 1
    hiddenComponents: visibility.hiddenComponents, // From hook 2
  });
  
  // Hook 4: Consumes data from hooks 1, 2, and local state
  const alignment = useAlignmentGuides({
    transforms: partTransforms.transforms,
    hiddenParts: visibility.hiddenComponents,
    dragPosition: localDragPosition,
  });
  
  // Parent orchestrates: when drag ends, apply snap from alignment
  const handleDragEnd = (partId, transform) => {
    const finalPosition = alignment.calculateSnapPosition(transform.position);
    partTransforms.updateTransform(partId, { ...transform, position: finalPosition });
  };
}
```

### 4.3 PartTransformControls Extension

```typescript
// ─────────────────────────────────────────────────────────────────────────────
// CHANGES TO PartTransformControls.tsx
// ─────────────────────────────────────────────────────────────────────────────

export interface PartTransformControlsProps {
  // ... existing props ...
  
  /** NEW: Callback fired on each drag frame with current position */
  onDragPositionChange?: (position: THREE.Vector3) => void;
  
  /** NEW: If set, override final position to this on drag end */
  snapToPosition?: THREE.Vector3 | null;
  
  /** NEW: Whether Alt key disables snapping */
  respectAltKeyDisable?: boolean;
}

export function PartTransformControls({
  object,
  mode = 'translate',
  enablePositionSnap = true,
  // ... existing props
  onDragPositionChange,      // NEW
  snapToPosition,            // NEW
  respectAltKeyDisable = true,
}: PartTransformControlsProps) {
  const altKeyPressed = useRef(false);
  
  // Track Alt key state
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Alt') altKeyPressed.current = true;
    };
    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.key === 'Alt') altKeyPressed.current = false;
    };
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, []);
  
  // Modify handleChange to emit position
  const handleChange = useCallback(() => {
    if (!object || !controlsRef.current) return;
    
    // Check if snapping disabled by Alt key
    const shouldSnap = enablePositionSnap && 
      !(respectAltKeyDisable && altKeyPressed.current);
    
    if (mode === 'translate') {
      // Apply grid snapping if enabled
      if (shouldSnap) {
        // ... existing snap logic ...
      }
      
      // NEW: Emit position for alignment calculation
      onDragPositionChange?.(object.position.clone());
    }
    
    // ... rest of existing logic ...
  }, [/* deps including onDragPositionChange */]);
  
  // Modify handleDragEnd to apply snap position
  const handleDragEnd = useCallback(() => {
    onDraggingChange?.(false);
    
    if (object && onTransformEnd) {
      // NEW: Apply snap-to position if provided
      if (snapToPosition && mode === 'translate') {
        object.position.copy(snapToPosition);
      }
      
      const transform = getTransformFromObject(object);
      onTransformEnd(transform);
    }
  }, [object, snapToPosition, mode, onTransformEnd, onDraggingChange]);
  
  // ... rest of component ...
}
```

---

## 5. Testing Architecture

### 5.1 Unit Test Strategy for Hooks

```typescript
// ─────────────────────────────────────────────────────────────────────────────
// HOOK TESTING PATTERN
// File: frontend/src/hooks/useAlignmentGuides.test.ts
// ─────────────────────────────────────────────────────────────────────────────

import { renderHook, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import * as THREE from 'three';
import { useAlignmentGuides } from './useAlignmentGuides';

// ═══════════════════════════════════════════════════════════════════════════
// THREE.js MOCKING STRATEGY
// ═══════════════════════════════════════════════════════════════════════════

// Mock only what's necessary - Vector3 is usually fine to use directly
vi.mock('three', async () => {
  const actual = await vi.importActual('three');
  return {
    ...actual,
    // Mock expensive operations if needed
    Box3: vi.fn().mockImplementation(() => ({
      setFromObject: vi.fn().mockReturnThis(),
      getCenter: vi.fn().mockReturnValue(new actual.Vector3()),
      getSize: vi.fn().mockReturnValue(new actual.Vector3(10, 10, 10)),
    })),
  };
});

// ═══════════════════════════════════════════════════════════════════════════
// TEST FIXTURES
// ═══════════════════════════════════════════════════════════════════════════

const createMockPart = (overrides = {}) => ({
  id: 'part-1',
  name: 'Test Part',
  position: { x: 0, y: 0, z: 0 },
  rotation: { rx: 0, ry: 0, rz: 0 },
  scale: { sx: 1, sy: 1, sz: 1 },
  ...overrides,
});

const defaultSettings: AlignmentSettings = {
  enableEdgeAlignment: true,
  enableCenterAlignment: true,
  enableFaceAlignment: true,
  snapDistance: 10,
  snapThreshold: 5,
  gridSnapIncrement: 5,
  maxGuides: 6,
};

// ═══════════════════════════════════════════════════════════════════════════
// TEST CASES
// ═══════════════════════════════════════════════════════════════════════════

describe('useAlignmentGuides', () => {
  describe('guide detection', () => {
    it('detects center alignment when parts are within threshold', () => {
      const partA = createMockPart({ id: 'a', position: { x: 0, y: 0, z: 0 } });
      const partB = createMockPart({ id: 'b', position: { x: 5, y: 0, z: 0 } }); // Within threshold
      
      const { result } = renderHook(() =>
        useAlignmentGuides({
          parts: [partA, partB],
          draggedPartId: 'a',
          dragPosition: new THREE.Vector3(5, 0, 0), // Moving toward B
          hiddenParts: new Set(),
          settings: defaultSettings,
          transforms: {},
        })
      );
      
      expect(result.current.guides).toHaveLength(1);
      expect(result.current.guides[0].type).toBe('center');
      expect(result.current.guides[0].targetPartId).toBe('b');
    });

    it('excludes hidden parts from alignment calculation', () => {
      const partA = createMockPart({ id: 'a', position: { x: 0, y: 0, z: 0 } });
      const partB = createMockPart({ id: 'b', position: { x: 5, y: 0, z: 0 } });
      
      const { result } = renderHook(() =>
        useAlignmentGuides({
          parts: [partA, partB],
          draggedPartId: 'a',
          dragPosition: new THREE.Vector3(5, 0, 0),
          hiddenParts: new Set(['b']), // B is hidden
          settings: defaultSettings,
          transforms: {},
        })
      );
      
      expect(result.current.guides).toHaveLength(0);
    });

    it('respects settings to disable specific guide types', () => {
      const partA = createMockPart({ id: 'a', position: { x: 0, y: 0, z: 0 } });
      const partB = createMockPart({ id: 'b', position: { x: 5, y: 0, z: 0 } });
      
      const { result } = renderHook(() =>
        useAlignmentGuides({
          parts: [partA, partB],
          draggedPartId: 'a',
          dragPosition: new THREE.Vector3(5, 0, 0),
          hiddenParts: new Set(),
          settings: { ...defaultSettings, enableCenterAlignment: false },
          transforms: {},
        })
      );
      
      // No center guides returned
      expect(result.current.guides.filter(g => g.type === 'center')).toHaveLength(0);
    });

    it('limits guides to maxGuides setting', () => {
      // Create many parts that would all trigger alignment
      const parts = Array.from({ length: 20 }, (_, i) =>
        createMockPart({ id: `part-${i}`, position: { x: i * 2, y: 0, z: 0 } })
      );
      
      const { result } = renderHook(() =>
        useAlignmentGuides({
          parts,
          draggedPartId: 'part-0',
          dragPosition: new THREE.Vector3(10, 0, 0),
          hiddenParts: new Set(),
          settings: { ...defaultSettings, maxGuides: 6 },
          transforms: {},
        })
      );
      
      expect(result.current.guides.length).toBeLessThanOrEqual(6);
    });
  });

  describe('snap position calculation', () => {
    it('returns null snapPosition when outside threshold', () => {
      const partA = createMockPart({ id: 'a', position: { x: 0, y: 0, z: 0 } });
      const partB = createMockPart({ id: 'b', position: { x: 100, y: 0, z: 0 } });
      
      const { result } = renderHook(() =>
        useAlignmentGuides({
          parts: [partA, partB],
          draggedPartId: 'a',
          dragPosition: new THREE.Vector3(50, 0, 0), // Far from both
          hiddenParts: new Set(),
          settings: defaultSettings,
          transforms: {},
        })
      );
      
      expect(result.current.snapPosition).toBeNull();
    });

    it('calculateSnapPosition returns aligned position', () => {
      const partA = createMockPart({ id: 'a', position: { x: 0, y: 0, z: 0 } });
      const partB = createMockPart({ id: 'b', position: { x: 10, y: 0, z: 0 } });
      
      const { result } = renderHook(() =>
        useAlignmentGuides({
          parts: [partA, partB],
          draggedPartId: 'a',
          dragPosition: new THREE.Vector3(8, 0, 0), // Close to B
          hiddenParts: new Set(),
          settings: defaultSettings,
          transforms: {},
        })
      );
      
      const snappedPos = result.current.calculateSnapPosition(
        new THREE.Vector3(8, 0, 0)
      );
      
      // Should snap to B's center
      expect(snappedPos.x).toBe(10);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// File: frontend/src/hooks/useExplodedView.test.ts
// ─────────────────────────────────────────────────────────────────────────────

describe('useExplodedView', () => {
  describe('state machine', () => {
    it('starts in collapsed state with factor 0', () => {
      const { result } = renderHook(() =>
        useExplodedView({
          components: [createMockPart()],
          transforms: {},
          hiddenComponents: new Set(),
        })
      );
      
      expect(result.current.state).toBe('collapsed');
      expect(result.current.factor).toBe(0);
    });

    it('transitions to exploding on toggle', () => {
      const { result } = renderHook(() =>
        useExplodedView({
          components: [createMockPart()],
          transforms: {},
          hiddenComponents: new Set(),
        })
      );
      
      act(() => {
        result.current.toggle();
      });
      
      expect(result.current.state).toBe('exploding');
      expect(result.current.isAnimating).toBe(true);
    });

    // Test with fake timers for animation
    it('completes animation and enters exploded state', async () => {
      vi.useFakeTimers();
      
      const { result } = renderHook(() =>
        useExplodedView({
          components: [createMockPart()],
          transforms: {},
          hiddenComponents: new Set(),
          expandDuration: 500,
        })
      );
      
      act(() => {
        result.current.toggle();
      });
      
      // Advance past animation duration
      await act(async () => {
        vi.advanceTimersByTime(600);
      });
      
      expect(result.current.state).toBe('exploded');
      expect(result.current.factor).toBe(1);
      expect(result.current.isAnimating).toBe(false);
      
      vi.useRealTimers();
    });
  });

  describe('explosion vectors', () => {
    it('calculates centroid from component positions', () => {
      const parts = [
        createMockPart({ id: 'a', position: { x: 0, y: 0, z: 0 } }),
        createMockPart({ id: 'b', position: { x: 10, y: 0, z: 0 } }),
      ];
      
      const { result } = renderHook(() =>
        useExplodedView({
          components: parts,
          transforms: {},
          hiddenComponents: new Set(),
        })
      );
      
      expect(result.current.centroid.x).toBe(5); // Average of 0 and 10
    });

    it('uses fallback direction for parts at centroid', () => {
      // All parts at same position
      const parts = [
        createMockPart({ id: 'a', position: { x: 0, y: 0, z: 0 } }),
        createMockPart({ id: 'b', position: { x: 0, y: 0, z: 0 } }),
      ];
      
      const { result } = renderHook(() =>
        useExplodedView({
          components: parts,
          transforms: {},
          hiddenComponents: new Set(),
        })
      );
      
      // Should have valid explosion vectors (not NaN)
      result.current.explosionVectors.forEach((vec) => {
        expect(Number.isNaN(vec.direction.x)).toBe(false);
        expect(vec.direction.length()).toBeGreaterThan(0);
      });
    });

    it('excludes hidden components from centroid calculation', () => {
      const parts = [
        createMockPart({ id: 'a', position: { x: 0, y: 0, z: 0 } }),
        createMockPart({ id: 'b', position: { x: 100, y: 0, z: 0 } }), // Hidden outlier
      ];
      
      const { result } = renderHook(() =>
        useExplodedView({
          components: parts,
          transforms: {},
          hiddenComponents: new Set(['b']),
        })
      );
      
      // Centroid should only consider 'a'
      expect(result.current.centroid.x).toBe(0);
    });
  });

  describe('getExplodedPosition', () => {
    it('returns original position when collapsed', () => {
      const { result } = renderHook(() =>
        useExplodedView({
          components: [createMockPart({ id: 'a', position: { x: 10, y: 0, z: 0 } })],
          transforms: {},
          hiddenComponents: new Set(),
        })
      );
      
      const pos = result.current.getExplodedPosition('a', new THREE.Vector3(10, 0, 0));
      expect(pos.x).toBe(10);
    });
  });
});
```

### 5.2 Component Test Strategy

```typescript
// ─────────────────────────────────────────────────────────────────────────────
// COMPONENT TESTING PATTERN
// File: frontend/src/components/assembly/AlignmentToolbar.test.tsx
// ─────────────────────────────────────────────────────────────────────────────

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect } from 'vitest';
import { AlignmentToolbar } from './AlignmentToolbar';

describe('AlignmentToolbar', () => {
  const defaultProps = {
    enabled: true,
    onToggle: vi.fn(),
    settings: {
      enableEdgeAlignment: true,
      enableCenterAlignment: true,
      enableFaceAlignment: true,
      snapDistance: 10,
      snapThreshold: 5,
      gridSnapIncrement: 5,
      maxGuides: 6,
    },
    onSettingsChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('button rendering', () => {
    it('renders magnet button with correct icon', () => {
      render(<AlignmentToolbar {...defaultProps} />);
      
      const button = screen.getByRole('button', { name: /alignment guides/i });
      expect(button).toBeInTheDocument();
      // Check for Magnet icon - implementation specific
      expect(button.querySelector('svg')).toBeInTheDocument();
    });

    it('shows active state when enabled', () => {
      render(<AlignmentToolbar {...defaultProps} enabled={true} />);
      
      const button = screen.getByRole('button', { name: /alignment guides/i });
      expect(button).toHaveClass('bg-primary-600');
    });

    it('shows inactive state when disabled', () => {
      render(<AlignmentToolbar {...defaultProps} enabled={false} />);
      
      const button = screen.getByRole('button', { name: /alignment guides/i });
      expect(button).not.toHaveClass('bg-primary-600');
    });
  });

  describe('popover interaction', () => {
    it('opens popover on button click', async () => {
      const user = userEvent.setup();
      render(<AlignmentToolbar {...defaultProps} />);
      
      const button = screen.getByRole('button', { name: /alignment guides/i });
      await user.click(button);
      
      // Popover content should be visible
      expect(screen.getByText('Alignment Guides')).toBeInTheDocument();
      expect(screen.getByLabelText('Edge alignment')).toBeInTheDocument();
    });

    it('closes popover when clicking outside', async () => {
      const user = userEvent.setup();
      render(
        <div>
          <div data-testid="outside">Outside</div>
          <AlignmentToolbar {...defaultProps} />
        </div>
      );
      
      // Open popover
      const button = screen.getByRole('button', { name: /alignment guides/i });
      await user.click(button);
      expect(screen.getByText('Alignment Guides')).toBeInTheDocument();
      
      // Click outside
      await user.click(screen.getByTestId('outside'));
      
      await waitFor(() => {
        expect(screen.queryByText('Alignment Guides')).not.toBeInTheDocument();
      });
    });
  });

  describe('settings controls', () => {
    it('toggles edge alignment on checkbox change', async () => {
      const user = userEvent.setup();
      const onSettingsChange = vi.fn();
      
      render(
        <AlignmentToolbar
          {...defaultProps}
          onSettingsChange={onSettingsChange}
        />
      );
      
      // Open popover
      await user.click(screen.getByRole('button', { name: /alignment guides/i }));
      
      // Toggle checkbox
      const checkbox = screen.getByLabelText('Edge alignment');
      await user.click(checkbox);
      
      expect(onSettingsChange).toHaveBeenCalledWith({
        enableEdgeAlignment: false,
      });
    });

    it('updates snap distance on slider change', async () => {
      const user = userEvent.setup();
      const onSettingsChange = vi.fn();
      
      render(
        <AlignmentToolbar
          {...defaultProps}
          onSettingsChange={onSettingsChange}
        />
      );
      
      // Open popover
      await user.click(screen.getByRole('button', { name: /alignment guides/i }));
      
      // Change slider
      const slider = screen.getByLabelText(/snap distance/i);
      fireEvent.change(slider, { target: { value: '15' } });
      
      expect(onSettingsChange).toHaveBeenCalledWith({
        snapDistance: 15,
      });
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// File: frontend/src/components/assembly/ExplodeToolbar.test.tsx
// ─────────────────────────────────────────────────────────────────────────────

describe('ExplodeToolbar', () => {
  const defaultProps = {
    state: 'collapsed' as const,
    isAnimating: false,
    distanceMultiplier: 1.0,
    onToggle: vi.fn(),
    onDistanceChange: vi.fn(),
  };

  describe('button states', () => {
    it('renders Expand icon when collapsed', () => {
      render(<ExplodeToolbar {...defaultProps} state="collapsed" />);
      
      // Check for Expand icon
      const button = screen.getByRole('button', { name: /explode/i });
      expect(button).toBeInTheDocument();
    });

    it('renders Shrink icon when exploded', () => {
      render(<ExplodeToolbar {...defaultProps} state="exploded" />);
      
      const button = screen.getByRole('button', { name: /collapse/i });
      expect(button).toBeInTheDocument();
    });

    it('disables button during animation', () => {
      render(<ExplodeToolbar {...defaultProps} isAnimating={true} />);
      
      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });
  });

  describe('distance slider', () => {
    it('shows slider in popover when exploded', async () => {
      const user = userEvent.setup();
      
      render(<ExplodeToolbar {...defaultProps} state="exploded" />);
      
      // Click dropdown arrow (or long-press simulation)
      const dropdownTrigger = screen.getByLabelText(/adjust distance/i);
      await user.click(dropdownTrigger);
      
      expect(screen.getByRole('slider')).toBeInTheDocument();
      expect(screen.getByText(/explosion distance/i)).toBeInTheDocument();
    });

    it('calls onDistanceChange when slider moves', async () => {
      const user = userEvent.setup();
      const onDistanceChange = vi.fn();
      
      render(
        <ExplodeToolbar
          {...defaultProps}
          state="exploded"
          onDistanceChange={onDistanceChange}
        />
      );
      
      // Open popover
      await user.click(screen.getByLabelText(/adjust distance/i));
      
      // Move slider
      const slider = screen.getByRole('slider');
      fireEvent.change(slider, { target: { value: '2.0' } });
      
      expect(onDistanceChange).toHaveBeenCalledWith(2.0);
    });

    it('clamps slider to valid range (0.5-3.0)', async () => {
      const user = userEvent.setup();
      
      render(<ExplodeToolbar {...defaultProps} state="exploded" />);
      await user.click(screen.getByLabelText(/adjust distance/i));
      
      const slider = screen.getByRole('slider');
      
      expect(slider).toHaveAttribute('min', '0.5');
      expect(slider).toHaveAttribute('max', '3');
    });
  });
});
```

### 5.3 E2E Test Scenarios (Playwright)

```typescript
// ─────────────────────────────────────────────────────────────────────────────
// E2E TEST FILE
// File: frontend/e2e/assembly-viewer-alignment.spec.ts
// ─────────────────────────────────────────────────────────────────────────────

import { test, expect } from '@playwright/test';

test.describe('US-6.2: Part Alignment/Snap Tools', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to assembly viewer with test fixture
    await page.goto('/assemblies/test-assembly-001');
    await page.waitForSelector('[data-testid="assembly-viewer"]');
  });

  test('alignment guides toggle with A key', async ({ page }) => {
    // Initial state: alignment enabled
    const alignmentButton = page.getByRole('button', { name: /alignment guides/i });
    await expect(alignmentButton).toHaveClass(/bg-primary/);

    // Press A to disable
    await page.keyboard.press('a');
    await expect(alignmentButton).not.toHaveClass(/bg-primary/);

    // Press A again to enable
    await page.keyboard.press('a');
    await expect(alignmentButton).toHaveClass(/bg-primary/);
  });

  test('alignment popover opens and settings persist', async ({ page }) => {
    // Click alignment button to open popover
    await page.getByRole('button', { name: /alignment guides/i }).click();

    // Popover should be visible
    await expect(page.getByText('Alignment Guides')).toBeVisible();

    // Uncheck edge alignment
    const edgeCheckbox = page.getByLabel('Edge alignment');
    await edgeCheckbox.uncheck();
    await expect(edgeCheckbox).not.toBeChecked();

    // Close popover
    await page.keyboard.press('Escape');

    // Reopen - setting should persist
    await page.getByRole('button', { name: /alignment guides/i }).click();
    await expect(page.getByLabel('Edge alignment')).not.toBeChecked();
  });

  test('alignment guides appear during part drag', async ({ page }) => {
    // Select a part
    await page.click('[data-testid="part-connector-a"]');

    // Start dragging
    const part = page.locator('[data-testid="part-connector-a"]');
    await part.dragTo(page.locator('[data-testid="part-housing"]'), {
      sourcePosition: { x: 50, y: 50 },
      targetPosition: { x: 50, y: 50 },
    });

    // Check that alignment guide is rendered
    // Note: This requires WebGL inspection or visual regression
    // For now, check that alignment state is active
    await expect(page.locator('[data-testid="alignment-indicator"]')).toBeVisible();
  });

  test('Alt key disables snapping during drag', async ({ page }) => {
    await page.click('[data-testid="part-connector-a"]');

    // Start drag with Alt held
    await page.keyboard.down('Alt');

    // Perform drag
    await page.mouse.move(100, 100);
    await page.mouse.down();
    await page.mouse.move(200, 200);

    // Check that no snap indicator appears
    await expect(page.locator('[data-testid="snap-indicator"]')).not.toBeVisible();

    await page.mouse.up();
    await page.keyboard.up('Alt');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// File: frontend/e2e/assembly-viewer-exploded.spec.ts
// ─────────────────────────────────────────────────────────────────────────────

test.describe('US-6.3: Exploded View Mode', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/assemblies/test-assembly-001');
    await page.waitForSelector('[data-testid="assembly-viewer"]');
  });

  test('E key toggles exploded view', async ({ page }) => {
    const explodeButton = page.getByRole('button', { name: /explode/i });

    // Initial: collapsed
    await expect(explodeButton).toContainText('Expand');

    // Press E
    await page.keyboard.press('e');

    // Wait for animation to complete
    await page.waitForTimeout(600); // 500ms animation + buffer

    // Should now show collapse option
    await expect(page.getByRole('button', { name: /collapse/i })).toBeVisible();
  });

  test('distance slider adjusts part positions', async ({ page }) => {
    // Enable exploded view
    await page.keyboard.press('e');
    await page.waitForTimeout(600);

    // Open distance popover
    await page.getByLabelText(/adjust distance/i).click();

    // Slide to max
    const slider = page.getByRole('slider');
    await slider.fill('3.0');

    // Parts should be more spread out (visual verification or position check)
    // This would typically use visual regression testing
    await expect(page.getByText('3.0x')).toBeVisible();
  });

  test('respects prefers-reduced-motion', async ({ page }) => {
    // Enable reduced motion
    await page.emulateMedia({ reducedMotion: 'reduce' });

    // Toggle exploded view
    await page.keyboard.press('e');

    // Should transition immediately (no 500ms delay)
    // Check button state changes instantly
    await expect(page.getByRole('button', { name: /collapse/i })).toBeVisible();
  });

  test('button disabled during animation', async ({ page }) => {
    const explodeButton = page.getByRole('button', { name: /explode/i });

    // Start animation
    await explodeButton.click();

    // Button should be disabled during animation
    await expect(explodeButton).toBeDisabled();

    // After animation, should be enabled
    await page.waitForTimeout(600);
    await expect(page.getByRole('button', { name: /collapse/i })).toBeEnabled();
  });
});
```

### 5.4 Test File Organization

```
frontend/
├── src/
│   ├── hooks/
│   │   ├── useAlignmentGuides.ts
│   │   ├── useAlignmentGuides.test.ts      ← Unit tests
│   │   ├── useExplodedView.ts
│   │   ├── useExplodedView.test.ts         ← Unit tests
│   │   ├── useAnimatedValue.ts
│   │   └── useAnimatedValue.test.ts        ← Unit tests
│   │
│   └── components/
│       └── assembly/
│           ├── AlignmentGuides.tsx
│           ├── AlignmentGuides.test.tsx    ← Component tests (RTL)
│           ├── AlignmentToolbar.tsx
│           ├── AlignmentToolbar.test.tsx   ← Component tests (RTL)
│           ├── ExplodeToolbar.tsx
│           ├── ExplodeToolbar.test.tsx     ← Component tests (RTL)
│           ├── InteractiveAssemblyViewer.tsx
│           └── InteractiveAssemblyViewer.test.tsx ← Integration tests
│
└── e2e/
    ├── assembly-viewer-alignment.spec.ts   ← E2E (US-6.2)
    └── assembly-viewer-exploded.spec.ts    ← E2E (US-6.3)
```

---

## 6. Security Considerations

### 6.1 Analysis Summary

These features are **purely client-side** with no backend changes required. Security concerns are minimal but documented for completeness.

### 6.2 Client-Side Input Validation

```typescript
// ─────────────────────────────────────────────────────────────────────────────
// INPUT VALIDATION (Defense in depth, even for UI-only settings)
// ─────────────────────────────────────────────────────────────────────────────

// Alignment settings validation
const ALIGNMENT_CONSTRAINTS = {
  snapDistance: { min: 2, max: 30, default: 10 },
  snapThreshold: { min: 1, max: 15, default: 5 },
  gridSnapIncrement: { min: 1, max: 25, default: 5 },
  maxGuides: { min: 1, max: 12, default: 6 },
} as const;

function validateAlignmentSettings(settings: Partial<AlignmentSettings>): AlignmentSettings {
  return {
    enableEdgeAlignment: settings.enableEdgeAlignment ?? true,
    enableCenterAlignment: settings.enableCenterAlignment ?? true,
    enableFaceAlignment: settings.enableFaceAlignment ?? true,
    snapDistance: clamp(
      settings.snapDistance ?? ALIGNMENT_CONSTRAINTS.snapDistance.default,
      ALIGNMENT_CONSTRAINTS.snapDistance.min,
      ALIGNMENT_CONSTRAINTS.snapDistance.max
    ),
    snapThreshold: clamp(
      settings.snapThreshold ?? ALIGNMENT_CONSTRAINTS.snapThreshold.default,
      ALIGNMENT_CONSTRAINTS.snapThreshold.min,
      ALIGNMENT_CONSTRAINTS.snapThreshold.max
    ),
    gridSnapIncrement: clamp(
      settings.gridSnapIncrement ?? ALIGNMENT_CONSTRAINTS.gridSnapIncrement.default,
      ALIGNMENT_CONSTRAINTS.gridSnapIncrement.min,
      ALIGNMENT_CONSTRAINTS.gridSnapIncrement.max
    ),
    maxGuides: clamp(
      settings.maxGuides ?? ALIGNMENT_CONSTRAINTS.maxGuides.default,
      ALIGNMENT_CONSTRAINTS.maxGuides.min,
      ALIGNMENT_CONSTRAINTS.maxGuides.max
    ),
  };
}

// Exploded view validation
const EXPLODE_CONSTRAINTS = {
  distanceMultiplier: { min: 0.5, max: 3.0, default: 1.0 },
} as const;

function validateDistanceMultiplier(value: number): number {
  return clamp(
    value,
    EXPLODE_CONSTRAINTS.distanceMultiplier.min,
    EXPLODE_CONSTRAINTS.distanceMultiplier.max
  );
}

// Helper
function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}
```

### 6.3 SessionStorage Security

```typescript
// ─────────────────────────────────────────────────────────────────────────────
// SESSIONSTORAGE HANDLING
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Security considerations for sessionStorage:
 * 
 * 1. Data is scoped to tab/session (cleared on tab close)
 * 2. No sensitive data is stored (only UI preferences)
 * 3. All loaded data is validated before use
 * 4. Graceful fallback on parse errors
 */

const STORAGE_KEY_PREFIX = 'assembly-alignment:';

function loadAlignmentSettings(assemblyId: string): AlignmentSettings {
  try {
    const raw = sessionStorage.getItem(`${STORAGE_KEY_PREFIX}${assemblyId}`);
    if (!raw) return DEFAULT_ALIGNMENT_SETTINGS;

    const parsed = JSON.parse(raw);
    
    // Validate parsed data - never trust storage
    return validateAlignmentSettings(parsed);
  } catch {
    // JSON parse error or other issue - use defaults
    console.warn('Failed to load alignment settings, using defaults');
    return DEFAULT_ALIGNMENT_SETTINGS;
  }
}

function saveAlignmentSettings(assemblyId: string, settings: AlignmentSettings): void {
  try {
    // Validate before saving
    const validated = validateAlignmentSettings(settings);
    sessionStorage.setItem(`${STORAGE_KEY_PREFIX}${assemblyId}`, JSON.stringify(validated));
  } catch {
    // Storage quota exceeded or other error - silently fail
    console.warn('Failed to save alignment settings');
  }
}
```

### 6.4 XSS Prevention

```typescript
// ─────────────────────────────────────────────────────────────────────────────
// XSS PREVENTION (React handles this, but documented for awareness)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * React automatically escapes values rendered in JSX.
 * No `dangerouslySetInnerHTML` is used in these features.
 * 
 * Component names (from API) are displayed but always escaped:
 */

// ✅ Safe - React escapes the component.name
<span>{component.name}</span>

// ❌ Never do this (not used in this feature)
<span dangerouslySetInnerHTML={{ __html: component.name }} />

/**
 * All text content comes from:
 * 1. Hardcoded UI labels (safe)
 * 2. Numeric values from sliders (validated to be numbers)
 * 3. Component names from API (escaped by React)
 */
```

### 6.5 Performance-Based DoS Prevention

```typescript
// ─────────────────────────────────────────────────────────────────────────────
// PREVENTING CLIENT-SIDE DoS
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Malicious or very large assemblies could cause performance issues.
 * Mitigations:
 */

// 1. Limit number of guides computed
const MAX_GUIDES = 6; // Hard cap regardless of settings

// 2. Limit spatial hash grid operations
const MAX_CANDIDATES_PER_FRAME = 50;

// 3. Time budget for calculations
const ALIGNMENT_CALC_BUDGET_MS = 3;

// 4. Throttle high-frequency updates
const DRAG_POSITION_THROTTLE_MS = 16; // ~60fps

// 5. Skip calculations entirely for very large assemblies
const MAX_PARTS_FOR_ALIGNMENT = 200;

function shouldEnableAlignment(partCount: number): boolean {
  if (partCount > MAX_PARTS_FOR_ALIGNMENT) {
    console.warn(`Alignment disabled for large assembly (${partCount} parts)`);
    return false;
  }
  return true;
}
```

---

## 7. Technical Specifications

### 7.1 Hook Interfaces

```typescript
// ═══════════════════════════════════════════════════════════════════════════
// FILE: frontend/src/hooks/useAlignmentGuides.ts
// ═══════════════════════════════════════════════════════════════════════════

import type { Vector3 } from 'three';
import type { AssemblyComponent } from '../types/assembly';
import type { PartTransformState } from './usePartTransforms';

// ─────────────────────────────────────────────────────────────────────────────
// Configuration Types
// ─────────────────────────────────────────────────────────────────────────────

export interface AlignmentSettings {
  /** Enable edge-to-edge alignment guides. Default: true */
  enableEdgeAlignment: boolean;
  /** Enable center-to-center alignment guides. Default: true */
  enableCenterAlignment: boolean;
  /** Enable face-to-face alignment guides. Default: true */
  enableFaceAlignment: boolean;
  /** Distance threshold for showing visual guides (units). Default: 10 */
  snapDistance: number;
  /** Distance threshold for executing snap on release (units). Default: 5 */
  snapThreshold: number;
  /** Grid snap increment (units). Default: 5 */
  gridSnapIncrement: number;
  /** Maximum simultaneous guides to display. Default: 6 */
  maxGuides: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Guide Types
// ─────────────────────────────────────────────────────────────────────────────

export type AlignmentGuideType = 'edge' | 'center' | 'face';

export interface AlignmentGuide {
  /** Unique identifier for React reconciliation. */
  id: string;
  /** Type of alignment. */
  type: AlignmentGuideType;
  /** ID of the part being dragged. */
  sourcePartId: string;
  /** ID of the part being aligned to. */
  targetPartId: string;
  /** Primary axis of alignment. */
  axis: 'x' | 'y' | 'z';
  /** World-space position of guide center. */
  position: Vector3;
  /** Start point for edge/center line guides. */
  startPoint?: Vector3;
  /** End point for edge/center line guides. */
  endPoint?: Vector3;
  /** Normal vector for face alignment plane. */
  planeNormal?: Vector3;
  /** Dimensions for face alignment plane visualization. */
  planeSize?: { width: number; height: number };
  /** Alignment strength (0-1) based on distance to threshold. */
  strength: number;
  /** Distance to alignment (for sorting/prioritization). */
  distance: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Hook Options & Return Types
// ─────────────────────────────────────────────────────────────────────────────

export interface UseAlignmentGuidesOptions {
  /** All parts in the assembly. */
  parts: AssemblyComponent[];
  /** ID of the part currently being dragged, or null. */
  draggedPartId: string | null;
  /** Current drag position in world coordinates, or null. */
  dragPosition: Vector3 | null;
  /** Set of part IDs that are hidden (excluded from alignment). */
  hiddenParts: Set<string>;
  /** Alignment configuration. */
  settings: AlignmentSettings;
  /** Current part transforms (for accurate bounding boxes). */
  transforms: PartTransformState;
}

export interface UseAlignmentGuidesReturn {
  /** Active alignment guides to render (sorted by priority, limited by maxGuides). */
  guides: AlignmentGuide[];
  /** Suggested snap position if within threshold, null otherwise. */
  snapPosition: Vector3 | null;
  /** Whether any alignment is currently active. */
  hasActiveAlignment: boolean;
  /**
   * Calculate the final snap position for a release point.
   * Considers active alignments and returns adjusted position.
   */
  calculateSnapPosition: (releasePosition: Vector3) => Vector3;
}

export function useAlignmentGuides(options: UseAlignmentGuidesOptions): UseAlignmentGuidesReturn;

// ═══════════════════════════════════════════════════════════════════════════
// FILE: frontend/src/hooks/useExplodedView.ts
// ═══════════════════════════════════════════════════════════════════════════

import type { Vector3 } from 'three';
import type { AssemblyComponent } from '../types/assembly';
import type { PartTransformState } from './usePartTransforms';

// ─────────────────────────────────────────────────────────────────────────────
// State Machine Types
// ─────────────────────────────────────────────────────────────────────────────

export type ExplodeState = 'collapsed' | 'exploding' | 'exploded' | 'collapsing';

// ─────────────────────────────────────────────────────────────────────────────
// Explosion Vector Types
// ─────────────────────────────────────────────────────────────────────────────

export interface ExplosionVector {
  /** Part identifier. */
  partId: string;
  /** Normalized direction vector from assembly centroid. */
  direction: Vector3;
  /** Base distance to travel at factor=1.0 (units). */
  baseDistance: number;
  /** Original position before explosion. */
  originalPosition: Vector3;
}

// ─────────────────────────────────────────────────────────────────────────────
// Hook Options & Return Types
// ─────────────────────────────────────────────────────────────────────────────

export interface UseExplodedViewOptions {
  /** Components in the assembly. */
  components: AssemblyComponent[];
  /** Current part transforms. */
  transforms: PartTransformState;
  /** Set of hidden component IDs (excluded from centroid calculation). */
  hiddenComponents: Set<string>;
  /** Animation duration for expansion (ms). Default: 500 */
  expandDuration?: number;
  /** Animation duration for collapse (ms). Default: 400 */
  collapseDuration?: number;
  /** Callback when state changes (for accessibility announcements). */
  onStateChange?: (state: ExplodeState) => void;
}

export interface UseExplodedViewReturn {
  /** Current state machine state. */
  state: ExplodeState;
  /** Current animated explosion factor (0-1). */
  factor: number;
  /** User-controlled distance multiplier (0.5-3.0). */
  distanceMultiplier: number;
  /** Pre-computed explosion vectors for each part. */
  explosionVectors: ExplosionVector[];
  /** Whether currently animating. */
  isAnimating: boolean;
  /** Toggle between collapsed and exploded states. */
  toggle: () => void;
  /** Set the distance multiplier (animates to new value). */
  setDistanceMultiplier: (multiplier: number) => void;
  /**
   * Get the current exploded position for a specific part.
   * Returns original position when collapsed.
   */
  getExplodedPosition: (partId: string, originalPosition: Vector3) => Vector3;
  /** Assembly centroid (for reference/visualization). */
  centroid: Vector3;
}

export function useExplodedView(options: UseExplodedViewOptions): UseExplodedViewReturn;

// ═══════════════════════════════════════════════════════════════════════════
// FILE: frontend/src/hooks/useAnimatedValue.ts
// ═══════════════════════════════════════════════════════════════════════════

// ─────────────────────────────────────────────────────────────────────────────
// Easing Function Type
// ─────────────────────────────────────────────────────────────────────────────

export type EasingFunction = (t: number) => number;

// ─────────────────────────────────────────────────────────────────────────────
// Hook Options & Return Types
// ─────────────────────────────────────────────────────────────────────────────

export interface UseAnimatedValueOptions {
  /** Initial value. */
  initialValue: number;
  /** Animation duration in milliseconds. Default: 300 */
  duration?: number;
  /** Easing function. Default: easeOutCubic */
  easing?: EasingFunction;
  /** Callback when animation completes. */
  onComplete?: () => void;
}

export interface UseAnimatedValueReturn {
  /** Current animated value. */
  value: number;
  /** Target value (what we're animating toward). */
  targetValue: number;
  /** Whether currently animating. */
  isAnimating: boolean;
  /** Set new target value (animates from current to target). */
  setTarget: (target: number) => void;
  /** Immediately set value without animation. */
  setValue: (value: number) => void;
}

export function useAnimatedValue(options: UseAnimatedValueOptions): UseAnimatedValueReturn;

// ─────────────────────────────────────────────────────────────────────────────
// Easing Presets
// ─────────────────────────────────────────────────────────────────────────────

export const easings = {
  linear: (t: number) => t,
  easeOutQuad: (t: number) => 1 - (1 - t) ** 2,
  easeOutCubic: (t: number) => 1 - (1 - t) ** 3,
  easeInOutCubic: (t: number) =>
    t < 0.5 ? 4 * t ** 3 : 1 - (-2 * t + 2) ** 3 / 2,
} as const;
```

### 7.2 Component Props Interfaces

```typescript
// ═══════════════════════════════════════════════════════════════════════════
// FILE: frontend/src/components/assembly/AlignmentGuides.tsx
// ═══════════════════════════════════════════════════════════════════════════

import type { AlignmentGuide } from '../../hooks/useAlignmentGuides';

export interface AlignmentGuidesProps {
  /** Array of guides to render. */
  guides: AlignmentGuide[];
  /** Whether guides should be visible. */
  visible: boolean;
  /** Whether to animate fade-in. Default: false */
  fadeIn?: boolean;
}

// ═══════════════════════════════════════════════════════════════════════════
// FILE: frontend/src/components/assembly/AlignmentToolbar.tsx
// ═══════════════════════════════════════════════════════════════════════════

import type { AlignmentSettings } from '../../hooks/useAlignmentGuides';

export interface AlignmentToolbarProps {
  /** Whether alignment guides are enabled. */
  enabled: boolean;
  /** Callback to toggle alignment on/off. */
  onToggle: () => void;
  /** Current alignment settings. */
  settings: AlignmentSettings;
  /** Callback when any setting changes. */
  onSettingsChange: (settings: Partial<AlignmentSettings>) => void;
}

// ═══════════════════════════════════════════════════════════════════════════
// FILE: frontend/src/components/assembly/ExplodeToolbar.tsx
// ═══════════════════════════════════════════════════════════════════════════

import type { ExplodeState } from '../../hooks/useExplodedView';

export interface ExplodeToolbarProps {
  /** Current explosion state. */
  state: ExplodeState;
  /** Whether animation is in progress. */
  isAnimating: boolean;
  /** Current distance multiplier (0.5-3.0). */
  distanceMultiplier: number;
  /** Callback to toggle exploded view. */
  onToggle: () => void;
  /** Callback when distance multiplier changes. */
  onDistanceChange: (multiplier: number) => void;
}

// ═══════════════════════════════════════════════════════════════════════════
// FILE: frontend/src/components/assembly/ExplosionLinesOverlay.tsx
// ═══════════════════════════════════════════════════════════════════════════

import type { Vector3 } from 'three';

export interface PartVector {
  partId: string;
  position: Vector3;
  direction: Vector3;
}

export interface ExplosionLinesOverlayProps {
  /** Whether to show the explosion lines. */
  visible: boolean;
  /** Assembly centroid position. */
  centroid: Vector3;
  /** Vectors for each part. */
  partVectors: PartVector[];
}

// ═══════════════════════════════════════════════════════════════════════════
// Extended PartTransformControls Props
// FILE: frontend/src/components/viewer/PartTransformControls.tsx
// ═══════════════════════════════════════════════════════════════════════════

import type { Object3D, Vector3 } from 'three';

export type TransformMode = 'translate' | 'rotate' | 'scale';

export interface PartTransform {
  position: { x: number; y: number; z: number };
  rotation: { rx: number; ry: number; rz: number };
  scale: { sx: number; sy: number; sz: number };
}

export interface PartTransformControlsProps {
  /** The mesh or object to transform. */
  object?: Object3D | null;
  /** Transform mode (translate, rotate, scale). */
  mode?: TransformMode;
  /** Enable position snapping (to grid). */
  enablePositionSnap?: boolean;
  /** Position snap increment in world units. */
  positionSnapIncrement?: number;
  /** Enable rotation snapping. */
  enableRotationSnap?: boolean;
  /** Rotation snap increment in degrees. */
  rotationSnapIncrement?: number;
  /** Callback when transform changes (during drag). */
  onTransformChange?: (transform: PartTransform) => void;
  /** Callback when transform ends (drag release). */
  onTransformEnd?: (transform: PartTransform) => void;
  /** Callback when dragging state changes. */
  onDraggingChange?: (isDragging: boolean) => void;
  
  // ══════════════════════════════════════════════════════════════════════════
  // NEW PROPS (US-6.2)
  // ══════════════════════════════════════════════════════════════════════════
  
  /** Callback fired on each drag frame with current world position. */
  onDragPositionChange?: (position: Vector3) => void;
  /** If set, override the final position to this on drag end. */
  snapToPosition?: Vector3 | null;
  /** Whether holding Alt key temporarily disables snapping. Default: true */
  respectAltKeyDisable?: boolean;
}
```

### 7.3 Internal State Shapes

```typescript
// ═══════════════════════════════════════════════════════════════════════════
// INTERNAL STATE SHAPES (Not exported, for implementation reference)
// ═══════════════════════════════════════════════════════════════════════════

// ─────────────────────────────────────────────────────────────────────────────
// Spatial Hash Grid (internal to useAlignmentGuides)
// ─────────────────────────────────────────────────────────────────────────────

interface SpatialHashGrid {
  cellSize: number;
  cells: Map<string, string[]>; // cellKey -> partId[]
}

interface BoundingBoxCache {
  boxes: Map<string, THREE.Box3>;
  lastTransforms: Map<string, string>; // partId -> transform hash for invalidation
}

interface AlignmentCalculationState {
  grid: SpatialHashGrid;
  boundingBoxes: BoundingBoxCache;
  lastDragPosition: THREE.Vector3 | null;
  lastCalculationTime: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Animation State (internal to useExplodedView / useAnimatedValue)
// ─────────────────────────────────────────────────────────────────────────────

interface AnimationState {
  isAnimating: boolean;
  startValue: number;
  endValue: number;
  startTime: number;
  duration: number;
  easing: EasingFunction;
  rafId: number | null; // requestAnimationFrame ID for cleanup
}

// ─────────────────────────────────────────────────────────────────────────────
// Explosion Computation Cache (internal to useExplodedView)
// ─────────────────────────────────────────────────────────────────────────────

interface ExplosionCache {
  componentHash: string; // Hash of component IDs for cache invalidation
  centroid: THREE.Vector3;
  vectors: ExplosionVector[];
}
```

---

## Appendix A: File Manifest

| File | Action | Feature |
|------|--------|---------|
| `frontend/src/hooks/useAlignmentGuides.ts` | Create | US-6.2 |
| `frontend/src/hooks/useAlignmentGuides.test.ts` | Create | US-6.2 |
| `frontend/src/hooks/useExplodedView.ts` | Create | US-6.3 |
| `frontend/src/hooks/useExplodedView.test.ts` | Create | US-6.3 |
| `frontend/src/hooks/useAnimatedValue.ts` | Create | US-6.3 |
| `frontend/src/hooks/useAnimatedValue.test.ts` | Create | US-6.3 |
| `frontend/src/components/assembly/AlignmentGuides.tsx` | Create | US-6.2 |
| `frontend/src/components/assembly/AlignmentGuides.test.tsx` | Create | US-6.2 |
| `frontend/src/components/assembly/AlignmentToolbar.tsx` | Create | US-6.2 |
| `frontend/src/components/assembly/AlignmentToolbar.test.tsx` | Create | US-6.2 |
| `frontend/src/components/assembly/ExplodeToolbar.tsx` | Create | US-6.3 |
| `frontend/src/components/assembly/ExplodeToolbar.test.tsx` | Create | US-6.3 |
| `frontend/src/components/assembly/ExplosionLinesOverlay.tsx` | Create | US-6.3 |
| `frontend/src/components/assembly/InteractiveAssemblyViewer.tsx` | Modify | Both |
| `frontend/src/components/assembly/InteractiveAssemblyViewer.test.tsx` | Modify | Both |
| `frontend/src/components/viewer/PartTransformControls.tsx` | Modify | US-6.2 |
| `frontend/src/components/viewer/PartTransformControls.test.tsx` | Modify | US-6.2 |
| `frontend/e2e/assembly-viewer-alignment.spec.ts` | Create | US-6.2 |
| `frontend/e2e/assembly-viewer-exploded.spec.ts` | Create | US-6.3 |

---

## Appendix B: Implementation Checklist

### Phase 1: Foundation (US-6.3 - Exploded View)

- [ ] Create `useAnimatedValue` hook with tests
- [ ] Create `useExplodedView` hook with tests
- [ ] Create `ExplodeToolbar` component with tests
- [ ] Modify `InteractiveAssemblyViewer` to use new hook
- [ ] Add `E` and `Shift+E` keyboard shortcuts
- [ ] Verify `prefers-reduced-motion` support
- [ ] Create E2E tests

### Phase 2: Alignment System (US-6.2)

- [ ] Create spatial hash grid utility
- [ ] Create `useAlignmentGuides` hook with tests
- [ ] Create `AlignmentGuides` Three.js component with tests
- [ ] Create `AlignmentToolbar` component with tests
- [ ] Extend `PartTransformControls` with new props
- [ ] Integrate into `InteractiveAssemblyViewer`
- [ ] Add `A` and `Alt` key handlers
- [ ] Create E2E tests

### Phase 3: Polish & QA

- [ ] Performance profiling with 50+ part assemblies
- [ ] Accessibility audit (screen reader, keyboard, reduced motion)
- [ ] Cross-browser testing (Chrome, Firefox, Safari, Edge)
- [ ] Visual regression tests for guide rendering
- [ ] Documentation update

---

*End of Technical Architecture Document*
