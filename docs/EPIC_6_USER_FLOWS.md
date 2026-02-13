# Epic 6: User Flows - Visual Guide

## Flow 1: Precision Part Alignment (Happy Path)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PRECISION PART ALIGNMENT                         │
└─────────────────────────────────────────────────────────────────────┘

User Goal: Align "Base Plate" to "Bracket" with 10mm spacing

Step 1: Select Part
┌──────────────────────┐
│  Assembly Viewer     │
│  ┌────────┐         │     User clicks "Base Plate"
│  │ Base   │ Bracket │  ──────────────────────────────►
│  │ Plate  │         │
│  └────────┘         │
└──────────────────────┘

Step 2: Activate Move Mode + Axis Lock
┌──────────────────────┐
│  Assembly Viewer     │
│  ┌────────┐         │     User presses: G (move), X (lock X-axis)
│  │ Base   │ Bracket │  ──────────────────────────────►
│  │ Plate⚡│         │     Result: Red X-axis glows, "🔒 X-AXIS" badge appears
│  └────────┘         │
│  🔒 X-AXIS          │
└──────────────────────┘

Step 3: Drag with Visual Alignment
┌──────────────────────┐
│  Assembly Viewer     │     User drags part to the right
│     ┌─────┐ Bracket │  ──────────────────────────────►
│     │Base │         │     Result: Cyan alignment guide appears
│  ━━━│Plate│━━━━━━━━│━━   Distance label shows "10mm"
│     └─────┘         │
│     👆 10mm         │
└──────────────────────┘

Step 4: Snap & Release
┌──────────────────────┐
│  Assembly Viewer     │     Guide turns solid, parts snap
│     ┌─────┐┌───────┐│  ──────────────────────────────►
│     │Base ││Bracket││     User releases mouse
│  ━━━│Plate││       ││━━   Transform committed to undo history
│     └─────┘└───────┘│
│     ✨ Snapped!     │
└──────────────────────┘

Step 5: Fine-Tune with Numeric Input
┌──────────────────────┐
│  Assembly Viewer     │     User presses: N (numeric dialog)
│     ┌─────┐┌───────┐│  ──────────────────────────────►
│     │Base ││Bracket││
│     └─────┘└───────┘│
│                      │
│  ┌────────────────┐ │
│  │ Transform      │ │     User types: X = 25, Y = 50, Z = 0
│  │ Position (mm)  │ │     User presses: Enter
│  │ X: [25___]     │ │  ──────────────────────────────►
│  │ Y: [50___]     │ │     Result: Part moves to exact coordinates
│  │ Z: [0____]     │ │
│  │   [Apply]      │ │
│  └────────────────┘ │
└──────────────────────┘

Step 6: Success!
┌──────────────────────┐
│  Assembly Viewer     │     ✅ Parts aligned precisely
│     ┌─────┐┌───────┐│     ✅ No drift on Y/Z axes
│     │Base ││Bracket││     ✅ Change recorded in undo history
│     └─────┘└───────┘│     ✅ User can undo with Ctrl+Z if needed
│  ✅ Positioned at    │
│     X:25 Y:50 Z:0   │
└──────────────────────┘

═══════════════════════════════════════════════════════════════════════
Time Saved: ~30 seconds (vs manual measurement + trial-and-error)
Error Rate: <5% (vs 15% without guides)
═══════════════════════════════════════════════════════════════════════
```

---

## Flow 2: Assembly Exploration with Exploded View

```
┌─────────────────────────────────────────────────────────────────────┐
│              ASSEMBLY EXPLORATION (8-part enclosure)                │
└─────────────────────────────────────────────────────────────────────┘

Step 1: Initial Assembled View
┌──────────────────────┐
│   ┌─────────────┐   │     User sees complete enclosure
│   │ ┌─────────┐ │   │     Internal structure hidden
│   │ │ ┌─────┐ │ │   │  
│   │ │ │     │ │ │   │
│   │ │ └─────┘ │ │   │
│   │ └─────────┘ │   │
│   └─────────────┘   │
│                      │
└──────────────────────┘

Step 2: Activate Exploded View
┌──────────────────────┐
│                      │     User clicks: Expand button
│   ┌─────────────┐   │  ──────────────────────────────►
│   │ ┌─────────┐ │   │     Result: Slider appears
│   │ │ ┌─────┐ │ │   │     Animation plays: 0% → 100% (1 second)
│   │ │ │     │ │ │   │
│   │ │ └─────┘ │ │   │
│   │ └─────────┘ │   │
│   └─────────────┘   │
│  [━━━━━●━━━━━] 100% │
└──────────────────────┘

