# ADR-016: Declarative CAD Schema Architecture

## Status
Accepted

## Context

The current CAD generation system has fundamental architectural issues that limit its effectiveness:

### Current Problems

1. **Template-Based Generation (1440+ lines in `templates.py`)**
   - Requires manual coding for each new shape type
   - Tight coupling between shape definitions and generation logic
   - Difficult to extend without modifying core code

2. **AI Code Generation Approach (`codegen.py` - 945 lines)**
   - LLM generates raw CadQuery Python code
   - High failure rate due to syntax errors and invalid API calls
   - No validation until runtime execution
   - Difficult to debug and correct

3. **Shape-Specific Parsing (`parser.py` - 482 lines)**
   - `ShapeType` enum-based system
   - Each shape requires hardcoded parsing logic
   - Cannot handle novel or composite shapes

4. **Fragmented Enclosure System (`enclosure/` module)**
   - Separate templates, cutouts, and standoffs modules
   - Duplicates logic from main CAD module
   - Difficult to maintain consistency

### Requirements

- Support complex enclosures with multiple components (Raspberry Pi, LCDs, buttons)
- Generate manufacturing-ready STEP files
- High reliability (validated before CAD execution)
- Extensible without code changes for common components
- Clear error messages for invalid designs

## Decision

We will implement a **Declarative Schema + Build123d** architecture with the following layers:

### 1. Declarative Schema Layer (Pydantic Models)

The AI will output validated JSON conforming to Pydantic schemas, not raw code:

```python
class EnclosureSpec(BaseModel):
    exterior: BoundingBox
    wall_thickness: Dimension
    corner_radius: Dimension | None = None
    lid: LidSpec | None = None
    components: list[ComponentMount] = []
    features: list[Feature] = []
```

**Benefits:**
- Schema validation before CAD execution
- Clear, semantic error messages
- Type-safe throughout the pipeline
- Easy to version and evolve

### 2. Component Library

A registry of known components with exact dimensions:

```python
RASPBERRY_PI_5 = ComponentDefinition(
    id="raspberry-pi-5",
    aliases=["rpi5", "pi 5", "raspberry pi 5"],
    dimensions=BoundingBox(width=85, depth=56, height=17),
    mounting_holes=[...],
    ports=[...],
)
```

**Benefits:**
- Accurate dimensions without AI hallucination
- Fuzzy matching for natural language references
- Extensible by adding definitions (no code changes)

### 3. Deterministic Compiler

A compiler that transforms validated schemas into Build123d geometry:

```python
class EnclosureCompiler:
    def compile(self, spec: EnclosureSpec) -> Part:
        # Deterministic transformation
        # No AI involved at this stage
```

**Benefits:**
- Reproducible outputs for same input
- Testable in isolation
- Clear error attribution (schema vs compilation)

### 4. Build123d (Replaces CadQuery)

Build123d is the successor to CadQuery with improvements:

- Cleaner Python API with fluent interface
- Better STEP export for manufacturing
- BREP-based solid modeling
- Apache 2.0 license
- Active development by original CadQuery team

## Consequences

### Positive

1. **Reliability**: Schema validation catches errors before CAD execution
2. **Debuggability**: Clear separation between intent extraction, schema generation, and geometry compilation
3. **Extensibility**: Add components to library without code changes
4. **Testability**: Each layer can be tested independently
5. **Manufacturing Ready**: Build123d produces high-quality STEP files
6. **Reduced AI Risk**: AI only generates structured data, not executable code

### Negative

1. **Initial Development Effort**: 17-22 days to implement full system
2. **Schema Evolution**: Need versioning strategy as schemas evolve
3. **Component Library Maintenance**: Must keep dimensions accurate
4. **Learning Curve**: Team needs to learn Build123d API

### Neutral

1. **Flexibility Trade-off**: Less flexible than raw code generation, but more reliable
2. **Two-Stage AI**: First extract intent, then generate schema (may need iteration)

## Options Considered

### Option 1: Fix Current System
- **Rejected**: Fundamental architecture issues; would require complete rewrite anyway

### Option 2: OpenSCAD via LLM
- **Rejected**: No native STEP export (critical for manufacturing); CSG-based has limitations

### Option 3: Declarative Schema + CadQuery
- **Partially Accepted**: Good approach, but Build123d is superior successor

### Option 4: Declarative Schema + Build123d ✓
- **Accepted**: Best balance of reliability, manufacturability, and extensibility

## Implementation Plan

See [sprint-planning-cad-v2-refactor.md](../sprint-planning-cad-v2-refactor.md) for detailed implementation plan.

### Phase Summary
| Phase | Description | Duration |
|-------|-------------|----------|
| 0 | Documentation & ADR | 1 day |
| 1 | Declarative Schema Foundation | 3-4 days |
| 2 | Component Library | 2-3 days |
| 3 | Schema → Build123d Compiler | 4-5 days |
| 4 | AI Intent → Schema Pipeline | 3-4 days |
| 5 | New API Endpoints | 2-3 days |
| 6 | Remove Old System | 2 days |

## References

- [Build123d Documentation](https://build123d.readthedocs.io/)
- [Build123d GitHub](https://github.com/gumyr/build123d)
- [Pydantic V2 Documentation](https://docs.pydantic.dev/latest/)
- [Sprint Planning Document](../sprint-planning-cad-v2-refactor.md)
- [ADR-005: CAD Processing Library](adr-005-cad-processing-library.md) (Superseded for v2)
- [ADR-006: AI/ML Integration](adr-006-ai-ml-integration.md) (Extended by this ADR)
