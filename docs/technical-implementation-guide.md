# Technical Implementation Guide
# AI Part Designer - Sprint 1

**Tech Lead:** Technical Lead  
**Date:** 2026-01-24  
**Sprint:** 1 (Foundation Setup)  

---

## 1. Codebase Assessment

### Current State Analysis

| Component | Status | Notes |
|-----------|--------|-------|
| **Core Infrastructure** | ✅ Complete | config, database, cache, storage |
| **Security** | ✅ Complete | auth, encryption, middleware, RBAC |
| **Models** | ✅ Complete | User, Project, Design, Template, Job, etc. |
| **Repositories** | ✅ Complete | BaseRepository + domain repos |
| **Worker Infrastructure** | ✅ Complete | Celery tasks (CAD, AI, export, maintenance) |
| **Migrations** | ✅ Complete | Initial schema migration |
| **Docker Compose** | ✅ Complete | All services defined |
| **Makefile** | ✅ Complete | Dev commands |
| **API Endpoints** | ❌ Missing | No FastAPI routes yet |
| **CAD Engine** | ❌ Missing | No CadQuery integration |
| **AI Integration** | ❌ Missing | No OpenAI client |
| **Frontend** | ❌ Missing | No frontend code |
| **CI/CD** | ❌ Missing | No GitHub Actions |
| **Backend Dockerfile** | ❌ Missing | Need to create |
| **pyproject.toml** | ❌ Missing | Need for dependency management |

### Technical Debt Assessment

**Low Priority (Phase 2+):**
- Celery tasks have placeholder implementations
- Some model relationships may need optimization
- Worker tasks need integration with actual CadQuery

**No Immediate Concerns:**
- Code follows consistent patterns
- Security infrastructure is comprehensive
- Repository pattern well implemented

---

## 2. Sprint 1 Technical Plan

### 2.1 Priority Order (Critical Path)

```
1. pyproject.toml + Dependencies
2. Backend Dockerfile  
3. CAD Primitives (P0.1.1.2)
4. Boolean Operations (P0.1.1.3)
5. STEP/STL Export (P0.1.1.5)
6. GitHub Actions (P0.2.2.1)
```

### 2.2 File Structure for Sprint 1

```
backend/
├── pyproject.toml          # NEW: Dependencies
├── Dockerfile              # NEW: Multi-stage build
├── app/
│   ├── cad/               # NEW: CAD engine package
│   │   ├── __init__.py
│   │   ├── primitives.py   # Basic shapes
│   │   ├── operations.py   # Boolean ops
│   │   └── export.py       # File export
│   └── api/               # NEW: API routes (Sprint 3)
│       └── v1/
├── tests/
│   ├── conftest.py        # NEW: Test fixtures
│   └── cad/               # NEW: CAD tests
│       ├── __init__.py
│       ├── test_primitives.py
│       ├── test_operations.py
│       └── test_export.py
.github/
└── workflows/
    ├── test.yml           # NEW: Test workflow
    ├── lint.yml           # NEW: Lint workflow
    └── build.yml          # NEW: Build workflow
```

---

## 3. Implementation Standards

### 3.1 Python Code Standards

```python
# File: All Python files should follow this template

"""
Module docstring explaining the purpose.

Example:
    >>> from app.cad.primitives import create_box
    >>> box = create_box(100, 50, 30)
"""

from __future__ import annotations

# Standard library imports
from pathlib import Path
from typing import TYPE_CHECKING, Literal
from uuid import UUID

# Third-party imports
import cadquery as cq

# Local imports
from app.core.config import settings

if TYPE_CHECKING:
    from app.models import Design


# Constants at module level
DEFAULT_TOLERANCE = 0.1  # mm


def create_box(
    length: float,
    width: float,
    height: float,
    *,  # Force keyword arguments after this
    center: bool = True,
) -> cq.Workplane:
    """
    Create a box primitive.
    
    Args:
        length: Box length in mm (X axis)
        width: Box width in mm (Y axis)
        height: Box height in mm (Z axis)
        center: If True, center on XY plane (default)
    
    Returns:
        CadQuery Workplane containing the box
    
    Raises:
        ValueError: If any dimension is <= 0
        
    Example:
        >>> box = create_box(100, 50, 30)
        >>> box.val().Volume()  # Returns volume in mm³
        150000.0
    """
    if length <= 0 or width <= 0 or height <= 0:
        raise ValueError("All dimensions must be positive")
    
    return cq.Workplane("XY").box(length, width, height, centered=center)
```