Step 3: Parts Separate (Exploded)
┌──────────────────────┐
│   Top Cover ↑       │     Parts explode radially from center
│                      │     Spacing: 50mm (100% factor)
│   ┌───┐  ┌───┐ PCB  │     Camera auto-fits to show all parts
│   │   │  │   │ ↗    │
│   └───┘  └───┘      │
│     Plate  Mount    │
│      ↓   Base ↓     │
│  [━━━━━●━━━━━] 100% │
└──────────────────────┘

Step 4: Increase Explosion Distance
┌──────────────────────┐
│   Top Cover ↑↑      │     User drags slider to 150%
│                      │  ──────────────────────────────►
│                      │     Parts separate further in real-time
│   ┌───┐      ┌───┐  │     No lag, smooth 60fps
│   │   │      │   │↗↗│
│   └───┘      └───┘  │
│     Plate    Mount  │
│      ↓↓   Base ↓↓   │
│  [━━━━━━━●━━] 150%  │
└──────────────────────┘

Step 5: Hide Specific Part
┌──────────────────────┐
│   Top Cover ↑↑      │     User clicks "PCB" part
│                      │     User presses: H (hide)
│                      │  ──────────────────────────────►
│   ┌───┐      [✕]    │     Result: PCB fades out
│   │   │             │     Bottom-left shows "(1 hidden)"
│   └───┘             │
│     Plate    Mount  │
│      ↓↓   Base ↓↓   │
│  8 components (1 hidden)
└──────────────────────┘

Step 6: Animate Back
┌──────────────────────┐
│   Top Cover ↑↑      │     User clicks: Animate button
│                      │  ──────────────────────────────►
│   ┌───┐      [✕]    │     Animation: 150% → 0% over 3 seconds
│   │   │             │     Easing: cubic ease-in-out
│   └───┘             │
│     Plate    Mount  │
│      ↓↓   Base ↓↓   │
│  [▶️ Animating...]   │
└──────────────────────┘

Step 7: Collapsed + Show All
┌──────────────────────┐
│   ┌─────────────┐   │     User presses: Shift+H (show all)
│   │ ┌─────────┐ │   │  ──────────────────────────────►
│   │ │ ┌─PCB─┐ │ │   │     Result: All parts visible + assembled
│   │ │ │     │ │ │   │     User now understands internal structure ✅
│   │ │ └─────┘ │ │   │
│   │ └─────────┘ │   │
│   └─────────────┘   │
│  [━●━━━━━━━━━] 0%   │
└──────────────────────┘

═══════════════════════════════════════════════════════════════════════
Usage Increase: 20% → 50% of sessions use exploded view
Learning Time: -40% to understand assembly structure
═══════════════════════════════════════════════════════════════════════
```

---

## Flow 3: Constraint Verification (P2 Feature)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CONSTRAINT VERIFICATION                          │
└─────────────────────────────────────────────────────────────────────┘

Step 1: Enable Constraint Display
┌──────────────────────┐
│  Assembly Viewer     │     User presses: C (toggle constraints)
│                      │  ──────────────────────────────►
│   Rail ━━━━━━━━━━   │     Result: Constraint icons appear
│        ⇄            │     ⇄ = Slide constraint (blue)
│   ┌─Slider───┐      │
│   └──────────┘      │
└──────────────────────┘

Step 2: Inspect Constraint
┌──────────────────────┐
│  Assembly Viewer     │     User hovers over ⇄ icon
│                      │  ──────────────────────────────►
│   Rail ━━━━━━━━━━   │     Tooltip appears
│        ⇄            │
│   ┌─Slider───┐      │     "Slide: Slider → Rail"
│   └──────────┘      │     "Axis: X"
│                      │     "Range: -50 to 50mm"
│   [Slide: X-axis]   │
│   [-50 to 50mm]     │
└──────────────────────┘

Step 3: Verify Constraint Behavior
┌──────────────────────┐
│  Assembly Viewer     │     User selects Slider part
│                      │     User presses: G (move), X (lock X)
│   Rail ━━━━━━━━━━   │  ──────────────────────────────►
│        ⇄            │     User drags along X-axis
│      ┌─Slider─┐     │     Movement matches constraint ✅
│      └────────┘     │
│   🔒 X-AXIS         │
└──────────────────────┘

═══════════════════════════════════════════════════════════════════════
Benefit: Visual confirmation of assembly relationships
Note: Constraints are view-only (editing happens in CAD software)
═══════════════════════════════════════════════════════════════════════
```

---

## Keyboard Shortcuts Quick Reference

