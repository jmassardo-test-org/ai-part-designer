# Epic 40: Thread Library — Strategy & Design Document

**Epic:** Thread Library
**Sub-Issues:** #247 (US-41.1), #248 (US-41.2), #249 (US-41.4)
**Total Story Points:** 11 SP
**Date:** 2026-02-23
**Status:** Draft

---

## Table of Contents

1. [Detailed User Stories with Acceptance Criteria](#1-detailed-user-stories-with-acceptance-criteria)
2. [Dependency Analysis](#2-dependency-analysis)
3. [Data Model Design Guidance](#3-data-model-design-guidance)
4. [API Design Guidance](#4-api-design-guidance)
5. [UI/UX Considerations](#5-uiux-considerations)
6. [Edge Cases and Constraints](#6-edge-cases-and-constraints)
7. [Security Considerations](#7-security-considerations)

---

## 1. Detailed User Stories with Acceptance Criteria

### US-41.1: Implement Thread Geometry Generator (#247 — 5 SP)

**As a** mechanical designer using the CAD engine,
**I want** a thread geometry generator that produces accurate 3D thread profiles,
**So that** I can add internal and external threads to my part designs.

#### Acceptance Criteria

**AC-1: External metric thread generation**

```
GIVEN a request to generate an external metric thread with nominal diameter 10mm and pitch 1.5mm
WHEN the thread geometry generator is invoked with family="iso_metric", size="M10", pitch=1.5, thread_type="external", length=20.0
THEN a Build123d Part is returned containing a helical thread body
AND the major diameter measures 10.0mm ± 0.01mm
AND the pitch between adjacent crests is 1.5mm ± 0.01mm
AND the thread length is 20.0mm
AND the Part volume is > 0
```

**AC-2: Internal metric thread generation**

```
GIVEN a request to generate an internal thread for an M6x1.0 hole
WHEN the thread geometry generator is invoked with family="iso_metric", size="M6", pitch=1.0, thread_type="internal", length=12.0
THEN a Build123d Part is returned representing the internal thread cut tool (negative shape)
AND the minor diameter matches ISO 261 specification for M6x1.0 internal
AND the Part can be used with the `difference()` operation to cut threads into a solid body
AND the resulting threaded hole accepts an M6 bolt in 3D preview
```

**AC-3: Imperial UNC thread generation**

```
GIVEN a request to generate a 1/4-20 UNC external thread
WHEN the thread geometry generator is invoked with family="unc", size="1/4-20", thread_type="external", length=25.4
THEN a Build123d Part is returned with major diameter of 6.35mm (0.250")
AND the pitch is 1.27mm (20 TPI)
AND the thread profile angle is 60° (Unified thread standard)
```

**AC-4: Imperial UNF thread generation**

```
GIVEN a request to generate a 1/4-28 UNF external thread
WHEN the thread geometry generator is invoked with family="unf", size="1/4-28", thread_type="external", length=25.4
THEN a Build123d Part is returned with major diameter of 6.35mm (0.250")
AND the pitch is 0.907mm (28 TPI)
AND the thread profile matches UNF 60° V-thread specification
```

**AC-5: NPT pipe thread generation**

```
GIVEN a request to generate a 1/4" NPT external pipe thread
WHEN the thread geometry generator is invoked with family="npt", size="1/4", thread_type="external", length=15.0
THEN a Build123d Part is returned with a tapered thread body
AND the taper rate is 1:16 (3°34'48") per NPT specification
AND the thread pitch is 18 TPI (1.411mm)
```

**AC-6: ACME trapezoidal thread generation**

```
GIVEN a request to generate a 10mm ACME/trapezoidal thread
WHEN the thread geometry generator is invoked with family="acme", size="10x2", thread_type="external", length=30.0
THEN a Build123d Part is returned with a 29° included angle thread profile (ACME) or 30° (trapezoidal)
AND the thread root and crest are flat (not pointed like V-threads)
AND the thread is suitable for lead-screw / linear motion applications
```

**AC-7: Configurable thread parameters**

```
GIVEN the thread generator
WHEN a user provides custom overrides (pitch, diameter, profile_angle, clearance)
THEN the generator uses the overrides instead of standard values
AND a validation error is raised if overrides produce geometrically invalid threads (e.g., pitch > diameter)
```

**AC-8: Thread geometry performance**

```
GIVEN any thread generation request
WHEN the geometry is computed
THEN the operation completes in < 10 seconds for thread lengths ≤ 50mm
AND the operation completes in < 30 seconds for thread lengths ≤ 200mm
AND a TimeoutError is raised for requests that exceed 60 seconds
```

**AC-9: Thread metadata output**

```
GIVEN a successful thread generation
WHEN the result is returned
THEN it includes metadata: {family, size, pitch, major_diameter, minor_diameter, pitch_diameter, thread_type, length, tap_drill_size, clearance_hole_size}
AND the metadata matches published standard values for the requested thread
```

**AC-10: Unit tests**

```
GIVEN the thread geometry module
WHEN the test suite runs
THEN tests cover: all supported families, internal/external, parameter validation, edge cases (minimum/maximum sizes), error paths
AND code coverage is ≥ 80%
```

---

### US-41.2: Create Standard Thread Library (#248 — 3 SP)

**As a** mechanical designer,
**I want** a comprehensive library of standard thread specifications,
**So that** I can select threads by standard name (e.g., "M8x1.25") without manually entering dimensions.

#### Acceptance Criteria

**AC-1: ISO metric coarse thread data (M1–M68)**

```
GIVEN the thread library is loaded
WHEN I query for family="iso_metric" with pitch_series="coarse"
THEN all standard ISO 261 coarse-pitch sizes are available: M1, M1.2, M1.4, M1.6, M2, M2.5, M3, M3.5, M4, M5, M6, M8, M10, M12, M14, M16, M18, M20, M22, M24, M27, M30, M33, M36, M39, M42, M45, M48, M52, M56, M60, M64, M68
AND each entry includes: major_diameter, pitch, minor_diameter_external, minor_diameter_internal, pitch_diameter, tap_drill_size, clearance_hole_close, clearance_hole_medium, clearance_hole_free
AND values match ISO 261 / ISO 724 published tables
```

**AC-2: ISO metric fine thread data**

```
GIVEN the thread library is loaded
WHEN I query for family="iso_metric" with pitch_series="fine"
THEN commonly used fine-pitch variants are available (e.g., M8x1.0, M10x1.0, M10x1.25, M12x1.25, M12x1.5)
AND each entry contains the same dimensional fields as coarse threads
AND values match ISO 261 fine-pitch published tables
```

**AC-3: UNC thread data (#1–4")**

```
GIVEN the thread library is loaded
WHEN I query for family="unc"
THEN standard UNC sizes are available from #1-64 through 4"-4
AND each entry includes: nominal_size, tpi, major_diameter_mm, minor_diameter_mm, pitch_diameter_mm, tap_drill_inch, tap_drill_mm
AND values match ASME B1.1
```

**AC-4: UNF thread data**

```
GIVEN the thread library is loaded
WHEN I query for family="unf"
THEN standard UNF sizes are available from #0-80 through 1.5"-12
AND values match ASME B1.1
```

**AC-5: NPT pipe thread data**

```
GIVEN the thread library is loaded
WHEN I query for family="npt"
THEN standard NPT sizes are available: 1/16", 1/8", 1/4", 3/8", 1/2", 3/4", 1", 1-1/4", 1-1/2", 2"
AND each entry includes: nominal_pipe_size, tpi, major_diameter_mm, taper_per_inch, engagement_length_mm
AND values match ASME B1.20.1
```

**AC-6: BSP thread data**

```
GIVEN the thread library is loaded
WHEN I query for family="bsp"
THEN standard BSPP (parallel) and BSPT (tapered) entries are available for common pipe sizes
AND values match ISO 228-1 (BSPP) and ISO 7-1 (BSPT)
```

**AC-7: ACME and trapezoidal thread data**

```
GIVEN the thread library is loaded
WHEN I query for family="acme" or family="trapezoidal"
THEN standard sizes are available (e.g., ACME 1/4"-16 through 5"-2; Tr8x1.5 through Tr100x12)
AND values match ASME B1.5 (ACME) and ISO 2904 (trapezoidal)
```

**AC-8: Lookup functions**

```
GIVEN the thread library
WHEN I call get_thread_spec(family="iso_metric", size="M8", pitch_series="coarse")
THEN a ThreadSpec dataclass is returned with all dimensional data populated
AND an error is raised for unknown size/family combinations with a helpful message listing valid options
```

**AC-9: Backward compatibility with existing hardware.py**

```
GIVEN the existing TAP_DRILL_SIZES and CLEARANCE_HOLES dicts in hardware.py
WHEN the thread library is active
THEN the existing dicts remain functional (no breaking changes)
AND the thread library's tap_drill and clearance_hole values are consistent with the existing values for overlapping sizes (M2–M10)
```

**AC-10: Seed into database**

```
GIVEN the thread library data
WHEN the db-seed command runs
THEN thread specifications are synced to the database as ReferenceComponent rows with category="thread_standard"
AND each row's JSONB fields contain the full dimensional data
AND the seed is idempotent (re-running updates, doesn't duplicate)
```

**AC-11: Unit tests**

```
GIVEN the thread library module
WHEN the test suite runs
THEN tests verify: data completeness for each family, dimensional accuracy spot-checks against published tables, lookup function behavior, error handling for invalid queries
AND code coverage is ≥ 80%
```

---

### US-41.4: Add Print-Optimized Thread Profiles (#249 — 3 SP)

**As a** maker using FDM/SLA 3D printers,
**I want** print-optimized thread profiles with appropriate clearances,
**So that** my printed threads actually mate and function without manual cleanup.

#### Acceptance Criteria

**AC-1: FDM clearance adjustment**

```
GIVEN a standard M10x1.5 thread specification
WHEN I request a print-optimized profile with process="fdm"
THEN the external thread major diameter is reduced by a configurable clearance (default 0.4mm)
AND the internal thread minor diameter is increased by the same clearance
AND the thread root is rounded (no sharp internal corners)
AND the resulting geometry is marked as print-optimized in metadata
```

**AC-2: SLA clearance adjustment**

```
GIVEN a standard M10x1.5 thread specification
WHEN I request a print-optimized profile with process="sla"
THEN the clearance applied is smaller than FDM (default 0.15mm)
AND the thread profile retains more detail than the FDM variant
```

**AC-3: Configurable clearance**

```
GIVEN a print optimization request
WHEN the user specifies custom clearance_mm=0.3
THEN the custom value is used instead of the process default
AND validation rejects clearance values ≤ 0 or > pitch/2
```

**AC-4: Minimum printable thread size recommendation**

```
GIVEN a request to print an M2x0.4 thread on FDM
WHEN the print optimizer evaluates feasibility
THEN a warning is returned indicating the thread is below recommended minimum (M4 for FDM, M3 for SLA)
AND the warning includes a recommendation to use a heat-set insert instead
AND the geometry is still generated if the user explicitly confirms
```

**AC-5: Looser tolerance option**

```
GIVEN a print-optimized thread request with tolerance="loose"
WHEN the profile is generated
THEN additional clearance is added beyond the standard FDM/SLA adjustment (e.g., +0.2mm)
AND the metadata indicates tolerance_class="loose"
AND a "normal" and "tight" tolerance option are also available
```

**AC-6: Print orientation recommendations**

```
GIVEN a print-optimized thread
WHEN the result metadata is inspected
THEN it includes orientation_recommendation: one of "vertical" (thread axis = Z), "horizontal", or "any"
AND for external threads > M8, vertical orientation is recommended
AND for internal threads, vertical orientation is always recommended
AND the reasoning is included in the metadata
```

**AC-7: Thread chamfer/lead-in for print**

```
GIVEN a print-optimized external thread
WHEN the geometry is generated
THEN the thread start includes a 45° chamfer/lead-in of at least 1 pitch length
AND internal threads include a countersink/chamfer entry
AND this improves first-layer adhesion and thread engagement during assembly
```

**AC-8: Flat-bottom thread option for FDM**

```
GIVEN an FDM print-optimized thread profile
WHEN flat_bottom=true is specified
THEN the thread root is flattened to at least 0.4mm width (one nozzle width)
AND the thread crest is flattened to at least 0.4mm width
AND this prevents the slicer from producing unsupported overhangs in the thread profile
```

**AC-9: Reference data display**

```
GIVEN a print-optimized thread result
WHEN the metadata is inspected
THEN it includes: original_spec (standard dimensions), adjusted_spec (print dimensions), clearance_applied, process, tap_drill_size (for reference), recommended_nozzle_size, recommended_layer_height
AND tap_drill_size is shown for reference even though printing doesn't use taps
```

**AC-10: Unit tests**

```
GIVEN the print optimization module
WHEN the test suite runs
THEN tests cover: FDM/SLA clearance application, custom clearance, tolerance classes, minimum size warnings, orientation recommendations, chamfer generation, flat-bottom option
AND code coverage is ≥ 80%
```

---

## 2. Dependency Analysis

### Dependency Graph

```
                    ┌────────────────────────────┐
                    │  #248 US-41.2              │
                    │  Standard Thread Library   │
                    │  (Data Layer — 3 SP)       │
                    └──────────┬─────────────────┘
                               │ provides ThreadSpec data
                               ▼
                    ┌────────────────────────────┐
                    │  #247 US-41.1              │
                    │  Thread Geometry Generator  │
                    │  (Geometry Layer — 5 SP)   │
                    └──────────┬─────────────────┘
                               │ provides base geometry
                               ▼
                    ┌────────────────────────────┐
                    │  #249 US-41.4              │
                    │  Print-Optimized Profiles  │
                    │  (Optimization Layer — 3 SP)│
                    └────────────────────────────┘
```

### Execution Strategy

| Phase | Issues | Parallelism | Notes |
|-------|--------|-------------|-------|
| **Phase 1** | #248 data definitions + #247 geometry interface | **Partial parallel** | Define `ThreadSpec` dataclass and `ThreadFamily` enum first as shared contract. Then #248 populates data dicts while #247 builds the helix/sweep geometry engine against the interface. |
| **Phase 2** | #247 integration with #248 data | Sequential | Wire the geometry generator to consume real thread data from #248. Integration tests. |
| **Phase 3** | #249 print optimization | Sequential | Depends on both #247 and #248 being complete. Wraps the generator with clearance adjustments. |

### Shared Contract (define first, before parallel work)

```python
# This ThreadSpec dataclass and ThreadFamily enum must be defined and merged
# BEFORE parallel work on #247 and #248 can begin.

@dataclass
class ThreadSpec:
    family: ThreadFamily
    size: str
    pitch: float
    ...

class ThreadFamily(StrEnum):
    ISO_METRIC = "iso_metric"
    UNC = "unc"
    ...
```

### Critical Path

**Shared types → (#248 data ∥ #247 geometry skeleton) → #247 integration → #249 optimization**

Total elapsed time (assuming no blockers): ~2 sprints if partially parallelized.

### External Dependencies

| Dependency | Risk | Mitigation |
|-----------|------|------------|
| Build123d `Helix` + `sweep` | Medium — helix sweep is performance-sensitive in OCCT | Prototype helix sweep early in #247; fall-back to simplified thread representation if needed |
| ISO/ASME dimensional data | Low — published standards, widely available | Use authoritative references; spot-check against Machinery's Handbook |
| Existing `hardware.py` | Low — additive changes only | Thread library extends, never modifies existing dicts |

---

## 3. Data Model Design Guidance

### 3.1 In-Memory Data Structure

The existing `hardware.py` uses simple tuple-dicts (`METRIC_SOCKET_HEAD_SCREWS`, `THREADED_INSERTS`). For threads, a **richer dataclass** is warranted because:

1. Thread data has 10+ fields per entry (vs. 4 for screws)
2. Multiple pitch series per nominal size (coarse/fine)
3. Internal vs. external diameter sets differ
4. Print optimization needs to layer additional fields on top

**Recommended: Typed dataclasses in a new `backend/app/cad/threads.py` module.**

```python
# backend/app/cad/threads.py

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


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
    """Internal or external thread."""
    INTERNAL = "internal"
    EXTERNAL = "external"


class PitchSeries(StrEnum):
    """Pitch series for metric threads."""
    COARSE = "coarse"
    FINE = "fine"
    SUPERFINE = "superfine"


@dataclass(frozen=True)
class ThreadSpec:
    """
    Complete specification for a single thread size.

    All dimensions in millimeters. Follows ISO 261 naming where applicable.
    """
    family: ThreadFamily
    size: str                        # e.g., "M8", "1/4-20", "1/2 NPT"
    pitch_mm: float                  # Thread pitch in mm
    pitch_series: PitchSeries | None = None  # coarse/fine (metric only)

    # External thread diameters
    major_diameter: float = 0.0      # Nominal / major diameter
    pitch_diameter_ext: float = 0.0  # Pitch diameter (external)
    minor_diameter_ext: float = 0.0  # Minor diameter (external)

    # Internal thread diameters
    major_diameter_int: float = 0.0  # Major diameter (internal)
    pitch_diameter_int: float = 0.0  # Pitch diameter (internal)
    minor_diameter_int: float = 0.0  # Minor diameter (internal)

    # Thread profile geometry
    profile_angle_deg: float = 60.0  # Thread angle (60° for ISO/UNC/UNF, 29° ACME, 30° trap)
    taper_per_mm: float = 0.0       # Taper rate (NPT/BSPT only), 0 = parallel

    # Drill sizes
    tap_drill_mm: float = 0.0       # Recommended tap drill
    clearance_hole_close_mm: float = 0.0
    clearance_hole_medium_mm: float = 0.0
    clearance_hole_free_mm: float = 0.0

    # Imperial convenience (stored alongside mm values)
    tpi: float | None = None         # Threads per inch (imperial families)
    nominal_size_inch: str | None = None  # e.g., "1/4", "#10"

    # Metadata
    standard_ref: str = ""           # e.g., "ISO 261", "ASME B1.1"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for API/DB storage."""
        ...
```

### 3.2 Data Organization Pattern

Follow the established pattern from `hardware.py` but use dicts of `ThreadSpec` instead of tuples:

```python
# Organized by family, then keyed by size string
ISO_METRIC_COARSE: dict[str, ThreadSpec] = {
    "M2": ThreadSpec(
        family=ThreadFamily.ISO_METRIC,
        size="M2",
        pitch_mm=0.4,
        pitch_series=PitchSeries.COARSE,
        major_diameter=2.0,
        pitch_diameter_ext=1.740,
        minor_diameter_ext=1.509,
        # ...
    ),
    "M3": ThreadSpec(...),
    # ...
}

ISO_METRIC_FINE: dict[str, ThreadSpec] = { ... }
UNC_THREADS: dict[str, ThreadSpec] = { ... }
# etc.
```

### 3.3 Lookup Registry

```python
# Single registry combining all families
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


def get_thread_spec(
    family: ThreadFamily,
    size: str,
    pitch_series: PitchSeries | None = None,
) -> ThreadSpec:
    """Look up a thread specification by family and size."""
    ...


def list_thread_sizes(
    family: ThreadFamily,
    pitch_series: PitchSeries | None = None,
) -> list[str]:
    """List available sizes for a thread family."""
    ...


def list_thread_families() -> list[ThreadFamily]:
    """List all supported thread families."""
    ...
```

### 3.4 Database Representation

Thread specs seed into the existing `ReferenceComponent` model as library entries:

| Field | Value |
|-------|-------|
| `category` | `"thread_standard"` |
| `subcategory` | Family name (e.g., `"iso_metric"`, `"unc"`) |
| `name` | Size string (e.g., `"M8x1.25 Coarse"`) |
| `source_type` | `"library"` |
| `dimensions` (JSONB) | `{major_diameter, pitch_mm, ...}` — full `ThreadSpec.to_dict()` |
| `tags` (JSONB) | `["metric", "coarse", "M8"]` |

This reuses the existing seeding pattern from `components_v2.py` — no new tables required.

### 3.5 Print Optimization Layer

Print adjustments are **not stored as separate specs**. Instead, the print optimizer is a **runtime transformation**:

```python
@dataclass
class PrintThreadConfig:
    """Configuration for print-optimized threads."""
    process: PrintProcess          # fdm, sla, sls
    clearance_mm: float | None     # None = use process default
    tolerance: ToleranceClass      # tight, normal, loose
    flat_bottom: bool = False      # Flatten roots/crests for FDM
    add_chamfer: bool = True       # Lead-in chamfer

class PrintProcess(StrEnum):
    FDM = "fdm"
    SLA = "sla"
    SLS = "sls"

class ToleranceClass(StrEnum):
    TIGHT = "tight"
    NORMAL = "normal"
    LOOSE = "loose"

@dataclass
class PrintThreadResult:
    """Result of print-optimized thread generation."""
    geometry: Part                         # Build123d Part
    original_spec: ThreadSpec              # Standard dimensions
    adjusted_spec: dict[str, float]        # Modified dimensions
    clearance_applied_mm: float
    process: PrintProcess
    orientation_recommendation: str        # "vertical", "horizontal", "any"
    orientation_reasoning: str
    warnings: list[str]
    recommended_nozzle_mm: float
    recommended_layer_height_mm: float
```

---

## 4. API Design Guidance

### 4.1 New Router: `backend/app/api/v2/threads.py`

Following the existing pattern in `backend/app/api/v2/` (see `components.py`, `enclosures.py`):

```python
router = APIRouter(prefix="/threads", tags=["threads"])
```

### 4.2 Endpoints

#### Browse & Lookup (Read-only, no auth required beyond base API key)

| Method | Path | Description | Query Params |
|--------|------|-------------|-------------|
| `GET` | `/api/v2/threads/families` | List all thread families | — |
| `GET` | `/api/v2/threads/sizes` | List sizes for a family | `family` (required), `pitch_series` (optional) |
| `GET` | `/api/v2/threads/{family}/{size}` | Get full spec for a thread | — |
| `GET` | `/api/v2/threads/search` | Search threads by query | `q`, `family`, `min_diameter`, `max_diameter` |

#### Geometry Generation (Authenticated, rate-limited)

| Method | Path | Description | Body |
|--------|------|-------------|------|
| `POST` | `/api/v2/threads/generate` | Generate thread geometry | `ThreadGenerateRequest` |
| `POST` | `/api/v2/threads/generate/print-optimized` | Generate print-optimized thread | `PrintOptimizedThreadRequest` |

#### Reference Data

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v2/threads/{family}/{size}/tap-drill` | Get tap drill info |
| `GET` | `/api/v2/threads/{family}/{size}/clearance-holes` | Get clearance hole sizes |

### 4.3 Request/Response Schemas

```python
# --- Pydantic models in backend/app/schemas/threads.py ---

class ThreadFamilyResponse(BaseModel):
    """Available thread families."""
    families: list[ThreadFamilyInfo]

class ThreadFamilyInfo(BaseModel):
    id: str                    # e.g., "iso_metric"
    name: str                  # e.g., "ISO Metric"
    description: str
    standard_ref: str          # e.g., "ISO 261"
    pitch_series: list[str]    # e.g., ["coarse", "fine"]
    size_count: int

class ThreadSizeListResponse(BaseModel):
    """Available sizes for a thread family."""
    family: str
    pitch_series: str | None
    sizes: list[ThreadSizeSummary]

class ThreadSizeSummary(BaseModel):
    size: str                  # e.g., "M8"
    pitch_mm: float
    major_diameter_mm: float
    description: str           # e.g., "M8 x 1.25 Coarse"

class ThreadSpecResponse(BaseModel):
    """Full thread specification."""
    family: str
    size: str
    pitch_mm: float
    pitch_series: str | None
    major_diameter: float
    pitch_diameter_ext: float
    minor_diameter_ext: float
    pitch_diameter_int: float
    minor_diameter_int: float
    profile_angle_deg: float
    taper_per_mm: float
    tap_drill_mm: float
    clearance_hole_close_mm: float
    clearance_hole_medium_mm: float
    clearance_hole_free_mm: float
    tpi: float | None
    standard_ref: str

class ThreadGenerateRequest(BaseModel):
    """Request to generate thread geometry."""
    family: str = Field(..., description="Thread family: iso_metric, unc, unf, npt, etc.")
    size: str = Field(..., description="Thread size: M8, 1/4-20, etc.")
    thread_type: str = Field(..., pattern="^(internal|external)$")
    length_mm: float = Field(..., gt=0, le=500)
    pitch_series: str | None = Field(None, description="coarse/fine (metric only)")
    # Optional overrides
    custom_pitch_mm: float | None = Field(None, gt=0)
    custom_diameter_mm: float | None = Field(None, gt=0)

class PrintOptimizedThreadRequest(ThreadGenerateRequest):
    """Request to generate print-optimized thread."""
    process: str = Field("fdm", pattern="^(fdm|sla|sls)$")
    clearance_mm: float | None = Field(None, ge=0.05, le=2.0)
    tolerance: str = Field("normal", pattern="^(tight|normal|loose)$")
    flat_bottom: bool = Field(False)
    add_chamfer: bool = Field(True)

class ThreadGenerateResponse(BaseModel):
    """Response from thread generation."""
    thread_spec: ThreadSpecResponse
    file_urls: dict[str, str]       # {"step": "/downloads/xxx.step", "stl": "/downloads/xxx.stl"}
    metadata: dict[str, Any]
    generation_time_ms: int

class PrintOptimizedThreadResponse(ThreadGenerateResponse):
    """Response from print-optimized thread generation."""
    original_spec: ThreadSpecResponse
    adjusted_dimensions: dict[str, float]
    clearance_applied_mm: float
    process: str
    tolerance_class: str
    orientation_recommendation: str
    orientation_reasoning: str
    warnings: list[str]
    recommended_nozzle_mm: float
    recommended_layer_height_mm: float
```

### 4.4 Security Considerations for API

- **Authentication:** All `POST` (generate) endpoints require `current_user: User = Depends(get_current_user)`.
- **Rate limiting:** Thread geometry generation is CPU-intensive. Apply stricter rate limits (e.g., 10 req/min per user) via existing middleware.
- **Input validation:** All numeric inputs validated via Pydantic `Field(gt=0, le=...)` constraints. Family/size validated against the thread registry (reject unknown combinations early).
- **Logging:** Log all generation requests with user ID, parameters, and timing for security monitoring.
- **No secrets exposure:** Thread data is public reference data — no sensitive information concerns.

---

## 5. UI/UX Considerations

### 5.1 Thread Insertion Wizard — Component Design

The wizard should be a **multi-step modal dialog** accessible from:
- The CAD toolbar in the 3D viewport ("Add Thread" button)
- The component library page under a "Threads" category

#### Step 1: Thread Family Selection

```
┌─────────────────────────────────────────────────┐
│  Add Thread                              [X]    │
│─────────────────────────────────────────────────│
│                                                 │
│  Select Thread Standard                         │
│                                                 │
│  ┌─────────────┐  ┌─────────────┐               │
│  │  ISO Metric  │  │    UNC      │               │
│  │  (M2–M68)   │  │  (#0–4")    │               │
│  │  ★ Common   │  │             │               │
│  └─────────────┘  └─────────────┘               │
│  ┌─────────────┐  ┌─────────────┐               │
│  │    UNF      │  │    NPT      │               │
│  │  (#0–1.5")  │  │  Pipe       │               │
│  └─────────────┘  └─────────────┘               │
│  ┌─────────────┐  ┌─────────────┐               │
│  │    BSP      │  │   ACME /    │               │
│  │  Pipe       │  │ Trapezoidal │               │
│  └─────────────┘  └─────────────┘               │
│                                                 │
│                         [Next →]                │
└─────────────────────────────────────────────────┘
```

#### Step 2: Size & Configuration

```
┌─────────────────────────────────────────────────┐
│  Add Thread — ISO Metric                 [X]    │
│─────────────────────────────────────────────────│
│                                                 │
│  Pitch Series:  [● Coarse] [○ Fine]             │
│                                                 │
│  Size:  [ M8 ▼ ]                                │
│  ┌──── Quick sizes ────────────────────┐        │
│  │ M3  M4  M5  M6  [M8]  M10  M12    │        │
│  └─────────────────────────────────────┘        │
│                                                 │
│  Type:  [● External] [○ Internal]               │
│                                                 │
│  Thread Length:  [ 20.0 ] mm                    │
│                                                 │
│  ┌─── Specification ──────────────────┐         │
│  │ Major Ø:     8.000 mm              │         │
│  │ Pitch:       1.250 mm              │         │
│  │ Minor Ø:     6.647 mm              │         │
│  │ Tap Drill:   6.800 mm              │         │
│  │ Clearance:   8.400 mm (close)      │         │
│  └────────────────────────────────────┘         │
│                                                 │
│  [← Back]                    [Next →]           │
└─────────────────────────────────────────────────┘
```

#### Step 3: Print Optimization (Optional)

```
┌─────────────────────────────────────────────────┐
│  Add Thread — Print Optimization         [X]    │
│─────────────────────────────────────────────────│
│                                                 │
│  ☑ Enable Print Optimization                    │
│                                                 │
│  Process:  [● FDM] [○ SLA] [○ SLS]             │
│                                                 │
│  Tolerance: [○ Tight] [● Normal] [○ Loose]     │
│                                                 │
│  FDM Options:                                   │
│  ☑ Flat-bottom thread roots (recommended)       │
│  ☑ Add lead-in chamfer                          │
│                                                 │
│  Clearance:  [0.40] mm  (FDM default)           │
│                                                 │
│  ┌─── Print Adjustments ──────────────┐         │
│  │ Original Major Ø:   8.000 mm       │         │
│  │ Adjusted Major Ø:   7.600 mm  ←    │         │
│  │ Clearance Applied:  0.400 mm       │         │
│  └────────────────────────────────────┘         │
│                                                 │
│  ⓘ Recommended: Print with thread axis          │
│    vertical (parallel to Z). Layer height        │
│    ≤ 0.15mm for best results.                   │
│                                                 │
│  ⚠ M8 threads print well on FDM.               │
│                                                 │
│  [← Back]                  [Generate →]         │
└─────────────────────────────────────────────────┘
```

#### Step 4: Preview & Download

```
┌─────────────────────────────────────────────────┐
│  Thread Preview                          [X]    │
│─────────────────────────────────────────────────│
│                                                 │
│  ┌─────────────────────────────────────┐        │
│  │                                     │        │
│  │    [React Three Fiber 3D Preview]   │        │
│  │    Rotatable thread cross-section   │        │
│  │    with dimension annotations       │        │
│  │                                     │        │
│  └─────────────────────────────────────┘        │
│                                                 │
│  ┌─── Reference ──────────────────────┐         │
│  │ Tap Drill:    6.8mm                │         │
│  │ Clearance:    8.4mm (close)        │         │
│  │ Orientation:  Vertical (Z-axis)    │         │
│  │ Nozzle:       ≤ 0.4mm             │         │
│  │ Layer Height: ≤ 0.15mm            │         │
│  └────────────────────────────────────┘         │
│                                                 │
│  [Download STEP]  [Download STL]  [Add to Part] │
│                                                 │
│  [← Back]                        [Done]         │
└─────────────────────────────────────────────────┘
```

### 5.2 Component Library Page Integration

Add a "Threads" category to the existing `ComponentLibraryPage`:

- New category icon: a thread/screw icon (use Lucide `Wrench` or `Cog`)
- Filter by thread family as subcategory
- Click a thread size to open specifications panel (reuse `ComponentSpecsViewer` pattern)
- "Generate" button on each thread spec card opens the wizard at Step 3

### 5.3 Tap Drill Reference Display

Always visible in the specification panel whenever a thread is selected:

```
┌─── Tap & Clearance Reference ───────────────┐
│                                              │
│  Tap Drill Sizes                             │
│  ├── Standard:    6.80 mm (recommended)      │
│  └── 75% thread:  6.80 mm                   │
│                                              │
│  Clearance Holes                             │
│  ├── Close fit:   8.40 mm                    │
│  ├── Medium fit:  9.00 mm                    │
│  └── Free fit:    10.00 mm                   │
│                                              │
│  Print Reference                             │
│  ├── FDM hole Ø:  8.80 mm (+0.40mm)         │
│  └── SLA hole Ø:  8.55 mm (+0.15mm)         │
│                                              │
└──────────────────────────────────────────────┘
```

### 5.4 Frontend Components (New Files)

| Component | Path | Description |
|-----------|------|-------------|
| `ThreadWizard` | `frontend/src/components/threads/ThreadWizard.tsx` | Multi-step modal |
| `ThreadFamilySelector` | `frontend/src/components/threads/ThreadFamilySelector.tsx` | Step 1 card grid |
| `ThreadSizeSelector` | `frontend/src/components/threads/ThreadSizeSelector.tsx` | Step 2 with spec preview |
| `PrintOptimizationForm` | `frontend/src/components/threads/PrintOptimizationForm.tsx` | Step 3 FDM/SLA config |
| `ThreadPreview3D` | `frontend/src/components/threads/ThreadPreview3D.tsx` | R3F cross-section view |
| `TapDrillReference` | `frontend/src/components/threads/TapDrillReference.tsx` | Reference data card |
| `useThreadFamilies` | `frontend/src/hooks/useThreadFamilies.ts` | React Query hook for families |
| `useThreadSpec` | `frontend/src/hooks/useThreadSpec.ts` | React Query hook for spec lookup |
| `useThreadGenerate` | `frontend/src/hooks/useThreadGenerate.ts` | Mutation hook for generation |
| `threadsApi` | `frontend/src/lib/api/threads.ts` | API client functions |

---

## 6. Edge Cases and Constraints

### 6.1 Build123d Helix/Sweep Performance

| Concern | Detail | Mitigation |
|---------|--------|------------|
| **OCCT helix sweep is slow** | Sweeping a thread profile along a helix path generates complex BRep geometry. For long threads (>50mm) or fine pitches, this can take 10–60+ seconds. | Implement a segmented approach: generate one revolution, then pattern it. Cache generated geometry for repeat requests. Set hard timeouts (60s). |
| **Memory consumption** | Thread geometry has high face/edge counts. An M10x100mm thread could produce 50k+ faces. | Limit maximum thread length to 200mm in the API. Use mesh simplification for STL output. Warn if estimated face count > 100k. |
| **OCCT sweep failures** | Helix sweeps in OCCT can fail with degenerate profiles or extreme parameters (very fine pitch, very large diameter). | Validate that `pitch > 0.2mm` and `length/pitch < 500 revolutions`. Catch OCCT kernel errors and return meaningful `GeometryError`. |

### 6.2 Thread Pitch Accuracy

| Concern | Detail | Mitigation |
|---------|--------|------------|
| **Floating-point pitch accumulation** | Over many revolutions, floating-point errors could cause pitch drift. | Use Build123d's parametric helix (defined by pitch, not incremental rotation). Validate total length vs. expected `n_turns * pitch`. |
| **Mixed unit confusion** | Imperial threads defined in TPI, metric in mm pitch. Easy to confuse. | Store everything internally in mm. Convert TPI → mm pitch at data entry time: `pitch_mm = 25.4 / tpi`. Display both in UI. |
| **Non-standard pitches** | Users may enter custom pitches that don't match any standard. | Allow custom pitches with a warning banner: "This is not a standard thread pitch. Mating parts must use the same custom specification." |

### 6.3 Print Feasibility of Small Threads

| Thread | FDM (0.4mm nozzle) | SLA (0.05mm) | Recommendation |
|--------|--------------------|--------------|----|
| M2 (0.4mm pitch) | ❌ Not printable | ⚠️ Marginal | Use heat-set insert (already in `hardware.py`) |
| M3 (0.5mm pitch) | ⚠️ Marginal | ✅ OK | FDM: recommend insert. SLA: OK with clearance. |
| M4 (0.7mm pitch) | ⚠️ Functional with loose tolerance | ✅ Good | FDM: loose tolerance + flat bottom |
| M5 (0.8mm pitch) | ✅ Functional | ✅ Good | FDM: normal tolerance |
| M6+ (1.0mm+ pitch) | ✅ Good | ✅ Excellent | Standard clearance sufficient |
| ACME/Trapezoidal 8mm+ | ✅ Excellent | ✅ Excellent | Best for FDM due to flat crests |

**Implementation:** The print optimizer should return a `feasibility_rating` (not_recommended, marginal, good, excellent) and cross-reference the existing `THREADED_INSERTS` data from `hardware.py` when recommending alternatives.

### 6.4 Clearance Calculations for 3D Printing

| Process | Default Clearance | Reasoning |
|---------|------------------|-----------|
| FDM (0.4mm nozzle) | 0.4mm per side | One nozzle width accounts for over-extrusion, elephants foot, and layer staircase effect |
| FDM (0.6mm nozzle) | 0.5mm per side | Larger nozzle = more material spread |
| SLA | 0.15mm per side | Resin shrinkage and overcure at edges |
| SLS | 0.20mm per side | Powder sintering expansion |

**Edge case:** Users printing in exotic materials (TPU, nylon) may need different clearances. Support configurable clearance while providing sensible defaults.

### 6.5 Tapered Threads (NPT/BSPT)

| Concern | Detail | Mitigation |
|---------|--------|------------|
| **Taper complicates helix** | NPT taper is 1:16 along thread axis. The helix must follow a conical surface, not cylindrical. | Use Build123d's conical helix or sweep along a tapered path. Test this early — it's the most complex geometry case. |
| **Engagement length matters** | NPT threads seal by interference — the engagement length determines seal quality. | Include `engagement_length_mm` in the NPT thread spec. UI should display it prominently. |
| **Not for 3D printing** | Tapered pipe threads are generally not suitable for functional 3D prints (they rely on deformation for sealing). | Display a warning for NPT/BSPT when print optimization is enabled: "Tapered pipe threads are for reference only. For printed fluid connections, consider O-ring grooves." |

### 6.6 Thread Direction

| Concern | Detail | Mitigation |
|---------|--------|------------|
| **Left-hand threads** | Some applications require left-hand threads (LH). Not common but occasionally needed. | Support a `hand` parameter (`right`/`left`, default `right`). The helix direction reverses for LH threads. Include in `ThreadSpec` but deprioritize in initial implementation. |

### 6.7 Concurrency and Caching

| Concern | Detail | Mitigation |
|---------|--------|------------|
| **Concurrent generation requests** | Thread generation is CPU-heavy. Multiple simultaneous requests could starve the server. | Route generation through Celery worker (existing pattern). Limit concurrent CAD tasks per user. |
| **Duplicate generation** | Users may generate the same standard thread repeatedly. | Cache generated STEP/STL files by a hash of `(family, size, type, length, print_config)`. Serve from cache on repeat requests. Use Redis (already in stack). |

---

## 7. Security Considerations

Per the project's security requirements and the attached review instructions:

### Authentication & Authorization
- All `GET` endpoints (browse/search) require base API authentication (API key or JWT)
- All `POST` endpoints (generate) require full user authentication via `Depends(get_current_user)`
- Thread library data is read-only for non-admin users; only admins can modify seed data

### Input Validation & Sanitization
- All numeric parameters validated via Pydantic `Field()` constraints with explicit `gt`, `le` bounds
- Family and size strings validated against the in-memory registry (whitelist, not regex)
- File path parameters (for downloads) validated against allowed directories
- Custom pitch/diameter validated for geometric feasibility (not just type correctness)

### Rate Limiting & Throttling
- Thread generation endpoints: 10 requests/minute per user (CPU-intensive operation)
- Thread browse/search endpoints: 60 requests/minute per user (standard read rate)
- Enforce via existing rate-limiting middleware

### Logging & Monitoring
- Log all generation requests with: user ID, thread parameters, generation time, success/failure
- Log failed validation attempts (potential fuzzing/abuse)
- Export generation timing as Prometheus metric (`thread_generation_duration_seconds` histogram)
- Alert on sustained generation times > 30s (performance regression indicator)

### Resource Protection
- Hard timeout of 60s on geometry generation (prevent OCCT infinite loops)
- Maximum thread length of 200mm (prevent memory exhaustion)
- Maximum concurrent generation tasks per user: 3

---

## Appendix A: File Structure for Implementation

```
backend/app/cad/
├── threads.py               # ThreadSpec, ThreadFamily, ThreadType, registries, lookups (#248)
├── thread_generator.py      # Helix/sweep geometry generation using Build123d (#247)
├── thread_print_optimizer.py # Print clearance adjustments, recommendations (#249)
├── hardware.py              # UNCHANGED — existing hardware catalog

backend/app/schemas/
├── threads.py               # Pydantic request/response models for API

backend/app/api/v2/
├── threads.py               # FastAPI router with endpoints

backend/app/seeds/
├── threads.py               # Seed thread data into ReferenceComponent table

backend/tests/cad/
├── test_threads.py          # Thread spec data tests
├── test_thread_generator.py # Geometry generation tests
├── test_thread_print_optimizer.py # Print optimization tests

backend/tests/api/
├── test_threads_api.py      # API endpoint tests

frontend/src/components/threads/
├── ThreadWizard.tsx
├── ThreadFamilySelector.tsx
├── ThreadSizeSelector.tsx
├── PrintOptimizationForm.tsx
├── ThreadPreview3D.tsx
├── TapDrillReference.tsx

frontend/src/hooks/
├── useThreadFamilies.ts
├── useThreadSpec.ts
├── useThreadGenerate.ts

frontend/src/lib/api/
├── threads.ts               # API client

frontend/src/components/threads/
├── __tests__/
│   ├── ThreadWizard.test.tsx
│   ├── ThreadFamilySelector.test.tsx
│   ├── ThreadSizeSelector.test.tsx
│   ├── PrintOptimizationForm.test.tsx
│   └── TapDrillReference.test.tsx
```

## Appendix B: Definition of Done Checklist

| Criterion | Sub-Issue | Verification |
|-----------|-----------|--------------|
| Standard metric threads available (M2–M68 coarse + common fine) | #248 | Unit test spot-checks against ISO 261 tables |
| UNC/UNF threads available | #248 | Unit test spot-checks against ASME B1.1 |
| NPT/BSP pipe threads available | #248 | Unit test spot-checks |
| ACME/Trapezoidal threads available | #248 | Unit test spot-checks |
| Thread geometry generator produces valid Build123d Parts | #247 | Volume > 0, bounding box within tolerance |
| Internal and external threads supported | #247 | Both types tested per family |
| Thread insertion wizard in UI | #247 + FE | Playwright E2E: open wizard, select M8, generate |
| Print-optimized profiles for FDM | #249 | Clearance correctly applied; dimensions verified |
| Tap drill sizes shown for reference | #248 + FE | Visible in wizard Step 2 + spec viewer |
| All endpoints protected by auth | All | Integration tests with/without auth token |
| Rate limiting on generation endpoints | #247 | Load test: 11th request in 1 min returns 429 |
| ≥80% test coverage on new modules | All | `pytest --cov` report |