### 3.2 Error Handling Pattern

```python
# Define domain-specific exceptions
class CADError(Exception):
    """Base exception for CAD operations."""
    pass


class GeometryError(CADError):
    """Invalid geometry or operation result."""
    pass


class ExportError(CADError):
    """File export failed."""
    pass


# Use in functions
def export_step(shape: cq.Workplane, filepath: Path) -> None:
    """Export shape to STEP format."""
    try:
        # Validate input
        if not shape.val():
            raise GeometryError("Cannot export empty shape")
        
        # Atomic write (temp file + rename)
        temp_path = filepath.with_suffix('.tmp')
        shape.val().exportStep(str(temp_path))
        temp_path.rename(filepath)
        
    except OSError as e:
        raise ExportError(f"Failed to write file: {e}") from e
```

### 3.3 Testing Standards

```python
# tests/cad/test_primitives.py
"""Tests for CAD primitive generation."""

import pytest
import cadquery as cq

from app.cad.primitives import create_box, create_cylinder, create_sphere
from app.cad.exceptions import GeometryError


class TestCreateBox:
    """Test cases for create_box function."""
    
    def test_creates_box_with_correct_dimensions(self):
        """Box should have exact specified dimensions."""
        box = create_box(100, 50, 30)
        bb = box.val().BoundingBox()
        
        assert bb.xlen == pytest.approx(100, abs=0.01)
        assert bb.ylen == pytest.approx(50, abs=0.01)
        assert bb.zlen == pytest.approx(30, abs=0.01)
    
    def test_box_volume_is_correct(self):
        """Volume should equal length * width * height."""
        box = create_box(100, 50, 30)
        expected_volume = 100 * 50 * 30
        
        assert box.val().Volume() == pytest.approx(expected_volume, rel=0.001)
    
    def test_rejects_zero_dimension(self):
        """Should raise ValueError for zero dimensions."""
        with pytest.raises(ValueError, match="must be positive"):
            create_box(0, 50, 30)
    
    def test_rejects_negative_dimension(self):
        """Should raise ValueError for negative dimensions."""
        with pytest.raises(ValueError, match="must be positive"):
            create_box(-10, 50, 30)
    
    @pytest.mark.parametrize("length,width,height", [
        (1, 1, 1),           # Minimum reasonable
        (0.1, 0.1, 0.1),     # Very small
        (1000, 1000, 1000),  # Large
    ])
    def test_handles_edge_case_dimensions(self, length, width, height):
        """Should handle edge case dimensions."""
        box = create_box(length, width, height)
        assert box.val().Volume() > 0
```

### 3.4 Logging Standards

```python
import logging
from app.core.config import settings

# Get logger for module
logger = logging.getLogger(__name__)

def generate_shape(params: dict) -> cq.Workplane:
    """Generate shape with logging."""
    logger.info(
        "Generating shape",
        extra={
            "shape_type": params.get("shape"),
            "dimensions": params.get("dimensions"),
        }
    )
    
    try:
        shape = _create_shape(params)
        logger.info(
            "Shape generated successfully",
            extra={"volume": shape.val().Volume()}
        )
        return shape
        
    except Exception as e:
        logger.error(
            "Shape generation failed",
            extra={"error": str(e), "params": params},
            exc_info=True,
        )
        raise
```

---

## 4. Detailed Implementation Specs

### 4.1 pyproject.toml

```toml
[project]
name = "ai-part-designer"
version = "0.1.0"
description = "AI-powered 3D part generation"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    # Web framework
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    
    # Database
    "sqlalchemy[asyncio]>=2.0.25",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    
    # Cache & Queue
    "redis>=5.0.0",
    "celery>=5.3.0",
    
    # CAD - Critical for Sprint 1
    "cadquery>=2.4.0",
    
    # AI
    "openai>=1.10.0",
    
    # Auth & Security
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "cryptography>=42.0.0",
    
    # Storage
    "boto3>=1.34.0",
    
    # Utilities
    "python-multipart>=0.0.6",
    "httpx>=0.26.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.12.0",
    "ruff>=0.1.14",
    "mypy>=1.8.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-v --tb=short"

[tool.ruff]
target-version = "py311"
line-length = 100
select = ["E", "F", "W", "I", "N", "UP", "B", "C4"]

[tool.mypy]
python_version = "3.11"
strict = true
plugins = ["pydantic.mypy"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 4.2 Backend Dockerfile

```dockerfile
# Multi-stage Dockerfile for AI Part Designer Backend