```
┌────────────────────────────────────────────────────────────────┐
│                    KEYBOARD SHORTCUTS                          │
├────────────────────────────────────────────────────────────────┤
│  Transform Mode                                                │
│  ├─ G             Switch to Move mode                          │
│  ├─ R             Switch to Rotate mode                        │
│  └─ S             Toggle snapping on/off                       │
│                                                                 │
│  Axis Locking (NEW!)                                           │
│  ├─ X             Lock to X-axis                               │
│  ├─ Y             Lock to Y-axis                               │
│  ├─ Z             Lock to Z-axis                               │
│  ├─ Shift+X       Lock to Y-Z plane                            │
│  ├─ Shift+Y       Lock to X-Z plane                            │
│  └─ Shift+Z       Lock to X-Y plane                            │
│                                                                 │
│  Numeric Input (NEW!)                                          │
│  └─ N             Open numeric transform dialog                │
│                                                                 │
│  Exploded View (NEW!)                                          │
│  ├─ E             Toggle exploded view on/off                  │
│  ├─ [             Decrease explosion by 10%                    │
│  ├─ ]             Increase explosion by 10%                    │
│  └─ Shift+E       Start/stop animation                         │
│                                                                 │
│  Constraints (NEW!)                                            │
│  ├─ C             Toggle constraint visibility                 │
│  └─ Shift+C       Open constraints panel                       │
│                                                                 │
│  Visibility (Existing)                                         │
│  ├─ H             Hide selected component                      │
│  ├─ Shift+H       Show all components                          │
│  └─ I             Isolate selected component                   │
│                                                                 │
│  Selection Sets (NEW!)                                         │
│  ├─ Ctrl+G        Create set from selection                    │
│  └─ 1-9           Select set 1-9                               │
│                                                                 │
│  Undo/Redo (Existing)                                          │
│  ├─ Ctrl+Z        Undo last transform                          │
│  └─ Ctrl+Y        Redo last transform                          │
│     Ctrl+Shift+Z                                               │
└────────────────────────────────────────────────────────────────┘
```

---

## Error State Handling

```
┌────────────────────────────────────────────────────────────────┐
│                     ERROR SCENARIOS                            │
├────────────────────────────────────────────────────────────────┤
│  1. No Part Selected                                           │
│     User presses: X, Y, Z, N                                   │
│     → No action (shortcuts ignored)                            │
│     → Tooltip: "Select a part first"                           │
│                                                                 │
│  2. Invalid Numeric Input                                      │
│     User types: "abc" in position field                        │
│     → Red border on field                                      │
│     → Error message: "Must be a number"                        │
│     → Apply button disabled                                    │
│                                                                 │
│  3. Alignment Guide Computation Fails                          │
│     Geometry error (invalid mesh)                              │
│     → Silently disable guides                                  │
│     → Toast: "Alignment guides temporarily unavailable"        │
│     → Log error to Sentry                                      │
│                                                                 │
│  4. Transform Out of Bounds                                    │
│     User enters X = 50000 (exceeds max 10000)                  │
│     → Red border, error: "Value must be between -10000 and 10000" │
│     → Prevent submission                                       │
│                                                                 │
│  5. Single Part Assembly                                       │
│     User clicks Explode with 1 part                            │
│     → Explode button disabled (grayed out)                     │
│     → Tooltip: "Requires 2+ parts"                             │
│                                                                 │
│  6. Constraint API Failure (Network Error)                     │
│     Backend /constraints endpoint returns 500                  │
│     → Show toast: "Failed to load constraints"                 │
│     → Retry button in panel                                    │
│     → Graceful degradation (rest of viewer works)              │
└────────────────────────────────────────────────────────────────┘
```

---

## Mobile Touch Gestures

```
┌────────────────────────────────────────────────────────────────┐
│                   MOBILE INTERACTIONS                          │
├────────────────────────────────────────────────────────────────┤
│  Viewing                                                       │
│  ├─ Single drag         Rotate view (existing)                │
│  ├─ Two-finger drag     Pan view (existing)                   │
│  └─ Pinch              Zoom in/out (existing)                 │
│                                                                 │
│  Part Transform (NEW!)                                         │
│  ├─ Long-press part (1s) → Select part                        │
│  ├─ Long-press axis     → Lock to that axis                   │
│  └─ Drag selected       → Move part                           │
│                                                                 │
│  Exploded View                                                 │
│  └─ Swipe up on slider  → Increase explosion                  │
│                                                                 │
│  Component List                                                │
│  ├─ Swipe up from bottom → Show component panel               │
│  └─ Tap eye icon        → Toggle visibility                   │
└────────────────────────────────────────────────────────────────┘
```

