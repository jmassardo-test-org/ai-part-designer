# CAD v1 to v2 Migration Guide

This document provides guidance for migrating from the legacy CAD system (`app.cad`) to the new declarative schema system (`app.cad_v2`).

## Overview

The CAD v2 system replaces the procedural CAD generation approach with a declarative schema-based approach. Instead of writing imperative code to generate geometry, you define what you want in a structured schema, and the compiler generates the geometry.

### Key Differences

| Aspect | v1 (Legacy) | v2 (New) |
|--------|-------------|----------|
| Approach | Procedural (CadQuery scripts) | Declarative (JSON schemas) |
| CAD Engine | CadQuery | Build123d |
| AI Integration | Code generation | Schema generation |
| Validation | Runtime | Schema validation |
| Testability | Integration tests | Unit tests on schemas |
| Extensibility | Template functions | Component library |

## Migration Path

### Phase 1: Parallel Operation (Current)

Both systems run side-by-side:
- v1 API: `/api/v1/generate/` - Uses legacy `app.cad`
- v2 API: `/api/v2/generate/` - Uses new `app.cad_v2`

### Phase 2: Gradual Migration

Enable v2 for specific use cases via feature flags:

```python
from app.core.config import get_settings

settings = get_settings()
if settings.CAD_V2_ENABLED and design_type == "enclosure":
    # Use v2 pipeline
    from app.cad_v2.ai import SchemaGenerator
    result = await SchemaGenerator().generate(description)
else:
    # Fall back to v1
    from app.ai.generator import generate_from_description
    result = await generate_from_description(description)
```

### Phase 3: Complete Migration

Once v2 is validated:
1. Update all v1 endpoints to use v2 internally
2. Add deprecation headers to v1 API responses
3. Eventually remove v1 endpoints

## API Migration

### Generating CAD from Natural Language

**v1 (Legacy):**
```python
from app.ai.generator import generate_from_description

result = await generate_from_description(
    "Create a box 100mm x 50mm x 30mm"
)
# result.cad_data contains CadQuery Workplane
```

**v2 (New):**
```python
from app.cad_v2.ai import SchemaGenerator
from app.cad_v2.compiler import CompilationEngine

# Generate schema from description
generator = SchemaGenerator()
result = await generator.generate(
    "Create a case for Raspberry Pi 5 with USB ports"
)

if result.success:
    # Compile to geometry
    engine = CompilationEngine()
    compilation = engine.compile_enclosure(result.spec)
    
    # Export
    paths = compilation.export("/output", format="step")
```

### Creating Enclosures Programmatically

**v1 (Legacy):**
```python
from app.cad.enclosure import create_enclosure

enclosure = create_enclosure(
    width=100,
    height=50,
    depth=80,
    wall_thickness=2.5,
    lid_type="snap_fit",
)
```

**v2 (New):**
```python
from app.cad_v2.schemas.base import BoundingBox, Dimension
from app.cad_v2.schemas.enclosure import EnclosureSpec, LidSpec, LidType, WallSpec
from app.cad_v2.compiler import CompilationEngine

spec = EnclosureSpec(
    exterior=BoundingBox(
        width=Dimension(value=100),
        depth=Dimension(value=80),
        height=Dimension(value=50),
    ),
    walls=WallSpec(thickness=Dimension(value=2.5)),
    lid=LidSpec(type=LidType.SNAP_FIT),
)

engine = CompilationEngine()
result = engine.compile_enclosure(spec)
```

### Using Component Library

**v1 (Legacy):**
```python
# No component library - dimensions hardcoded or fetched externally
PI5_WIDTH = 85
PI5_DEPTH = 56
PI5_HEIGHT = 17
```

**v2 (New):**
```python
from app.cad_v2.components import get_registry

registry = get_registry()

# Lookup by ID
pi5 = registry.lookup("raspberry-pi-5")
print(pi5.dimensions.to_tuple_mm())  # (85.0, 56.0, 17.0)

# Fuzzy search
matches = registry.search("pi 5")
```

### Export Formats

**v1 (Legacy):**
```python
from app.cad.export import export_step, export_stl, ExportQuality

export_step(workplane, "/output/part.step")
export_stl(workplane, "/output/part.stl", quality=ExportQuality.HIGH)
```

**v2 (New):**
```python
from app.cad_v2.compiler.export import export_part, ExportFormat

export_part(part, "/output/part.step", format=ExportFormat.STEP)
export_part(part, "/output/part.stl", format=ExportFormat.STL)

# Or via CompilationResult
result.export("/output", format=ExportFormat.STEP)
```

## REST API Migration

### Generate Endpoint

**v1:** `POST /api/v1/generate/`
```json
{
  "description": "Create a box 100mm x 50mm x 30mm",
  "export_step": true,
  "export_stl": true
}
```

**v2:** `POST /api/v2/generate/`
```json
{
  "description": "Create a case for Raspberry Pi 5",
  "export_format": "step"
}
```

Response includes the generated schema for transparency:
```json
{
  "job_id": "...",
  "success": true,
  "schema_json": {
    "exterior": {"width": {"value": 95}, ...},
    ...
  },
  "parts": ["body", "lid"],
  "downloads": {...}
}
```

### Component Lookup

**v1:** No equivalent

**v2:** `GET /api/v2/components/raspberry-pi-5`
```json
{
  "id": "raspberry-pi-5",
  "name": "Raspberry Pi 5",
  "dimensions_mm": [85, 56, 17],
  "mounting_holes": [...],
  "ports": [...]
}
```

## Schema Reference

The v2 system uses Pydantic models for validation. Key schemas:

- `EnclosureSpec` - Top-level enclosure definition
- `BoundingBox` - 3D dimensions
- `WallSpec` - Wall thickness configuration
- `LidSpec` - Lid attachment type
- `ComponentMount` - Component positioning
- `PortCutout`, `ButtonCutout`, `DisplayCutout` - Feature definitions

See `backend/app/cad_v2/schemas/` for complete definitions.

## Deprecation Timeline

| Version | Status |
|---------|--------|
| v2.0 | v1 deprecated, v2 available |
| v2.5 | v1 emits warnings, v2 default |
| v3.0 | v1 removed |

## Support

For migration assistance:
- Review ADR-016: `docs/adrs/adr-016-declarative-cad-schema.md`
- Check component library scope: `docs/cad-v2-component-library-scope.md`
- File issues in the repository