# =============================================================================
# Base stage with system dependencies
# =============================================================================
FROM python:3.11-slim as base

# Install system dependencies for CadQuery/OpenCASCADE
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglu1-mesa \
    libxrender1 \
    libxext6 \
    libsm6 \
    libice6 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# =============================================================================
# Development stage
# =============================================================================
FROM base as development

# Install dev dependencies
RUN pip install --no-cache-dir pip-tools

# Copy requirements and install
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

# Copy source code
COPY . .

# Expose port
EXPOSE 8000

# Development command with hot reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# =============================================================================
# Production stage
# =============================================================================
FROM base as production

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Copy requirements and install production only
COPY pyproject.toml .
RUN pip install --no-cache-dir . && rm -rf ~/.cache

# Copy source code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Production command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 4.3 CAD Primitives Implementation

```python
# backend/app/cad/primitives.py
"""
CAD primitive generation using CadQuery.

Provides parameterized 3D shape creation for basic primitives.
All dimensions are in millimeters unless otherwise specified.
"""

from __future__ import annotations

import cadquery as cq

from app.cad.exceptions import GeometryError


def create_box(
    length: float,
    width: float,
    height: float,
    *,
    centered: bool = True,
) -> cq.Workplane:
    """
    Create a box (rectangular prism) primitive.
    
    Args:
        length: Box length in mm (X axis)
        width: Box width in mm (Y axis)
        height: Box height in mm (Z axis)
        centered: Center the box on XY plane at Z=0
    
    Returns:
        CadQuery Workplane containing the box
    
    Raises:
        ValueError: If any dimension is <= 0
    """
    _validate_positive_dimensions(length=length, width=width, height=height)
    
    # CadQuery centered=(True,True,True) centers on all axes
    # We want centered on XY but sitting on Z=0
    box = cq.Workplane("XY").box(length, width, height, centered=(centered, centered, False))
    
    return box


def create_cylinder(
    radius: float,
    height: float,
    *,
    centered: bool = True,
) -> cq.Workplane:
    """
    Create a cylinder primitive.
    
    Args:
        radius: Cylinder radius in mm
        height: Cylinder height in mm (Z axis)
        centered: Center the cylinder on XY plane at Z=0
    
    Returns:
        CadQuery Workplane containing the cylinder
    
    Raises:
        ValueError: If radius or height is <= 0
    """
    _validate_positive_dimensions(radius=radius, height=height)
    
    cylinder = cq.Workplane("XY").cylinder(
        height,
        radius,
        centered=(centered, centered, False)
    )
    
    return cylinder


def create_sphere(
    radius: float,
    *,
    centered: bool = True,
) -> cq.Workplane:
    """
    Create a sphere primitive.
    
    Args:
        radius: Sphere radius in mm
        centered: If True, center at origin; if False, place tangent to XY plane
    
    Returns:
        CadQuery Workplane containing the sphere
    
    Raises:
        ValueError: If radius is <= 0
    """
    _validate_positive_dimensions(radius=radius)
    
    sphere = cq.Workplane("XY").sphere(radius)
    
    if not centered:
        # Move sphere up so it sits on XY plane
        sphere = sphere.translate((0, 0, radius))
    
    return sphere


def create_cone(
    radius_bottom: float,
    radius_top: float,
    height: float,
    *,
    centered: bool = True,
) -> cq.Workplane:
    """
    Create a cone or truncated cone (frustum) primitive.
    
    Args:
        radius_bottom: Bottom radius in mm
        radius_top: Top radius in mm (0 for pointed cone)
        height: Height in mm (Z axis)
        centered: Center on XY plane at Z=0
    
    Returns:
        CadQuery Workplane containing the cone
    """
    _validate_positive_dimensions(height=height)
    if radius_bottom < 0 or radius_top < 0:
        raise ValueError("Radii must be non-negative")
    if radius_bottom == 0 and radius_top == 0:
        raise ValueError("At least one radius must be positive")
    
    # Use loft between circles or revolution
    if radius_top == 0:
        # Simple cone
        result = (
            cq.Workplane("XY")
            .circle(radius_bottom)
            .workplane(offset=height)
            .center(0, 0)
            .circle(0.001)  # Near-zero for point
            .loft()
        )
    else:
        # Truncated cone
        result = (
            cq.Workplane("XY")
            .circle(radius_bottom)
            .workplane(offset=height)
            .circle(radius_top)
            .loft()
        )
    
    return result


def _validate_positive_dimensions(**dimensions: float) -> None:
    """Validate that all dimensions are positive."""
    for name, value in dimensions.items():
        if value <= 0:
            raise ValueError(f"{name} must be positive, got {value}")
```

