# Epic 40: Thread Library — Architecture & Security Document

**Epic:** Thread Library
**Sub-Issues:** #247 (Thread Geometry Generator), #248 (Standard Thread Library), #249 (Print-Optimized Thread Profiles)
**Total Story Points:** 11 SP
**Date:** 2026-02-23
**Status:** Draft
**Upstream:** [epic-40-thread-library-strategy.md](epic-40-thread-library-strategy.md)

---

## Table of Contents

1. [File Structure](#1-file-structure)
2. [Data Model Details](#2-data-model-details)
3. [Build123d Thread Geometry](#3-build123d-thread-geometry)
4. [API Architecture](#4-api-architecture)
5. [Security Controls](#5-security-controls)
6. [Testing Strategy](#6-testing-strategy)
7. [Integration Points](#7-integration-points)

---

## 1. File Structure

### 1.1 New Backend Files

| File | Sub-Issue | Purpose |
|------|-----------|---------|
| `backend/app/cad/threads.py` | #248 | `ThreadSpec` frozen dataclass, `ThreadFamily`/`ThreadForm`/`ThreadType`/`PitchSeries` enums, all thread data dicts (`ISO_METRIC_COARSE`, `ISO_METRIC_FINE`, `UNC_THREADS`, `UNF_THREADS`, `NPT_THREADS`, `BSPP_THREADS`, `BSPT_THREADS`, `ACME_THREADS`, `TRAPEZOIDAL_THREADS`), `THREAD_REGISTRY`, and lookup functions (`get_thread_spec()`, `list_thread_sizes()`, `list_thread_families()`) |
| `backend/app/cad/thread_generator.py` | #247 | `ThreadGeneratorConfig` dataclass, `generate_thread()` entry-point function, internal helpers `_build_thread_profile()`, `_create_helix_path()`, `_sweep_thread()`, `_add_chamfer_lead_in()`, `_generate_tapered_thread()`. Returns `ThreadGenerationResult` (Part + metadata). |
| `backend/app/cad/thread_print_optimizer.py` | #249 | `PrintProcess`/`ToleranceClass` enums, `PrintThreadConfig` dataclass, `PrintThreadResult` dataclass, `optimize_thread_for_print()` function, `get_print_recommendation()` function, clearance defaults dicts, feasibility rating logic |
| `backend/app/schemas/threads.py` | All | Pydantic request/response models for every API endpoint (see §4.3) |
| `backend/app/api/v2/threads.py` | All | FastAPI `APIRouter` with all 7 endpoints (see §4.1) |
| `backend/app/seeds/threads.py` | #248 | `seed_thread_standards()` async function following `components_v2.py` upsert pattern; syncs `THREAD_REGISTRY` → `ReferenceComponent` rows with `category="thread_standard"` |

### 1.2 New Test Files

| File | Purpose |
|------|---------|
| `backend/tests/cad/test_threads.py` | Thread data completeness, dimensional accuracy spot-checks, lookup functions, error handling |
| `backend/tests/cad/test_thread_generator.py` | Geometry generation for each family, internal/external, edge cases, timeout, performance |
| `backend/tests/cad/test_thread_print_optimizer.py` | FDM/SLA clearance, tolerance classes, min-size warnings, chamfer, flat-bottom |
| `backend/tests/api/test_threads_api.py` | All 7 endpoints: success, validation errors, auth, rate limiting, 404 on unknown thread |
| `backend/tests/seeds/test_thread_seeds.py` | Seed idempotency, correct category/subcategory, JSONB contents |

### 1.3 Existing Files Modified

| File | Change |
|------|--------|
| `backend/app/cad/__init__.py` | No change—`threads.py` is a standalone module under `app.cad`, does not need a deprecation warning (it's new v1 CAD code, not CadQuery legacy) |
| `backend/app/api/v2/__init__.py` | Add `from app.api.v2.threads import router as threads_router` and `api_router.include_router(threads_router, prefix="/threads", tags=["v2-threads"])` |
| `backend/app/cad/hardware.py` | **No modifications**. Thread library is a separate module. Backward compatibility preserved. |
| `backend/app/cad/exceptions.py` | Add `ThreadGenerationError(CADError)` and `ThreadDataError(CADError)` exception classes |

### 1.4 New Frontend Files

| File | Purpose |
|------|---------|
| `frontend/src/lib/api/threads.ts` | API client: `fetchThreadFamilies()`, `fetchThreadSizes()`, `fetchThreadSpec()`, `fetchTapDrill()`, `generateThread()`, `generatePrintOptimizedThread()`, `fetchPrintRecommendation()` |
| `frontend/src/hooks/useThreadFamilies.ts` | React Query `useQuery` wrapper for families listing |
| `frontend/src/hooks/useThreadSpec.ts` | React Query `useQuery` wrapper for individual spec |
| `frontend/src/hooks/useThreadGenerate.ts` | React Query `useMutation` wrapper for POST endpoints |
| `frontend/src/components/threads/ThreadWizard.tsx` | Multi-step modal (family → size → print opts → preview) |
| `frontend/src/components/threads/ThreadFamilySelector.tsx` | Card grid of families |
| `frontend/src/components/threads/ThreadSizeSelector.tsx` | Size dropdown + quick-select + live spec panel |
| `frontend/src/components/threads/PrintOptimizationForm.tsx` | FDM/SLA config, tolerance, flat-bottom toggle |
| `frontend/src/components/threads/ThreadPreview3D.tsx` | React Three Fiber rendering of thread cross-section |
| `frontend/src/components/threads/TapDrillReference.tsx` | Read-only spec table for tap drill + clearance holes |
| `frontend/src/types/threads.ts` | TypeScript interfaces (`ThreadFamily`, `ThreadSpec`, `ThreadGenerateRequest`, etc.) |

### 1.5 New Frontend Test Files

| File | Purpose |
|------|---------|
| `frontend/src/components/threads/__tests__/ThreadWizard.test.tsx` | Step navigation, form submission, validation |
| `frontend/src/components/threads/__tests__/ThreadFamilySelector.test.tsx` | Renders families, selection callback |
| `frontend/src/components/threads/__tests__/ThreadSizeSelector.test.tsx` | Dropdown behavior, spec display, edge cases |
| `frontend/src/components/threads/__tests__/PrintOptimizationForm.test.tsx` | Toggle states, clearance display, validation |
| `frontend/src/components/threads/__tests__/TapDrillReference.test.tsx` | Data rendering, empty state |
| `frontend/src/hooks/__tests__/useThreadFamilies.test.ts` | Query firing, loading/error states |
| `frontend/src/hooks/__tests__/useThreadSpec.test.ts` | Parameter propagation, cache keys |
| `frontend/src/hooks/__tests__/useThreadGenerate.test.ts` | Mutation lifecycle, error mapping |

---

## 2. Data Model Details

### 2.1 Enums

All enums use `StrEnum` (matching `HardwareType`, `ScrewHead`, etc. in `hardware.py`).

```python
# backend/app/cad/threads.py

from enum import StrEnum


class ThreadFamily(StrEnum):
    """Thread standard families."""
    ISO_METRIC = "iso_metric"
    UNC = "unc"
    UNF = "unf"
    NPT = "npt"
    BSPP = "bspp"
    BSPT = "bspt"
    ACME = "acme"
    TRAPEZOIDAL = "trapezoidal"


class ThreadType(StrEnum):
    """Direction of thread engagement."""
    INTERNAL = "internal"
    EXTERNAL = "external"


class PitchSeries(StrEnum):
    """Pitch series for metric threads only."""
    COARSE = "coarse"
    FINE = "fine"
    SUPERFINE = "superfine"


class ThreadForm(StrEnum):
    """Thread profile cross-section geometry."""
    TRIANGULAR = "triangular"      # ISO metric, UNC, UNF (60° V)
    TRUNCATED_TRIANGULAR = "truncated_triangular"  # Practical ISO (flattened crests/roots)
    TRAPEZOIDAL = "trapezoidal"    # Trapezoidal / metric trapezoidal (30° included)
    ACME = "acme"                  # ACME (29° included)
    NPT = "npt"                    # Tapered 60° V (truncated)
    SQUARE = "square"              # Square thread (rare, for completeness)


class ThreadHand(StrEnum):
    """Thread helix direction."""
    RIGHT = "right"
    LEFT = "left"
```

### 2.2 `ThreadSpec` Frozen Dataclass

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ThreadSpec:
    """
    Complete specification for a single standard thread size.

    All linear dimensions in millimeters.
    Follows ISO 261 naming conventions where applicable.

    This is the shared contract between #247 (generator), #248 (data),
    and #249 (print optimizer).
    """

    # --- Identity ---
    family: ThreadFamily
    size: str                                # "M8", "1/4-20", "1/2 NPT"
    pitch_mm: float                          # Thread pitch in mm
    form: ThreadForm = ThreadForm.TRIANGULAR
    pitch_series: PitchSeries | None = None  # coarse/fine/superfine (metric only)

    # --- External thread diameters ---
    major_diameter: float = 0.0              # Nominal / major Ø
    pitch_diameter_ext: float = 0.0          # Pitch Ø (external)
    minor_diameter_ext: float = 0.0          # Minor Ø (external)

    # --- Internal thread diameters ---
    major_diameter_int: float = 0.0          # Major Ø (internal, = nominal for parallel)
    pitch_diameter_int: float = 0.0          # Pitch Ø (internal)
    minor_diameter_int: float = 0.0          # Minor Ø (internal)

    # --- Thread profile geometry ---
    profile_angle_deg: float = 60.0          # Full thread angle (60° ISO/UNC/UNF, 29° ACME, 30° trap)
    taper_per_mm: float = 0.0               # Taper rate in mm/mm (NPT/BSPT); 0.0 = parallel

    # --- Drill and clearance sizes ---
    tap_drill_mm: float = 0.0               # Recommended tap drill Ø
    clearance_hole_close_mm: float = 0.0     # Close-fit clearance hole Ø
    clearance_hole_medium_mm: float = 0.0    # Medium-fit clearance hole Ø
    clearance_hole_free_mm: float = 0.0      # Free-fit clearance hole Ø

    # --- Imperial convenience (populated for UNC/UNF/NPT/BSP/ACME) ---
    tpi: float | None = None                 # Threads per inch
    nominal_size_inch: str | None = None     # "1/4", "#10", "3/4"

    # --- Taper engagement (NPT/BSPT only) ---
    engagement_length_mm: float = 0.0        # Hand-tight engagement length

    # --- Metadata ---
    standard_ref: str = ""                   # "ISO 261", "ASME B1.1"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for API/DB storage.

        Returns:
            Dictionary with all spec fields suitable for JSONB storage.
        """
        result: dict[str, Any] = {
            "family": self.family.value,
            "size": self.size,
            "pitch_mm": self.pitch_mm,
            "form": self.form.value,
            "profile_angle_deg": self.profile_angle_deg,
            "major_diameter": self.major_diameter,
            "pitch_diameter_ext": self.pitch_diameter_ext,
            "minor_diameter_ext": self.minor_diameter_ext,
            "major_diameter_int": self.major_diameter_int,
            "pitch_diameter_int": self.pitch_diameter_int,
            "minor_diameter_int": self.minor_diameter_int,
            "taper_per_mm": self.taper_per_mm,
            "tap_drill_mm": self.tap_drill_mm,
            "clearance_hole_close_mm": self.clearance_hole_close_mm,
            "clearance_hole_medium_mm": self.clearance_hole_medium_mm,
            "clearance_hole_free_mm": self.clearance_hole_free_mm,
            "standard_ref": self.standard_ref,
        }
        if self.pitch_series is not None:
            result["pitch_series"] = self.pitch_series.value
        if self.tpi is not None:
            result["tpi"] = self.tpi
        if self.nominal_size_inch is not None:
            result["nominal_size_inch"] = self.nominal_size_inch
        if self.engagement_length_mm:
            result["engagement_length_mm"] = self.engagement_length_mm
        if self.notes:
            result["notes"] = self.notes
        return result
```

### 2.3 Thread Data Organization

Data dicts are keyed by size string, each value is a `ThreadSpec` instance. This mirrors
`METRIC_SOCKET_HEAD_SCREWS` and `THREADED_INSERTS` in `hardware.py`, but with richer frozen-dataclass
values instead of tuples.

```python
# === ISO Metric Coarse (ISO 261) ===
ISO_METRIC_COARSE: dict[str, ThreadSpec] = {
    "M2": ThreadSpec(
        family=ThreadFamily.ISO_METRIC,
        size="M2",
        pitch_mm=0.4,
        form=ThreadForm.TRUNCATED_TRIANGULAR,
        pitch_series=PitchSeries.COARSE,
        major_diameter=2.0,
        pitch_diameter_ext=1.740,
        minor_diameter_ext=1.509,
        major_diameter_int=2.0,
        pitch_diameter_int=1.740,
        minor_diameter_int=1.567,
        tap_drill_mm=1.6,
        clearance_hole_close_mm=2.2,
        clearance_hole_medium_mm=2.4,
        clearance_hole_free_mm=2.6,
        standard_ref="ISO 261",
    ),
    # M2.5, M3, M3.5, M4, M5, M6, M8, M10, M12, M14, M16, M18, M20,
    # M22, M24, M27, M30, M33, M36, M39, M42, M45, M48, M52, M56, M60, M64, M68
    # ... (all sizes from M1 to M68 per ISO 261 preferred series)
}

# === ISO Metric Fine ===
ISO_METRIC_FINE: dict[str, ThreadSpec] = {
    "M8x1.0": ThreadSpec(
        family=ThreadFamily.ISO_METRIC,
        size="M8x1.0",
        pitch_mm=1.0,
        form=ThreadForm.TRUNCATED_TRIANGULAR,
        pitch_series=PitchSeries.FINE,
        major_diameter=8.0,
        pitch_diameter_ext=7.350,
        minor_diameter_ext=6.773,
        major_diameter_int=8.0,
        pitch_diameter_int=7.350,
        minor_diameter_int=6.917,
        tap_drill_mm=7.0,
        clearance_hole_close_mm=8.4,
        clearance_hole_medium_mm=9.0,
        clearance_hole_free_mm=10.0,
        standard_ref="ISO 261",
    ),
    # M10x1.0, M10x1.25, M12x1.25, M12x1.5, etc.
}

# === UNC (ASME B1.1) ===
UNC_THREADS: dict[str, ThreadSpec] = {
    "1/4-20": ThreadSpec(
        family=ThreadFamily.UNC,
        size="1/4-20",
        pitch_mm=1.27,  # 25.4 / 20
        form=ThreadForm.TRIANGULAR,
        major_diameter=6.35,
        tpi=20,
        nominal_size_inch="1/4",
        standard_ref="ASME B1.1",
        # ... remaining diameters per ASME B1.1
    ),
    # #1-64, #2-56, #3-48, #4-40, #5-40, #6-32, #8-32, #10-24, #10-32,
    # 1/4-20, 5/16-18, 3/8-16, 7/16-14, 1/2-13, 9/16-12, 5/8-11, 3/4-10,
    # 7/8-9, 1"-8, 1-1/8"-7, 1-1/4"-7, 1-3/8"-6, 1-1/2"-6, ...
}

# === UNF (ASME B1.1) ===
UNF_THREADS: dict[str, ThreadSpec] = { ... }

# === NPT (ASME B1.20.1) ===
NPT_THREADS: dict[str, ThreadSpec] = {
    "1/4": ThreadSpec(
        family=ThreadFamily.NPT,
        size="1/4",
        pitch_mm=1.411,  # 25.4 / 18
        form=ThreadForm.NPT,
        profile_angle_deg=60.0,
        taper_per_mm=0.0625,  # 1:16 = 0.0625 mm/mm per side
        major_diameter=13.616,
        tpi=18,
        nominal_size_inch="1/4",
        engagement_length_mm=10.2,
        standard_ref="ASME B1.20.1",
    ),
    # 1/16", 1/8", 3/8", 1/2", 3/4", 1", 1-1/4", 1-1/2", 2"
}

# === BSPP (ISO 228-1) & BSPT (ISO 7-1) ===
BSPP_THREADS: dict[str, ThreadSpec] = { ... }
BSPT_THREADS: dict[str, ThreadSpec] = { ... }

# === ACME (ASME B1.5) ===
ACME_THREADS: dict[str, ThreadSpec] = {
    "1/4-16": ThreadSpec(
        family=ThreadFamily.ACME,
        size="1/4-16",
        pitch_mm=1.5875,  # 25.4 / 16
        form=ThreadForm.ACME,
        profile_angle_deg=29.0,
        major_diameter=6.35,
        tpi=16,
        nominal_size_inch="1/4",
        standard_ref="ASME B1.5",
    ),
    # Through 5"-2
}

# === Trapezoidal (ISO 2904) ===
TRAPEZOIDAL_THREADS: dict[str, ThreadSpec] = {
    "Tr8x1.5": ThreadSpec(
        family=ThreadFamily.TRAPEZOIDAL,
        size="Tr8x1.5",
        pitch_mm=1.5,
        form=ThreadForm.TRAPEZOIDAL,
        profile_angle_deg=30.0,
        major_diameter=8.0,
        standard_ref="ISO 2904",
    ),
    # Through Tr100x12
}
```

### 2.4 Lookup Registry and Functions

```python
# === Unified registry ===
THREAD_REGISTRY: dict[ThreadFamily, dict[str, ThreadSpec]] = {
    ThreadFamily.ISO_METRIC: {**ISO_METRIC_COARSE, **ISO_METRIC_FINE},
    ThreadFamily.UNC: UNC_THREADS,
    ThreadFamily.UNF: UNF_THREADS,
    ThreadFamily.NPT: NPT_THREADS,
    ThreadFamily.BSPP: BSPP_THREADS,
    ThreadFamily.BSPT: BSPT_THREADS,
    ThreadFamily.ACME: ACME_THREADS,
    ThreadFamily.TRAPEZOIDAL: TRAPEZOIDAL_THREADS,
}

# === Family metadata (for API /families endpoint) ===
THREAD_FAMILY_INFO: dict[ThreadFamily, dict[str, Any]] = {
    ThreadFamily.ISO_METRIC: {
        "name": "ISO Metric",
        "description": "ISO 261 metric threads, coarse and fine pitch",
        "standard_ref": "ISO 261 / ISO 724",
        "pitch_series": ["coarse", "fine"],
    },
    ThreadFamily.UNC: {
        "name": "Unified National Coarse",
        "description": "American standard coarse threads",
        "standard_ref": "ASME B1.1",
        "pitch_series": [],
    },
    # ... all families
}


def get_thread_spec(
    family: ThreadFamily,
    size: str,
    pitch_series: PitchSeries | None = None,
) -> ThreadSpec:
    """
    Look up a thread specification by family and size.

    For ISO metric, if pitch_series is specified and size lacks a pitch suffix,
    the appropriate dict (coarse/fine) is searched first.

    Args:
        family: Thread standard family.
        size: Thread size designator (e.g., "M8", "1/4-20").
        pitch_series: Optional pitch series filter (metric only).

    Returns:
        Matching ThreadSpec.

    Raises:
        ThreadDataError: If family or size not found in registry.
    """
    ...


def list_thread_sizes(
    family: ThreadFamily,
    pitch_series: PitchSeries | None = None,
) -> list[str]:
    """
    List all available size designators for a thread family.

    Args:
        family: Thread standard family.
        pitch_series: Filter metric sizes by coarse/fine.

    Returns:
        Sorted list of size strings.

    Raises:
        ThreadDataError: If family not found.
    """
    ...


def list_thread_families() -> list[ThreadFamily]:
    """Return all supported thread families."""
    return list(THREAD_REGISTRY.keys())
```

### 2.5 Integration with Existing `hardware.py`

**Decision: Separate module, no modifications to `hardware.py`.**

Rationale:
- `hardware.py` stores fastener _hardware_ specs (screws, inserts, standoffs) as simple tuples.
- `threads.py` stores _thread standard dimensional data_ as rich frozen dataclasses.
- The two concerns are related but distinct. Thread data is 10+ fields per entry; hardware tuples are 3-4 fields.
- Cross-references are maintained at read time: `threads.py` tap drill values must match `hardware.py` `TAP_DRILL_SIZES` for overlapping sizes (M2–M10). This is enforced by a consistency test in `test_threads.py`.

Consistency contract (tested):

```python
# test_threads.py::TestThreadHardwareConsistency
def test_tap_drill_matches_hardware_py():
    """Thread library tap drill values must match hardware.py TAP_DRILL_SIZES."""
    from app.cad.hardware import TAP_DRILL_SIZES
    for size, expected_drill in TAP_DRILL_SIZES.items():
        spec = get_thread_spec(ThreadFamily.ISO_METRIC, size)
        assert spec.tap_drill_mm == pytest.approx(expected_drill, abs=0.05)

def test_clearance_hole_matches_hardware_py():
    """Thread library close-fit clearance holes must match hardware.py CLEARANCE_HOLES."""
    from app.cad.hardware import CLEARANCE_HOLES
    for size, expected_hole in CLEARANCE_HOLES.items():
        spec = get_thread_spec(ThreadFamily.ISO_METRIC, size)
        assert spec.clearance_hole_close_mm == pytest.approx(expected_hole, abs=0.1)
```

### 2.6 Database Representation

No new tables. Thread specs seed into the existing `ReferenceComponent` model:

| `ReferenceComponent` Field | Value |
|---------------------------|-------|
| `category` | `"thread_standard"` |
| `subcategory` | Family value (e.g., `"iso_metric"`, `"unc"`) |
| `name` | Size + pitch label (e.g., `"M8x1.25 Coarse"`, `"1/4-20 UNC"`) |
| `source_type` | `"library"` |
| `dimensions` (JSONB) | Full `ThreadSpec.to_dict()` output |
| `mounting_specs` (JSONB) | `{"tap_drill_mm": ..., "clearance_holes": {...}}` |
| `tags` (JSONB) | `["metric", "coarse", "M8", "iso_261"]` |

---

## 3. Build123d Thread Geometry

### 3.1 Architecture of `thread_generator.py`

```python
# backend/app/cad/thread_generator.py

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from build123d import Part

from app.cad.exceptions import ThreadGenerationError, ValidationError
from app.cad.threads import ThreadFamily, ThreadHand, ThreadSpec, ThreadType

logger = logging.getLogger(__name__)

# === Constants ===
MAX_THREAD_LENGTH_MM: float = 200.0
MAX_REVOLUTIONS: int = 500
GENERATION_TIMEOUT_SECONDS: float = 60.0
DEFAULT_SEGMENTS_PER_REVOLUTION: int = 64


@dataclass(frozen=True)
class ThreadGeneratorConfig:
    """
    Configuration for generating a single thread.

    Args:
        spec: Thread specification from the library.
        thread_type: Internal or external.
        length_mm: Axial length of the threaded section.
        hand: Right-hand or left-hand helix.
        segments_per_revolution: Tessellation fidelity (higher = smoother, slower).
        add_chamfer: Add 45° lead-in chamfer of 1× pitch length.
        custom_pitch_mm: Override the spec pitch (non-standard threads).
        custom_diameter_mm: Override the spec major diameter.
    """
    spec: ThreadSpec
    thread_type: ThreadType
    length_mm: float
    hand: ThreadHand = ThreadHand.RIGHT
    segments_per_revolution: int = DEFAULT_SEGMENTS_PER_REVOLUTION
    add_chamfer: bool = True
    custom_pitch_mm: float | None = None
    custom_diameter_mm: float | None = None


@dataclass
class ThreadGenerationResult:
    """
    Result of thread geometry generation.

    Attributes:
        part: The Build123d Part object containing thread geometry.
        metadata: Dictionary of computed values (diameters, pitch, length, etc.).
        generation_time_ms: Wall-clock time for geometry creation.
        estimated_face_count: Approximate number of BRep faces.
    """
    part: Part
    metadata: dict[str, Any]
    generation_time_ms: int
    estimated_face_count: int


def generate_thread(config: ThreadGeneratorConfig) -> ThreadGenerationResult:
    """
    Generate 3D thread geometry from a ThreadSpec and configuration.

    This is the primary public entry point for #247.

    The approach:
    1. Build a 2D thread profile sketch (cross-section of one tooth).
    2. Create a helical path (cylindrical for ISO/UNC/UNF, conical for NPT/BSPT).
    3. Sweep the profile along the helix.
    4. Optionally add chamfer/lead-in.
    5. For internal threads, return the thread body as a "cutting tool" shape
       suitable for use with `difference()`.

    Args:
        config: Thread generation configuration.

    Returns:
        ThreadGenerationResult with Part and metadata.

    Raises:
        ValidationError: If config parameters are geometrically invalid.
        ThreadGenerationError: If Build123d/OCCT fails during sweep.
    """
    ...
```

### 3.2 Helix Sweep Approach

The Build123d thread generation uses a **profile sketch + helical sweep** pattern:

```
Step 1: Build 2D Profile       Step 2: Create Helix Path       Step 3: Sweep
┌─────────────┐                ┌──────────────┐                ┌──────────────┐
│    ╱╲       │                │    ╱──╲      │                │  ┌──thread──┐│
│   ╱  ╲      │     +          │   ╱    ╲     │     =          │  │  helix   ││
│  ╱    ╲     │                │  ╱      ╲    │                │  │  body    ││
│ ╱──────╲    │                │ ╱        ╲   │                │  └──────────┘│
│ Profile     │                │  Helix path  │                │   Solid      │
└─────────────┘                └──────────────┘                └──────────────┘
```

#### Step 1 — Thread Profile Sketch (`_build_thread_profile`)

```python
def _build_thread_profile(
    spec: ThreadSpec,
    thread_type: ThreadType,
    pitch_mm: float,
    major_diameter: float,
) -> Sketch:
    """
    Create the 2D cross-section of one thread tooth.

    The profile is constructed on the XZ plane at the pitch radius, with:
    - Width = pitch_mm
    - Height = thread depth (computed from pitch and profile angle)
    - Shape varies by ThreadForm:
        - TRIANGULAR / TRUNCATED_TRIANGULAR: ISO V-thread (60°), with
          flat crests and roots per ISO 68-1 truncation rules
        - ACME: 29° included angle, flat crests and roots
        - TRAPEZOIDAL: 30° included angle, flat crests and roots
        - NPT: 60° V, truncated, same as ISO but on a taper
        - SQUARE: Rectangular profile

    For external threads: profile extends outward from minor Ø to major Ø.
    For internal threads: profile extends inward from major Ø to minor Ø.

    Args:
        spec: Thread specification.
        thread_type: Internal or external.
        pitch_mm: Effective pitch (possibly overridden).
        major_diameter: Effective major diameter (possibly overridden).

    Returns:
        Build123d Sketch of the thread tooth profile.
    """
    ...
```

Thread depth formulas by form:

| Form | Thread Height (H) | Truncation |
|------|-------------------|------------|
| ISO Metric (60°) | H = 0.866025 × P | Crest flat = P/8, root flat = P/4 |
| UNC/UNF (60°) | H = 0.866025 × P | Same as ISO |
| ACME (29°) | H = P/2 + 0.010" clearance | Flat crest = 0.3707 × P, flat root = 0.3707 × P |
| Trapezoidal (30°) | H = P/2 + clearance | Per ISO 2904 |
| NPT (60°) | H = 0.866025 × P | Crest/root truncated by H/8 |

#### Step 2 — Helix Path (`_create_helix_path`)

```python
def _create_helix_path(
    pitch_mm: float,
    length_mm: float,
    radius_mm: float,
    hand: ThreadHand,
    taper_per_mm: float = 0.0,
) -> Wire:
    """
    Create a helical wire path for thread sweep.

    Uses Build123d's Helix constructor for cylindrical threads or a
    custom conical helix for tapered threads (NPT/BSPT).

    Build123d API:
        Helix(pitch, height, radius, center, direction, cone_angle)

    For parallel threads (taper_per_mm == 0):
        helix = Helix(pitch=pitch_mm, height=length_mm, radius=radius_mm)

    For tapered threads (NPT/BSPT, taper_per_mm > 0):
        cone_angle = math.degrees(math.atan(taper_per_mm))
        helix = Helix(pitch=pitch_mm, height=length_mm, radius=radius_mm,
                       cone_angle=cone_angle)

    For left-hand threads:
        The helix direction is negated.

    Args:
        pitch_mm: Thread pitch.
        length_mm: Axial length.
        radius_mm: Starting radius (at pitch diameter).
        hand: Right or left hand.
        taper_per_mm: Taper rate (0 for parallel).

    Returns:
        Build123d Wire representing the helical path.
    """
    ...
```

#### Step 3 — Sweep (`_sweep_thread`)

```python
def _sweep_thread(
    profile: Sketch,
    helix_path: Wire,
) -> Part:
    """
    Sweep a thread profile along a helical path to create 3D geometry.

    Uses Build123d's `sweep()` operation.

    For performance, if the thread has > MAX_REVOLUTIONS turns,
    a segmented approach is used:
    1. Generate one full revolution.
    2. Linear-pattern the single revolution along the axis.
    3. Union/fuse the segments.

    This avoids OCCT's performance cliff on very long sweeps.

    Args:
        profile: 2D thread tooth cross-section.
        helix_path: Helical wire path.

    Returns:
        Build123d Part of the thread body.

    Raises:
        ThreadGenerationError: If OCCT sweep fails.
    """
    ...
```

#### Step 4 — Chamfer Lead-In (`_add_chamfer_lead_in`)

```python
def _add_chamfer_lead_in(
    thread_part: Part,
    spec: ThreadSpec,
    thread_type: ThreadType,
    pitch_mm: float,
) -> Part:
    """
    Add a 45° chamfer/lead-in at the thread start.

    For external threads: chamfer on the leading face (bottom).
    For internal threads: countersink at the entry face (top).

    Chamfer depth = 1 × pitch_mm (one full tooth lead-in).

    Args:
        thread_part: Generated thread geometry.
        spec: Thread specification.
        thread_type: Internal or external.
        pitch_mm: Effective pitch.

    Returns:
        Part with chamfer applied.
    """
    ...
```

### 3.3 Internal vs External Thread Differences

| Aspect | External Thread | Internal Thread |
|--------|-----------------|-----------------|
| **Profile direction** | Extends outward from minor Ø to major Ø | Inward from major Ø to minor Ø |
| **Helix radius** | At pitch diameter of **external** thread | At pitch diameter of **internal** thread |
| **Resulting Part** | Solid threaded shaft (additive) | Hollow threaded bore (cutting tool) |
| **Usage** | `union(shaft, thread_body)` | `difference(block, thread_bore)` |
| **Chamfer** | 45° chamfer on thread tip | Countersink on entry face |
| **Metadata flag** | `"usage": "additive"` | `"usage": "subtractive"` |

For internal threads, the generator returns a solid representing the threaded void.
The consumer calls `difference(target_body, internal_thread_part)` to cut the threads.

### 3.4 Performance Considerations

| Parameter | Limit | Rationale |
|-----------|-------|-----------|
| `MAX_THREAD_LENGTH_MM` | 200 mm | Prevents memory exhaustion; 200mm ÷ 0.4mm pitch = 500 revolutions |
| `MAX_REVOLUTIONS` | 500 | OCCT helix sweep degrades above ~500 turns |
| `GENERATION_TIMEOUT_SECONDS` | 60 s | Hard wall-clock cap; raises `ThreadGenerationError` |
| `DEFAULT_SEGMENTS_PER_REVOLUTION` | 64 | Good visual fidelity; 32 for draft mode, 128 for high quality |
| Estimated face count warning | >100,000 faces | Log warning; suggest reducing length or segments |

**Segmented generation strategy** for threads with > 100 revolutions:

```
1. Generate a single-revolution thread body (2 × pitch_mm height to overlap).
2. Linear-pattern this body along the Z-axis at pitch_mm intervals.
3. Fuse all segments with union().
4. Trim start and end faces to the requested length.
```

This avoids the OCCT helix sweep performance cliff while producing geometrically
identical results.

**Cache strategy:** Generated STEP/STL files are cached by a composite key:

```python
cache_key = f"thread:{family}:{size}:{thread_type}:{length_mm}:{segments}:{hand}"
```

Redis TTL: 24 hours. Cache invalidated on code deployment.

---

## 4. API Architecture

### 4.1 Router Structure

```python
# backend/app/api/v2/threads.py

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_user
from app.core.auth import get_current_user_optional
from app.schemas.threads import (
    PrintOptimizedThreadRequest,
    PrintOptimizedThreadResponse,
    PrintRecommendationResponse,
    TapDrillResponse,
    ThreadFamilyResponse,
    ThreadGenerateRequest,
    ThreadGenerateResponse,
    ThreadSizeListResponse,
    ThreadSpecResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()
```

**Router registration** in `backend/app/api/v2/__init__.py`:

```python
from app.api.v2.threads import router as threads_router

api_router.include_router(threads_router, prefix="/threads", tags=["v2-threads"])
```

### 4.2 Endpoint Implementations

#### `GET /api/v2/threads/families`

```python
@router.get(
    "/families",
    response_model=ThreadFamilyResponse,
    summary="List all thread standard families",
)
async def list_families() -> ThreadFamilyResponse:
    """
    Return all supported thread families with metadata.

    No authentication required — public reference data.
    """
    ...
```

#### `GET /api/v2/threads/standards/{family}`

```python
@router.get(
    "/standards/{family}",
    response_model=ThreadSizeListResponse,
    summary="List available sizes in a thread family",
)
async def list_sizes(
    family: str,
    pitch_series: str | None = Query(None, description="coarse/fine (metric)"),
) -> ThreadSizeListResponse:
    """
    List all available thread sizes for the given family.

    No authentication required — public reference data.

    Raises:
        HTTPException 404: If family is unknown.
    """
    ...
```

#### `GET /api/v2/threads/standards/{family}/{size}`

```python
@router.get(
    "/standards/{family}/{size:path}",
    response_model=ThreadSpecResponse,
    summary="Get full specification for a specific thread",
)
async def get_spec(
    family: str,
    size: str,
) -> ThreadSpecResponse:
    """
    Get complete dimensional data for a specific thread size.

    The `size` path parameter uses `:path` converter to handle
    sizes containing slashes (e.g., "1/4-20").

    No authentication required — public reference data.

    Raises:
        HTTPException 404: If family/size combination not found.
    """
    ...
```

#### `GET /api/v2/threads/tap-drill/{family}/{size}`

```python
@router.get(
    "/tap-drill/{family}/{size:path}",
    response_model=TapDrillResponse,
    summary="Get tap drill and clearance hole information",
)
async def get_tap_drill(
    family: str,
    size: str,
) -> TapDrillResponse:
    """
    Get tap drill sizes and clearance hole diameters.

    No authentication required — public reference data.

    Raises:
        HTTPException 404: If family/size combination not found.
    """
    ...
```

#### `POST /api/v2/threads/generate`

```python
@router.post(
    "/generate",
    response_model=ThreadGenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate thread geometry",
)
async def generate_thread_geometry(
    request: ThreadGenerateRequest,
    current_user: User = Depends(get_current_user),
) -> ThreadGenerateResponse:
    """
    Generate 3D thread geometry and return download links.

    Requires authentication. Rate limited to 10 req/min per user.

    The geometry is generated synchronously for short threads (< 50mm).
    For longer threads, the request is routed through Celery and a job_id
    is returned for polling.

    Args:
        request: Thread generation parameters.
        current_user: Authenticated user (injected).

    Raises:
        HTTPException 400: If parameters are invalid.
        HTTPException 404: If thread family/size not found.
        HTTPException 422: If geometry generation fails.
        HTTPException 429: If rate limit exceeded.
    """
    ...
```

#### `POST /api/v2/threads/generate/print-optimized`

```python
@router.post(
    "/generate/print-optimized",
    response_model=PrintOptimizedThreadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate print-optimized thread geometry",
)
async def generate_print_optimized_thread(
    request: PrintOptimizedThreadRequest,
    current_user: User = Depends(get_current_user),
) -> PrintOptimizedThreadResponse:
    """
    Generate thread geometry with 3D-printing clearance adjustments.

    Requires authentication. Rate limited to 10 req/min per user.

    Applies FDM/SLA/SLS clearance offsets, optional flat-bottom roots,
    and chamfer lead-ins. Returns both original and adjusted dimensions.

    Args:
        request: Print-optimized thread parameters.
        current_user: Authenticated user (injected).

    Raises:
        HTTPException 400: If parameters or print config are invalid.
        HTTPException 404: If thread family/size not found.
        HTTPException 422: If geometry generation fails.
        HTTPException 429: If rate limit exceeded.
    """
    ...
```

#### `GET /api/v2/threads/print-recommendations/{family}/{size}`

```python
@router.get(
    "/print-recommendations/{family}/{size:path}",
    response_model=PrintRecommendationResponse,
    summary="Get print feasibility for a thread",
)
async def get_print_recommendation(
    family: str,
    size: str,
    process: str = Query("fdm", pattern="^(fdm|sla|sls)$"),
) -> PrintRecommendationResponse:
    """
    Return print feasibility rating and recommendations for a thread size.

    No authentication required — public reference data.

    Includes feasibility_rating, recommended_alternatives (e.g., heat-set
    inserts for small threads), orientation, nozzle, and layer height
    recommendations.

    Raises:
        HTTPException 404: If family/size combination not found.
    """
    ...
```

### 4.3 Full Pydantic Schema Definitions

```python
# backend/app/schemas/threads.py

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# === Family listing ===

class ThreadFamilyInfo(BaseModel):
    """Metadata for a single thread standard family."""
    id: str = Field(description="Family identifier (e.g., 'iso_metric')")
    name: str = Field(description="Display name (e.g., 'ISO Metric')")
    description: str = Field(description="Brief description of the standard")
    standard_ref: str = Field(description="Reference standard (e.g., 'ISO 261')")
    pitch_series: list[str] = Field(description="Available pitch series (metric)")
    size_count: int = Field(description="Number of available sizes")


class ThreadFamilyResponse(BaseModel):
    """List of all available thread families."""
    families: list[ThreadFamilyInfo]


# === Size listing ===

class ThreadSizeSummary(BaseModel):
    """Summary of one thread size within a family."""
    size: str = Field(description="Size designator (e.g., 'M8')")
    pitch_mm: float = Field(description="Thread pitch in mm")
    major_diameter_mm: float = Field(description="Major diameter in mm")
    description: str = Field(description="Human-readable label")


class ThreadSizeListResponse(BaseModel):
    """All available sizes for a thread family."""
    family: str
    pitch_series: str | None = None
    sizes: list[ThreadSizeSummary]


# === Full specification ===

class ThreadSpecResponse(BaseModel):
    """Complete dimensional data for a thread size."""
    family: str
    size: str
    pitch_mm: float
    form: str
    pitch_series: str | None = None
    profile_angle_deg: float
    taper_per_mm: float

    # External diameters
    major_diameter: float
    pitch_diameter_ext: float
    minor_diameter_ext: float

    # Internal diameters
    major_diameter_int: float
    pitch_diameter_int: float
    minor_diameter_int: float

    # Drill and clearance
    tap_drill_mm: float
    clearance_hole_close_mm: float
    clearance_hole_medium_mm: float
    clearance_hole_free_mm: float

    # Imperial
    tpi: float | None = None
    nominal_size_inch: str | None = None

    # Taper
    engagement_length_mm: float = 0.0

    # Reference
    standard_ref: str


# === Tap drill ===

class TapDrillResponse(BaseModel):
    """Tap drill and clearance hole information."""
    family: str
    size: str
    tap_drill_mm: float
    clearance_hole_close_mm: float
    clearance_hole_medium_mm: float
    clearance_hole_free_mm: float
    # Print reference
    fdm_clearance_hole_mm: float = Field(description="Tap drill + FDM clearance offset")
    sla_clearance_hole_mm: float = Field(description="Tap drill + SLA clearance offset")


# === Generation request/response ===

class ThreadGenerateRequest(BaseModel):
    """Request to generate thread geometry."""
    family: str = Field(
        ...,
        description="Thread family: iso_metric, unc, unf, npt, bspp, bspt, acme, trapezoidal",
    )
    size: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Thread size designator (e.g., 'M8', '1/4-20')",
    )
    thread_type: str = Field(
        ...,
        pattern="^(internal|external)$",
        description="internal or external",
    )
    length_mm: float = Field(
        ...,
        gt=0,
        le=200.0,
        description="Thread length in mm (max 200)",
    )
    pitch_series: str | None = Field(
        None,
        pattern="^(coarse|fine|superfine)$",
        description="Pitch series (metric only)",
    )
    hand: str = Field(
        "right",
        pattern="^(right|left)$",
        description="Thread hand (right or left)",
    )
    # Optional overrides
    custom_pitch_mm: float | None = Field(
        None,
        gt=0.1,
        le=20.0,
        description="Override pitch (non-standard threads)",
    )
    custom_diameter_mm: float | None = Field(
        None,
        gt=0.5,
        le=200.0,
        description="Override major diameter (non-standard threads)",
    )
    export_format: str = Field(
        "step",
        pattern="^(step|stl|both)$",
        description="Output format",
    )
    segments_per_revolution: int = Field(
        64,
        ge=16,
        le=256,
        description="Tessellation quality (higher = smoother, slower)",
    )


class ThreadGenerateResponse(BaseModel):
    """Response from thread generation."""
    job_id: str = Field(description="Unique generation ID")
    success: bool
    thread_spec: ThreadSpecResponse
    file_urls: dict[str, str] = Field(
        description="Download URLs keyed by format ('step', 'stl')",
    )
    metadata: dict[str, Any] = Field(
        description="Generation metadata (face_count, volume, bounding_box)",
    )
    generation_time_ms: int = Field(description="Wall-clock generation time")


# === Print-optimized generation ===

class PrintOptimizedThreadRequest(ThreadGenerateRequest):
    """Request to generate print-optimized thread geometry."""
    process: str = Field(
        "fdm",
        pattern="^(fdm|sla|sls)$",
        description="3D printing process",
    )
    clearance_mm: float | None = Field(
        None,
        ge=0.05,
        le=2.0,
        description="Custom clearance override (mm per side)",
    )
    tolerance: str = Field(
        "normal",
        pattern="^(tight|normal|loose)$",
        description="Tolerance class",
    )
    flat_bottom: bool = Field(
        False,
        description="Flatten thread roots/crests for FDM (min nozzle width)",
    )
    add_chamfer: bool = Field(
        True,
        description="Add 45° lead-in chamfer (recommended for print)",
    )
    nozzle_diameter_mm: float = Field(
        0.4,
        ge=0.1,
        le=1.2,
        description="Nozzle diameter for flat-bottom calculation",
    )


class PrintOptimizedThreadResponse(ThreadGenerateResponse):
    """Response from print-optimized thread generation."""
    original_spec: ThreadSpecResponse = Field(
        description="Standard thread dimensions before adjustment",
    )
    adjusted_dimensions: dict[str, float] = Field(
        description="Dimensions after print clearance applied",
    )
    clearance_applied_mm: float
    process: str
    tolerance_class: str
    orientation_recommendation: str = Field(
        description="'vertical', 'horizontal', or 'any'",
    )
    orientation_reasoning: str
    warnings: list[str]
    recommended_nozzle_mm: float
    recommended_layer_height_mm: float


# === Print recommendation ===

class PrintRecommendationResponse(BaseModel):
    """Print feasibility recommendation for a thread."""
    family: str
    size: str
    process: str
    feasibility_rating: str = Field(
        description="not_recommended, marginal, good, excellent",
    )
    feasibility_details: str
    warnings: list[str]
    recommended_alternative: str | None = Field(
        None,
        description="E.g., 'Use M3 heat-set insert (McMaster 94180A331)'",
    )
    orientation_recommendation: str
    orientation_reasoning: str
    recommended_nozzle_mm: float
    recommended_layer_height_mm: float
    default_clearance_mm: float
```

### 4.4 Error Handling Patterns

Error responses follow the existing `CADError.to_dict()` pattern:

```python
# New exceptions in backend/app/cad/exceptions.py

class ThreadGenerationError(CADError):
    """
    Thread geometry generation failed.

    Raised when:
    - Build123d helix sweep fails
    - OCCT kernel error during thread boolean operations
    - Generation exceeds timeout
    - Memory limit approached
    """


class ThreadDataError(CADError):
    """
    Thread data lookup failed.

    Raised when:
    - Unknown thread family requested
    - Unknown thread size for a valid family
    - Invalid pitch_series for family
    """
```

API error mapping:

| Exception | HTTP Status | Response Body |
|-----------|-------------|---------------|
| `ThreadDataError` (unknown family/size) | 404 Not Found | `{"error": "ThreadDataError", "message": "...", "details": {"valid_families": [...]}}` |
| `ValidationError` (bad params) | 400 Bad Request | `{"error": "ValidationError", "message": "...", "details": {...}}` |
| `ThreadGenerationError` (OCCT failure) | 422 Unprocessable Entity | `{"error": "ThreadGenerationError", "message": "...", "details": {...}}` |
| `ThreadGenerationError` (timeout) | 504 Gateway Timeout | `{"error": "ThreadGenerationError", "message": "Generation timed out after 60s"}` |
| Rate limit exceeded | 429 Too Many Requests | Handled by `RateLimitMiddleware` |
| Generic 500 | 500 Internal Server Error | Generic error body (no internal details exposed) |

### 4.5 Response Caching Strategy

| Endpoint | Cache | TTL | Key Pattern |
|----------|-------|-----|-------------|
| `GET .../families` | Redis | 24 h | `threads:families` |
| `GET .../standards/{family}` | Redis | 24 h | `threads:sizes:{family}:{pitch_series}` |
| `GET .../standards/{family}/{size}` | Redis | 24 h | `threads:spec:{family}:{size}` |
| `GET .../tap-drill/{family}/{size}` | Redis | 24 h | `threads:tapdrill:{family}:{size}` |
| `GET .../print-recommendations/...` | Redis | 4 h | `threads:printrec:{family}:{size}:{process}` |
| `POST .../generate` | Redis (file URL) | 24 h | `threads:gen:{hash(all_params)}` |
| `POST .../generate/print-optimized` | Redis (file URL) | 24 h | `threads:gen:print:{hash(all_params)}` |

Lookup endpoints (GET) use a `@cache_response(ttl=86400)` decorator or inline Redis
check, following the pattern in existing v2 endpoints. Generated file caching stores
the STEP/STL file path and serves it from the existing downloads infrastructure.

Cache invalidation: All thread caches flush on server restart (code deployment).
Manual flush via admin endpoint if needed (existing admin tooling).

---

## 5. Security Controls

### 5.1 Authentication Requirements per Endpoint

| Endpoint | Auth Required | Auth Mechanism | Rationale |
|----------|---------------|----------------|-----------|
| `GET /families` | No* | — | Public reference data |
| `GET /standards/{family}` | No* | — | Public reference data |
| `GET /standards/{family}/{size}` | No* | — | Public reference data |
| `GET /tap-drill/{family}/{size}` | No* | — | Public reference data |
| `GET /print-recommendations/...` | No* | — | Public reference data |
| `POST /generate` | **Yes** | `Depends(get_current_user)` | CPU-intensive, needs user tracking |
| `POST /generate/print-optimized` | **Yes** | `Depends(get_current_user)` | CPU-intensive, needs user tracking |

\* All endpoints sit behind the base API middleware stack (CORS, security headers, request ID,
IP blocking). The global `RateLimitMiddleware` applies to all routes. No JWT required for
GET lookup endpoints, but the middleware still enforces IP-based rate limits.

### 5.2 Input Validation Strategy

**Layer 1 — Pydantic schema validation (automatic):**

All request bodies and query params validated by Pydantic before the handler runs.
Key constraints:

| Field | Constraint | Rationale |
|-------|-----------|-----------|
| `family` | Must be one of `ThreadFamily` values | Whitelist, not regex |
| `size` | `min_length=1, max_length=20` | Prevent empty or absurdly long strings |
| `thread_type` | `^(internal\|external)$` regex | Exact match only |
| `length_mm` | `gt=0, le=200.0` | Prevent zero, negative, or memory-exhausting lengths |
| `custom_pitch_mm` | `gt=0.1, le=20.0` | Prevent degenerate thread geometry |
| `custom_diameter_mm` | `gt=0.5, le=200.0` | Prevent physically impossible threads |
| `clearance_mm` | `ge=0.05, le=2.0` | Reasonable clearance bounds |
| `segments_per_revolution` | `ge=16, le=256` | Prevent DoS via huge polygon counts |
| `nozzle_diameter_mm` | `ge=0.1, le=1.2` | Real nozzle range |

**Layer 2 — Business logic validation (in handler):**

After Pydantic, the handler validates:

```python
# 1. Family exists in registry
if family_enum not in THREAD_REGISTRY:
    raise HTTPException(404, detail={"error": "Unknown family", "valid": [f.value for f in ThreadFamily]})

# 2. Size exists for family
if size not in THREAD_REGISTRY[family_enum]:
    raise HTTPException(404, detail={"error": f"Unknown size '{size}' for {family}", "valid": list_thread_sizes(family_enum)})

# 3. Geometric feasibility (for custom overrides)
if request.custom_pitch_mm and request.custom_pitch_mm > (effective_diameter / 2):
    raise HTTPException(400, detail="Pitch cannot exceed half the diameter")

# 4. Revolution count check
n_revolutions = request.length_mm / effective_pitch
if n_revolutions > MAX_REVOLUTIONS:
    raise HTTPException(400, detail=f"Thread would require {n_revolutions:.0f} revolutions (max {MAX_REVOLUTIONS})")
```

**Layer 3 — Size string sanitization:**

The `size` parameter in path and body is validated against the in-memory registry keys
(whitelist approach). No filesystem operations use the size string directly. The `:path`
converter in FastAPI handles encoded slashes (e.g., `1%2F4-20` → `1/4-20`).

### 5.3 Resource Limits

| Resource | Limit | Enforcement |
|----------|-------|-------------|
| Generation timeout | 60 seconds | `signal.alarm()` or `asyncio.wait_for()` in handler |
| Maximum thread length | 200 mm | Pydantic `Field(le=200.0)` |
| Maximum revolutions | 500 | Business logic validation |
| Maximum segments/rev | 256 | Pydantic `Field(le=256)` |
| Maximum concurrent generations per user | 3 | Redis counter with user ID key |
| Estimated face count warning | 100,000 | Log warning; generation still proceeds |
| Maximum STEP/STL file size | 50 MB | Post-generation check; reject if exceeded |

**Concurrent generation limiting:**

```python
async def _check_concurrent_limit(user_id: UUID, max_concurrent: int = 3) -> None:
    """
    Check and increment concurrent generation counter for user.

    Uses Redis INCR with TTL to track active generations.
    Each generation decrements the counter on completion (or TTL expiry).

    Raises:
        HTTPException 429: If user has too many active generation tasks.
    """
    key = f"thread_gen:active:{user_id}"
    current = await redis_client.incr(key)
    if current == 1:
        await redis_client.expire(key, 120)  # Auto-expire after 2 min safety net
    if current > max_concurrent:
        await redis_client.decr(key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Maximum {max_concurrent} concurrent thread generations allowed",
        )
```

### 5.4 Rate Limiting Configuration

Thread endpoints integrate with the existing `RateLimitMiddleware` from
`backend/app/middleware/security.py`. Endpoint-specific rate limits:

| Endpoint Pattern | Rate Limit | Window | Scope |
|------------------|-----------|--------|-------|
| `GET /api/v2/threads/*` | 60 req/min | Per IP | All read endpoints |
| `POST /api/v2/threads/generate*` | 10 req/min | Per user (JWT) | Generation endpoints |

Implementation: Add thread-specific rules to the middleware configuration in
`backend/app/main.py` or via per-route dependency:

```python
from app.middleware.security import RateLimitMiddleware

# In router or as a dependency
THREAD_GENERATE_RATE_LIMIT = Depends(
    RateLimitMiddleware.create_limiter(max_requests=10, window_seconds=60)
)
```

### 5.5 Logging and Monitoring

**Structured log events** (following `backend/docs/structured-logging.md`):

```python
# On generation request
logger.info(
    "thread_generation_requested",
    extra={
        "user_id": str(current_user.id),
        "family": request.family,
        "size": request.size,
        "thread_type": request.thread_type,
        "length_mm": request.length_mm,
        "print_optimized": isinstance(request, PrintOptimizedThreadRequest),
    },
)

# On generation completion
logger.info(
    "thread_generation_completed",
    extra={
        "user_id": str(current_user.id),
        "generation_time_ms": result.generation_time_ms,
        "face_count": result.estimated_face_count,
        "cache_hit": cache_hit,
    },
)

# On generation failure
logger.error(
    "thread_generation_failed",
    extra={
        "user_id": str(current_user.id),
        "error": str(e),
        "family": request.family,
        "size": request.size,
    },
)
```

**Prometheus metrics** (following `backend/docs/prometheus-metrics.md`):

```python
# New metrics in thread_generator.py
from prometheus_client import Counter, Histogram

THREAD_GEN_DURATION = Histogram(
    "thread_generation_duration_seconds",
    "Time to generate thread geometry",
    labelnames=["family", "thread_type", "print_optimized"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

THREAD_GEN_TOTAL = Counter(
    "thread_generation_total",
    "Total thread generation requests",
    labelnames=["family", "thread_type", "status"],  # status: success/failure/timeout
)

THREAD_LOOKUP_TOTAL = Counter(
    "thread_lookup_total",
    "Total thread data lookup requests",
    labelnames=["family", "endpoint"],
)
```

**Security audit events** (via existing `SecurityAuditService`):

- Log failed validation attempts (potential fuzzing).
- Log rate limit hits on generation endpoints.
- Alert threshold: >5 rate limit hits from same user in 5 minutes.

---

## 6. Testing Strategy

### 6.1 Test File Summary

| Test File | Module Under Test | Pytest Markers |
|-----------|-------------------|----------------|
| `backend/tests/cad/test_threads.py` | `app.cad.threads` | — |
| `backend/tests/cad/test_thread_generator.py` | `app.cad.thread_generator` | `@pytest.mark.slow` (for full geometry tests) |
| `backend/tests/cad/test_thread_print_optimizer.py` | `app.cad.thread_print_optimizer` | — |
| `backend/tests/api/test_threads_api.py` | `app.api.v2.threads` | `@pytest.mark.asyncio` |
| `backend/tests/seeds/test_thread_seeds.py` | `app.seeds.threads` | `@pytest.mark.asyncio` |

### 6.2 Test Classes and Key Scenarios

#### `test_threads.py` — Thread Data Library (#248)

```python
class TestThreadFamily:
    """ThreadFamily enum tests."""
    def test_all_families_defined(self): ...
    def test_family_string_values(self): ...

class TestThreadForm:
    """ThreadForm enum tests."""
    def test_all_forms_defined(self): ...

class TestThreadSpec:
    """ThreadSpec dataclass tests."""
    def test_frozen_immutability(self): ...
    def test_to_dict_contains_all_required_fields(self): ...
    def test_to_dict_omits_none_optionals(self): ...

class TestISOMetricCoarseData:
    """ISO 261 coarse thread data accuracy tests."""
    def test_m2_dimensions_match_iso_261(self): ...
    def test_m3_dimensions_match_iso_261(self): ...
    def test_m4_dimensions_match_iso_261(self): ...
    def test_m5_dimensions_match_iso_261(self): ...
    def test_m6_dimensions_match_iso_261(self): ...
    def test_m8_dimensions_match_iso_261(self): ...
    def test_m10_dimensions_match_iso_261(self): ...
    def test_m12_dimensions_match_iso_261(self): ...
    def test_m16_dimensions_match_iso_261(self): ...
    def test_m20_dimensions_match_iso_261(self): ...
    def test_all_coarse_sizes_present(self): ...
    def test_pitch_diameter_between_major_and_minor(self): ...
    def test_tap_drill_less_than_minor_diameter_int(self): ...

class TestISOMetricFineData:
    """ISO 261 fine thread data accuracy tests."""
    def test_m8x1_dimensions(self): ...
    def test_m10x1_dimensions(self): ...
    def test_m10x1_25_dimensions(self): ...
    def test_fine_pitch_less_than_coarse_for_same_nominal(self): ...

class TestUNCData:
    """ASME B1.1 UNC thread data tests."""
    def test_quarter_20_dimensions(self): ...
    def test_half_13_dimensions(self): ...
    def test_number_sizes_present(self): ...  # #1-64 through #12-24
    def test_fractional_sizes_present(self): ...  # 1/4 through 4"
    def test_tpi_values_correct(self): ...

class TestUNFData:
    """ASME B1.1 UNF thread data tests."""
    def test_quarter_28_dimensions(self): ...
    def test_unf_pitch_finer_than_unc(self): ...

class TestNPTData:
    """ASME B1.20.1 NPT thread data tests."""
    def test_quarter_npt_dimensions(self): ...
    def test_taper_rate_1_to_16(self): ...
    def test_engagement_length_populated(self): ...

class TestACMEData:
    """ASME B1.5 ACME thread data tests."""
    def test_acme_profile_angle_29_degrees(self): ...
    def test_acme_quarter_16_dimensions(self): ...

class TestTrapezoidalData:
    """ISO 2904 trapezoidal thread data tests."""
    def test_trapezoidal_profile_angle_30_degrees(self): ...
    def test_tr8x1_5_dimensions(self): ...

class TestLookupFunctions:
    """Thread registry lookup function tests."""
    def test_get_thread_spec_valid(self): ...
    def test_get_thread_spec_unknown_family_raises(self): ...
    def test_get_thread_spec_unknown_size_raises(self): ...
    def test_get_thread_spec_with_pitch_series_filter(self): ...
    def test_list_thread_sizes_returns_sorted(self): ...
    def test_list_thread_sizes_unknown_family_raises(self): ...
    def test_list_thread_sizes_pitch_series_filter(self): ...
    def test_list_thread_families_returns_all(self): ...

class TestThreadHardwareConsistency:
    """Cross-check thread library against hardware.py data."""
    def test_tap_drill_matches_hardware_py(self): ...
    def test_clearance_hole_matches_hardware_py(self): ...
```

#### `test_thread_generator.py` — Geometry Generation (#247)

```python
class TestThreadGeneratorConfig:
    """Config validation tests."""
    def test_config_requires_spec(self): ...
    def test_config_defaults(self): ...

class TestGenerateExternalMetricThread:
    """External ISO metric thread generation."""
    def test_m8_coarse_returns_part_with_volume(self): ...
    def test_m8_major_diameter_within_tolerance(self): ...
    def test_m8_pitch_accuracy(self): ...
    def test_m3_external_thread(self): ...
    def test_m10_external_thread(self): ...

class TestGenerateInternalMetricThread:
    """Internal ISO metric thread (cutting tool)."""
    def test_m6_internal_returns_part(self): ...
    def test_internal_thread_usable_with_difference(self): ...

class TestGenerateImperialThread:
    """UNC/UNF thread generation."""
    def test_quarter_20_unc_external(self): ...
    def test_quarter_28_unf_external(self): ...

class TestGenerateNPTThread:
    """NPT tapered thread generation."""
    def test_quarter_npt_external_tapered(self): ...
    def test_npt_taper_angle_correct(self): ...

class TestGenerateACMEThread:
    """ACME/trapezoidal thread generation."""
    def test_acme_profile_flat_crests(self): ...
    def test_trapezoidal_30_degree_angle(self): ...

class TestCustomOverrides:
    """Custom pitch/diameter override tests."""
    def test_custom_pitch_applied(self): ...
    def test_custom_diameter_applied(self): ...
    def test_invalid_pitch_too_large_raises(self): ...

class TestLeftHandThread:
    """Left-hand thread generation."""
    def test_left_hand_helix_direction(self): ...

class TestChamferLeadIn:
    """Chamfer/lead-in feature tests."""
    def test_external_chamfer_applied(self): ...
    def test_internal_countersink_applied(self): ...
    def test_no_chamfer_when_disabled(self): ...

class TestPerformance:
    """Performance and resource limit tests."""
    @pytest.mark.slow
    def test_50mm_thread_under_10_seconds(self): ...
    @pytest.mark.slow
    def test_200mm_thread_under_30_seconds(self): ...
    def test_length_exceeding_max_raises(self): ...
    def test_revolutions_exceeding_max_raises(self): ...

class TestMetadataOutput:
    """Thread generation metadata tests."""
    def test_metadata_includes_all_required_fields(self): ...
    def test_metadata_diameters_match_spec(self): ...
    def test_generation_time_recorded(self): ...
    def test_face_count_estimated(self): ...
```

#### `test_thread_print_optimizer.py` — Print Optimization (#249)

```python
class TestPrintProcessDefaults:
    """Default clearance values per process."""
    def test_fdm_default_clearance_0_4mm(self): ...
    def test_sla_default_clearance_0_15mm(self): ...
    def test_sls_default_clearance_0_2mm(self): ...

class TestFDMClearanceApplication:
    """FDM clearance adjustment tests."""
    def test_external_major_diameter_reduced(self): ...
    def test_internal_minor_diameter_increased(self): ...
    def test_clearance_symmetric_internal_external(self): ...

class TestSLAClearanceApplication:
    """SLA clearance adjustment tests."""
    def test_sla_clearance_smaller_than_fdm(self): ...
    def test_sla_thread_retains_more_detail(self): ...

class TestCustomClearance:
    """User-specified clearance override tests."""
    def test_custom_clearance_applied(self): ...
    def test_clearance_below_min_rejected(self): ...
    def test_clearance_above_half_pitch_rejected(self): ...

class TestToleranceClasses:
    """Tight/normal/loose tolerance tests."""
    def test_loose_adds_extra_clearance(self): ...
    def test_tight_reduces_clearance(self): ...
    def test_normal_uses_process_default(self): ...
    def test_loose_clearance_greater_than_normal(self): ...
    def test_tight_clearance_less_than_normal(self): ...

class TestMinimumSizeWarnings:
    """Printability warning tests."""
    def test_m2_fdm_returns_not_recommended(self): ...
    def test_m3_fdm_returns_marginal(self): ...
    def test_m4_fdm_returns_good_with_loose(self): ...
    def test_m6_fdm_returns_good(self): ...
    def test_m8_fdm_returns_excellent(self): ...
    def test_m3_sla_returns_good(self): ...
    def test_small_thread_suggests_heat_set_insert(self): ...

class TestOrientationRecommendation:
    """Print orientation recommendation tests."""
    def test_external_large_recommends_vertical(self): ...
    def test_internal_always_recommends_vertical(self): ...
    def test_recommendation_includes_reasoning(self): ...

class TestChamferGeneration:
    """Print chamfer/lead-in tests."""
    def test_external_chamfer_45_degrees(self): ...
    def test_internal_countersink(self): ...
    def test_chamfer_depth_equals_one_pitch(self): ...

class TestFlatBottom:
    """FDM flat-bottom option tests."""
    def test_flat_bottom_applied(self): ...
    def test_flat_root_width_at_least_nozzle_width(self): ...
    def test_flat_crest_width_at_least_nozzle_width(self): ...
    def test_flat_bottom_off_by_default(self): ...

class TestPrintMetadata:
    """Result metadata completeness tests."""
    def test_original_spec_included(self): ...
    def test_adjusted_spec_included(self): ...
    def test_clearance_amount_recorded(self): ...
    def test_recommended_nozzle_included(self): ...
    def test_recommended_layer_height_included(self): ...

class TestNPTPrintWarning:
    """Tapered thread print warning tests."""
    def test_npt_print_warns_not_suitable(self): ...
    def test_bspt_print_warns_not_suitable(self): ...
```

#### `test_threads_api.py` — API Endpoints (All)

```python
class TestListFamilies:
    """GET /api/v2/threads/families tests."""
    async def test_returns_all_families(self, client): ...
    async def test_response_schema_valid(self, client): ...
    async def test_size_count_positive(self, client): ...

class TestListSizes:
    """GET /api/v2/threads/standards/{family} tests."""
    async def test_iso_metric_returns_sizes(self, client): ...
    async def test_unc_returns_sizes(self, client): ...
    async def test_pitch_series_filter(self, client): ...
    async def test_unknown_family_returns_404(self, client): ...

class TestGetSpec:
    """GET /api/v2/threads/standards/{family}/{size} tests."""
    async def test_m8_returns_full_spec(self, client): ...
    async def test_quarter_20_handles_slash(self, client): ...
    async def test_unknown_size_returns_404(self, client): ...
    async def test_unknown_family_returns_404(self, client): ...

class TestGetTapDrill:
    """GET /api/v2/threads/tap-drill/{family}/{size} tests."""
    async def test_m6_tap_drill(self, client): ...
    async def test_fdm_sla_clearance_included(self, client): ...
    async def test_unknown_returns_404(self, client): ...

class TestGenerateThread:
    """POST /api/v2/threads/generate tests."""
    async def test_requires_auth(self, client): ...
    async def test_valid_request_returns_201(self, auth_client): ...
    async def test_response_includes_file_urls(self, auth_client): ...
    async def test_response_includes_spec(self, auth_client): ...
    async def test_invalid_family_returns_400(self, auth_client): ...
    async def test_length_zero_returns_422(self, auth_client): ...
    async def test_length_exceeds_max_returns_422(self, auth_client): ...
    async def test_custom_overrides_accepted(self, auth_client): ...
    async def test_unknown_size_returns_404(self, auth_client): ...

class TestGeneratePrintOptimized:
    """POST /api/v2/threads/generate/print-optimized tests."""
    async def test_requires_auth(self, client): ...
    async def test_fdm_request_returns_adjusted_dims(self, auth_client): ...
    async def test_sla_request_returns_adjusted_dims(self, auth_client): ...
    async def test_clearance_reflected_in_response(self, auth_client): ...
    async def test_warnings_for_small_thread(self, auth_client): ...
    async def test_flat_bottom_option(self, auth_client): ...
    async def test_invalid_tolerance_returns_422(self, auth_client): ...

class TestGetPrintRecommendation:
    """GET /api/v2/threads/print-recommendations/{family}/{size} tests."""
    async def test_m8_fdm_returns_good(self, client): ...
    async def test_m2_fdm_returns_not_recommended(self, client): ...
    async def test_m3_sla_returns_good(self, client): ...
    async def test_unknown_process_returns_422(self, client): ...
    async def test_unknown_thread_returns_404(self, client): ...

class TestRateLimiting:
    """Rate limiting on generation endpoints."""
    async def test_generation_rate_limit_enforced(self, auth_client): ...
    async def test_read_endpoints_higher_limit(self, client): ...

class TestSecurityHeaders:
    """Security controls on responses."""
    async def test_no_internal_details_in_error(self, client): ...
    async def test_request_id_in_response(self, client): ...
```

#### `test_thread_seeds.py` — Seed Data (#248)

```python
class TestThreadSeeding:
    """Thread data seeding to ReferenceComponent table."""
    async def test_seed_creates_reference_components(self, db): ...
    async def test_seed_category_is_thread_standard(self, db): ...
    async def test_seed_subcategory_matches_family(self, db): ...
    async def test_seed_dimensions_jsonb_complete(self, db): ...
    async def test_seed_idempotent(self, db): ...
    async def test_seed_updates_existing_on_rerun(self, db): ...
    async def test_seed_source_type_is_library(self, db): ...
    async def test_seed_count_matches_registry(self, db): ...
```

### 6.3 Mocking Strategy for Build123d Parts

Geometry tests require Build123d + OCCT. Strategy:

1. **Unit tests** (`test_threads.py`, `test_thread_print_optimizer.py`):
   No Build123d dependency. Test data lookups, clearance math, metadata
   construction. Mock `Part` objects as `MagicMock(spec=Part)` with
   configured `.volume`, `.bounding_box()` return values.

2. **Integration tests** (`test_thread_generator.py`):
   Require real Build123d. Mark slow geometry tests with `@pytest.mark.slow`.
   CI runs these but local dev can skip with `pytest -m "not slow"`.
   Assert on: `result.part.volume > 0`, bounding box dimensions within
   tolerance, face count > 0.

3. **API tests** (`test_threads_api.py`):
   Mock the `generate_thread()` function at the module level to return a
   pre-constructed `ThreadGenerationResult` with a dummy Part. This avoids
   OCCT dependency in API tests. Use `unittest.mock.patch`:

   ```python
   @patch("app.api.v2.threads.generate_thread")
   async def test_valid_request_returns_201(self, mock_gen, auth_client):
       mock_gen.return_value = ThreadGenerationResult(
           part=MagicMock(spec=Part),
           metadata={"volume": 42.0},
           generation_time_ms=500,
           estimated_face_count=10000,
       )
       response = await auth_client.post("/api/v2/threads/generate", json={...})
       assert response.status_code == 201
   ```

### 6.4 Coverage Target

- All new modules: **≥ 80% line coverage** (project minimum per copilot-instructions).
- Critical paths (lookup functions, validation, security checks): **100% branch coverage**.
- Run: `pytest --cov=app.cad.threads --cov=app.cad.thread_generator --cov=app.cad.thread_print_optimizer --cov=app.api.v2.threads --cov=app.schemas.threads --cov=app.seeds.threads --cov-report=term-missing`

---

## 7. Integration Points

### 7.1 How Threads Connect to Existing Enclosure Generator

The enclosure generator (`backend/app/cad/enclosure.py`) currently uses `hardware.py`
for screw specs and threaded insert dimensions. Threads integrate as follows:

**Threaded bosses in enclosures:**

Currently, `enclosure.py` imports `get_insert_hole()` and `get_clearance_hole()` from
`hardware.py` to create mounting holes. With the thread library, the enclosure generator
gains the ability to include actual thread geometry in bosses:

```python
# New optional feature in enclosure generation
# backend/app/cad/enclosure.py — future integration

from app.cad.threads import ThreadFamily, get_thread_spec
from app.cad.thread_generator import ThreadGeneratorConfig, generate_thread

def _add_threaded_boss(
    body: Part,
    position: tuple[float, float],
    thread_size: str = "M3",
    boss_height: float = 8.0,
) -> Part:
    """
    Add a boss with internal threads to the enclosure body.

    Uses the thread generator to create an internal thread cutting tool,
    then differences it from the boss cylinder.
    """
    spec = get_thread_spec(ThreadFamily.ISO_METRIC, thread_size)
    config = ThreadGeneratorConfig(
        spec=spec,
        thread_type=ThreadType.INTERNAL,
        length_mm=boss_height,
    )
    thread_cut = generate_thread(config)
    # ... position and subtract from boss
```

**This is a future enhancement.** The initial thread library is self-contained. The
integration point exists but is not activated in the first release of Epic 40. The
enclosure generator continues to use simple cylindrical holes for mounting.

### 7.2 How Threads Appear in BillOfMaterials

The existing `BillOfMaterials` class in `hardware.py` tracks hardware components by
`HardwareSpec`. Threads integrate by providing a corresponding `HardwareSpec` entry
for each threaded feature:

```python
# backend/app/cad/threads.py — convenience function

def get_thread_hardware_spec(
    spec: ThreadSpec,
    thread_type: ThreadType,
    length_mm: float,
) -> HardwareSpec:
    """
    Convert a ThreadSpec to a HardwareSpec for BOM inclusion.

    This allows threaded features to appear in the BillOfMaterials
    alongside screws, inserts, and other hardware.

    Args:
        spec: Thread specification.
        thread_type: Internal or external.
        length_mm: Thread length used.

    Returns:
        HardwareSpec representing the threaded feature.
    """
    return HardwareSpec(
        type=HardwareType.SCREW if thread_type == ThreadType.EXTERNAL else HardwareType.NUT,
        name=f"{spec.size} {'External' if thread_type == ThreadType.EXTERNAL else 'Internal'} Thread",
        description=f"{spec.family.value} {spec.size} thread, {length_mm}mm long",
        dimensions={
            "major_diameter": spec.major_diameter,
            "pitch_mm": spec.pitch_mm,
            "length": length_mm,
        },
        properties={
            "family": spec.family.value,
            "form": spec.form.value,
            "standard_ref": spec.standard_ref,
        },
    )
```

Usage in enclosure or assembly code:

```python
bom = BillOfMaterials()
bom.add(get_thread_hardware_spec(m3_spec, ThreadType.INTERNAL, 8.0), quantity=4)
```

### 7.3 How Seed Data Is Loaded

Thread data seeds follow the exact pattern established by `components_v2.py`:

```python
# backend/app/seeds/threads.py

import asyncio
import logging
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cad.threads import (
    THREAD_FAMILY_INFO,
    THREAD_REGISTRY,
    ThreadFamily,
    ThreadSpec,
)
from app.core.database import async_session_maker
from app.models.reference_component import ReferenceComponent

logger = logging.getLogger(__name__)


def _thread_spec_to_component_dict(
    spec: ThreadSpec,
    family_info: dict[str, Any],
) -> dict[str, Any]:
    """
    Convert a ThreadSpec to a dict suitable for ReferenceComponent.

    Args:
        spec: Thread specification to convert.
        family_info: Metadata about the thread family.

    Returns:
        Dictionary with ReferenceComponent-compatible fields.
    """
    pitch_label = f" {spec.pitch_series.value.title()}" if spec.pitch_series else ""
    return {
        "name": f"{spec.size}{pitch_label} ({family_info['name']})",
        "category": "thread_standard",
        "subcategory": spec.family.value,
        "description": f"{family_info['name']} thread {spec.size}, pitch {spec.pitch_mm}mm",
        "source_type": "library",
        "dimensions": spec.to_dict(),
        "mounting_specs": {
            "tap_drill_mm": spec.tap_drill_mm,
            "clearance_holes": {
                "close_mm": spec.clearance_hole_close_mm,
                "medium_mm": spec.clearance_hole_medium_mm,
                "free_mm": spec.clearance_hole_free_mm,
            },
        },
        "tags": _build_tags(spec),
    }


def _build_tags(spec: ThreadSpec) -> list[str]:
    """
    Build searchable tags for a thread spec.

    Args:
        spec: Thread specification.

    Returns:
        List of tag strings.
    """
    tags = [spec.family.value, spec.size.lower(), spec.form.value]
    if spec.pitch_series:
        tags.append(spec.pitch_series.value)
    if spec.standard_ref:
        tags.append(spec.standard_ref.lower().replace(" ", "_"))
    if spec.nominal_size_inch:
        tags.append(f"imperial_{spec.nominal_size_inch}")
    return tags


async def seed_thread_standards(db: AsyncSession) -> tuple[int, int]:
    """
    Sync thread standard registry with the database.

    Creates or updates ReferenceComponent records for each thread spec
    in the registry. Idempotent — re-running updates existing records
    without duplicating them.

    Args:
        db: Async database session.

    Returns:
        Tuple of (created_count, updated_count).
    """
    created = 0
    updated = 0

    for family, sizes in THREAD_REGISTRY.items():
        family_info = THREAD_FAMILY_INFO[family]

        for size, spec in sizes.items():
            comp_dict = _thread_spec_to_component_dict(spec, family_info)

            # Check for existing record by name + category + subcategory
            result = await db.execute(
                select(ReferenceComponent).where(
                    ReferenceComponent.name == comp_dict["name"],
                    ReferenceComponent.category == "thread_standard",
                    ReferenceComponent.subcategory == spec.family.value,
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing record
                for key, value in comp_dict.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                updated += 1
            else:
                # Create new record
                new_comp = ReferenceComponent(
                    id=uuid4(),
                    **comp_dict,
                )
                db.add(new_comp)
                created += 1

    await db.commit()
    logger.info(
        "thread_standards_seeded",
        extra={"created": created, "updated": updated},
    )
    return created, updated


async def main() -> None:
    """Run thread seeding standalone."""
    async with async_session_maker() as db:
        created, updated = await seed_thread_standards(db)
        print(f"Thread standards seeded: {created} created, {updated} updated")


if __name__ == "__main__":
    asyncio.run(main())
```

**Makefile integration:** Add `seed-threads` target alongside existing `db-seed`:

```makefile
seed-threads:
	cd backend && python -m app.seeds.threads
```

Or integrate into the existing `db-seed` target:

```makefile
db-seed:
	cd backend && python -m app.seeds.components_v2
	cd backend && python -m app.seeds.threads
```

---

## Appendix A: Dependency Graph (Implementation Order)

```
Week 1 (Parallel Start)
├── Define shared contract: ThreadSpec, ThreadFamily, ThreadForm, ThreadType enums
│   └── File: backend/app/cad/threads.py (enums + dataclass only)
│
├── #248 (3 SP) — Thread data population
│   ├── Populate ISO_METRIC_COARSE dict (M1–M68)
│   ├── Populate ISO_METRIC_FINE dict
│   ├── Populate UNC_THREADS dict
│   ├── Populate UNF_THREADS dict
│   ├── Populate NPT_THREADS dict
│   ├── Populate BSPP_THREADS, BSPT_THREADS dicts
│   ├── Populate ACME_THREADS, TRAPEZOIDAL_THREADS dicts
│   ├── Implement lookup functions
│   ├── Implement seed function
│   └── Write test_threads.py + test_thread_seeds.py
│
└── #247 (5 SP) — Thread geometry generator (skeleton)
    ├── Implement _build_thread_profile() for ISO metric
    ├── Implement _create_helix_path() (parallel)
    ├── Implement _sweep_thread()
    └── Write test_thread_generator.py (with mock specs)

Week 2 (Sequential Integration)
├── #247 continued — Wire generator to real data from #248
│   ├── Add UNC/UNF profile support
│   ├── Add NPT tapered helix support
│   ├── Add ACME/trapezoidal profile support
│   ├── Add chamfer/lead-in
│   ├── Add internal thread support
│   ├── Implement caching
│   └── Performance optimization + tests
│
├── API layer
│   ├── Create schemas/threads.py
│   ├── Create api/v2/threads.py
│   ├── Register router in __init__.py
│   ├── Add exceptions to exceptions.py
│   └── Write test_threads_api.py
│
└── #249 (3 SP) — Print optimization
    ├── Implement clearance adjustment logic
    ├── Implement tolerance classes
    ├── Implement feasibility ratings
    ├── Implement orientation recommendations
    ├── Implement flat-bottom option
    ├── Implement chamfer for print
    └── Write test_thread_print_optimizer.py
```

## Appendix B: Thread Profile Geometry Reference

### ISO Metric (60° V-Thread, Truncated)

```
          ← P (pitch) →
    P/8 ┌─┐
        │ │╲
        │ │ ╲            H = 0.866025 × P
        │ │  ╲           h = 5H/8 (effective depth)
        │ │   ╲          Crest flat = P/8
        │ │    ╲         Root flat  = P/4
        │ │     ╲        60° included angle
        │ │      ╲
   P/4  │ │_______╲
        ├─┤ Root
```

### ACME (29° Included Angle)

```
         ← P (pitch) →
    ┌────────┐
    │  crest │  = 0.3707 × P
    │        │╲
    │        │ ╲         H = P/2
    │        │  ╲        29° included angle
    │        │   ╲       Flat crests and roots
    │        │    │
    └────────┘────┘
       root = 0.3707 × P
```

### Trapezoidal (30° Included Angle)

```
         ← P (pitch) →
    ┌────────┐
    │  crest │
    │        │╲
    │        │ ╲         H = P/2
    │        │  ╲        30° included angle
    │        │   ╲       Flat crests and roots
    │        │    │
    └────────┘────┘
```

## Appendix C: Security Checklist

| Item | Status | Notes |
|------|--------|-------|
| All POST endpoints require JWT auth via `Depends(get_current_user)` | Planned | §5.1 |
| All numeric inputs bounded by Pydantic `Field()` constraints | Planned | §5.2 |
| Family/size validated against in-memory registry (whitelist) | Planned | §5.2 |
| No user input used in file paths or shell commands | Planned | By design |
| Rate limiting: 10 req/min on generation, 60 req/min on reads | Planned | §5.4 |
| Concurrent generation limit: 3 per user | Planned | §5.3 |
| Hard timeout of 60s on OCCT operations | Planned | §5.3 |
| Maximum thread length 200mm enforced at schema level | Planned | §5.2 |
| No internal errors exposed in API responses | Planned | §4.4 |
| All generation requests logged with user ID | Planned | §5.5 |
| Failed validation attempts logged (security audit) | Planned | §5.5 |
| Prometheus metrics for generation duration and count | Planned | §5.5 |
| Cache keys do not contain user-controlled raw strings | Planned | §4.5 |
| STEP/STL download URLs use UUIDs, not user input | Planned | By design |
| No secrets or credentials in thread data | N/A | Public reference data |