### 4.4 Boolean Operations Implementation

```python
# backend/app/cad/operations.py
"""
Boolean and transformation operations for CadQuery shapes.
"""

from __future__ import annotations

import cadquery as cq

from app.cad.exceptions import GeometryError


def union(*shapes: cq.Workplane) -> cq.Workplane:
    """
    Combine multiple shapes into one (boolean union).
    
    Args:
        *shapes: Two or more shapes to combine
    
    Returns:
        Combined shape
    
    Raises:
        ValueError: If fewer than 2 shapes provided
    """
    if len(shapes) < 2:
        raise ValueError("Union requires at least 2 shapes")
    
    result = shapes[0]
    for shape in shapes[1:]:
        result = result.union(shape)
    
    return result


def difference(base: cq.Workplane, *tools: cq.Workplane) -> cq.Workplane:
    """
    Subtract tools from base shape (boolean difference).
    
    Args:
        base: Shape to subtract from
        *tools: Shapes to subtract
    
    Returns:
        Result of subtracting tools from base
    
    Raises:
        GeometryError: If result is empty
    """
    if not tools:
        return base
    
    result = base
    for tool in tools:
        result = result.cut(tool)
    
    # Check if result is valid
    if result.val().Volume() <= 0:
        raise GeometryError("Boolean difference resulted in empty geometry")
    
    return result


def intersection(*shapes: cq.Workplane) -> cq.Workplane:
    """
    Return the common volume of shapes (boolean intersection).
    
    Args:
        *shapes: Two or more shapes to intersect
    
    Returns:
        Common volume of all shapes
    
    Raises:
        GeometryError: If no common volume exists
    """
    if len(shapes) < 2:
        raise ValueError("Intersection requires at least 2 shapes")
    
    result = shapes[0]
    for shape in shapes[1:]:
        result = result.intersect(shape)
    
    if result.val().Volume() <= 0:
        raise GeometryError("Shapes have no common volume")
    
    return result


def translate(
    shape: cq.Workplane,
    x: float = 0,
    y: float = 0,
    z: float = 0,
) -> cq.Workplane:
    """
    Move a shape by the specified offset.
    
    Args:
        shape: Shape to translate
        x: X offset in mm
        y: Y offset in mm
        z: Z offset in mm
    
    Returns:
        Translated shape
    """
    return shape.translate((x, y, z))


def rotate(
    shape: cq.Workplane,
    axis: tuple[float, float, float],
    angle: float,
) -> cq.Workplane:
    """
    Rotate a shape around an axis.
    
    Args:
        shape: Shape to rotate
        axis: Rotation axis as (x, y, z) tuple
        angle: Rotation angle in degrees
    
    Returns:
        Rotated shape
    """
    return shape.rotate((0, 0, 0), axis, angle)


def scale(shape: cq.Workplane, factor: float) -> cq.Workplane:
    """
    Uniformly scale a shape.
    
    Args:
        shape: Shape to scale
        factor: Scale factor (1.0 = no change)
    
    Returns:
        Scaled shape
    
    Raises:
        ValueError: If factor <= 0
    """
    if factor <= 0:
        raise ValueError("Scale factor must be positive")
    
    # CadQuery doesn't have direct scale, use OCP
    from OCP.gp import gp_Trsf, gp_Pnt
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    
    trsf = gp_Trsf()
    trsf.SetScale(gp_Pnt(0, 0, 0), factor)
    
    transformer = BRepBuilderAPI_Transform(shape.val().wrapped, trsf, True)
    return cq.Workplane(cq.Shape(transformer.Shape()))


def fillet(shape: cq.Workplane, radius: float) -> cq.Workplane:
    """
    Apply fillet (rounded edge) to all edges.
    
    Args:
        shape: Shape to fillet
        radius: Fillet radius in mm
    
    Returns:
        Filleted shape
    
    Raises:
        GeometryError: If fillet radius is too large
    """
    if radius <= 0:
        raise ValueError("Fillet radius must be positive")
    
    try:
        return shape.edges().fillet(radius)
    except Exception as e:
        raise GeometryError(f"Fillet failed (radius may be too large): {e}")


def chamfer(shape: cq.Workplane, distance: float) -> cq.Workplane:
    """
    Apply chamfer (beveled edge) to all edges.
    
    Args:
        shape: Shape to chamfer
        distance: Chamfer distance in mm
    
    Returns:
        Chamfered shape
    """
    if distance <= 0:
        raise ValueError("Chamfer distance must be positive")
    
    try:
        return shape.edges().chamfer(distance)
    except Exception as e:
        raise GeometryError(f"Chamfer failed: {e}")
```

### 4.5 GitHub Actions Test Workflow

```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  backend-tests:
    name: Backend Tests
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      
      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y libgl1-mesa-glx libglu1-mesa
      
      - name: Install Python dependencies
        working-directory: ./backend
        run: |
          pip install --upgrade pip
          pip install -e ".[dev]"
      
      - name: Run linting
        working-directory: ./backend
        run: |
          ruff check app tests
          mypy app --ignore-missing-imports
      
      - name: Run tests
        working-directory: ./backend
        env:
          DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379/0
          SECRET_KEY: test-secret-key
        run: |
          pytest --cov=app --cov-report=xml --cov-report=term-missing
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./backend/coverage.xml
          fail_ci_if_error: false

  lint:
    name: Lint
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install ruff
        run: pip install ruff
      
      - name: Run ruff
        working-directory: ./backend
        run: ruff check app tests --output-format=github
```

---

## 5. Code Review Checklist

Before approving PRs, verify:

### Functionality
- [ ] Code implements the acceptance criteria
- [ ] Edge cases are handled
- [ ] Error messages are helpful

### Code Quality
- [ ] Follows style guide (ruff passes)
- [ ] Type hints on all public functions
- [ ] No unused imports or variables
- [ ] Functions are single-purpose (< 30 lines)

### Testing
- [ ] Unit tests cover happy path
- [ ] Unit tests cover edge cases
- [ ] Tests are isolated (no external dependencies)
- [ ] Coverage ≥ 80% for new code

### Documentation
- [ ] Docstrings on all public functions
- [ ] Complex logic has comments
- [ ] README updated if needed

### Security
- [ ] No secrets in code
- [ ] Input validation on all user data
- [ ] No SQL injection vulnerabilities
- [ ] Proper error handling (no stack traces to users)

---

## 6. Risk Mitigation

### Risk: CadQuery Container Size
**Impact:** Large Docker images slow CI/CD  
**Mitigation:** 
- Multi-stage builds
- Use slim base images
- Cache pip dependencies in CI
- Consider separate CAD worker image

### Risk: CadQuery License (LGPL)
**Impact:** Legal compliance  
**Mitigation:**
- CadQuery is LGPL, which allows use in proprietary software
- Document dependency licenses in NOTICE file
- Don't modify CadQuery source directly

### Risk: OpenCASCADE Geometry Failures
**Impact:** Some operations may fail on complex geometry  
**Mitigation:**
- Comprehensive error handling
- Fallback strategies for common failures
- User-friendly error messages
- Logging for debugging

---

## 7. Sprint 1 Kickoff Checklist

### Pre-Sprint
- [x] Work breakdown complete
- [x] Technical specs documented
- [x] Development environment documented
- [ ] Team has reviewed this guide
- [ ] Questions addressed in sprint planning

### Day 1 Priorities
1. Create `pyproject.toml` (P0)
2. Create `backend/Dockerfile` (P0)
3. Create `backend/app/cad/__init__.py` and exceptions
4. Verify Docker Compose still works

### Definition of "Sprint 1 Complete"
- [ ] CadQuery container builds and runs
- [ ] All primitives generate correct geometry
- [ ] Boolean operations work
- [ ] STEP/STL export works
- [ ] GitHub Actions runs tests on PR
- [ ] 80% test coverage on new code

---

*Let's build something awesome! 🚀*
