# ADR-005: CAD/3D Processing Library Selection

## Status
Proposed

## Context
We need to select a CAD processing library for generating and manipulating 3D geometry. This is a **critical** decision as it forms the core of our value proposition. Requirements include:
- Generate parametric 3D models programmatically
- Export to STEP, STL, OBJ, and 3MF formats
- Import and parse existing STEP files
- Boolean operations (union, difference, intersection)
- Fillet, chamfer, and other common operations
- Geometry validation for 3D printability
- Python integration for our backend

## Decision
We will use **CadQuery 2.x** as our primary CAD library, with **OCP (OpenCASCADE Python)** as the underlying kernel.

Supporting technology choices:
- **Primary Library**: CadQuery 2.x
- **CAD Kernel**: OpenCASCADE via OCP (python-occ successor)
- **Mesh Operations**: trimesh (for STL operations)
- **Visualization**: vtk or pythreejs for server-side rendering
- **Validation**: Custom validators using CadQuery/OCP primitives

## Consequences

### Positive
- **Pythonic API**: CadQuery provides a fluent, readable API for CAD operations
- **Full STEP support**: OpenCASCADE is the gold standard for STEP import/export
- **Parametric design**: Excellent support for parametric, constraint-based modeling
- **Boolean operations**: Robust CSG operations for combining shapes
- **Active community**: Growing ecosystem, regular updates
- **Commercial quality**: OpenCASCADE kernel used in FreeCAD, commercial CAD

### Negative
- **Installation complexity**: OpenCASCADE has complex dependencies (mitigated by conda/docker)
- **Learning curve**: CAD concepts required for complex operations
- **Memory usage**: OpenCASCADE can be memory-intensive for complex models
- **Limited documentation**: Less documentation than commercial CAD APIs

### Risk Mitigation
- Use Docker containers with pre-built dependencies
- Create abstraction layer to isolate CadQuery specifics
- Implement geometry complexity limits
- Thorough testing with various STEP files

## Options Considered

| Option | Pros | Cons | Score |
|--------|------|------|-------|
| **CadQuery + OCP** | Pythonic, full STEP support, parametric | Complex setup | ⭐⭐⭐⭐⭐ |
| Build123d | Modern API, CadQuery-inspired | Newer, less proven | ⭐⭐⭐⭐ |
| pythonocc-core | Direct OpenCASCADE access | Verbose API | ⭐⭐⭐⭐ |
| FreeCAD Python | Full CAD suite | Heavy, UI-focused | ⭐⭐⭐ |
| OpenSCAD + subprocess | Simple CSG | Limited operations, no STEP | ⭐⭐ |
| Onshape API | Cloud CAD | Vendor lock-in, cost, latency | ⭐⭐⭐ |

## Technical Details

### Installation via Conda
```yaml
# environment.yml
name: ai-part-designer
channels:
  - conda-forge
dependencies:
  - python=3.11
  - cadquery=2.4
  - ocp=7.7
  - vtk
  - trimesh
  - numpy
```

### Docker Setup
```dockerfile
FROM continuumio/miniconda3:latest

# Install CadQuery with dependencies
RUN conda install -c conda-forge cadquery=2.4 ocp=7.7 vtk -y

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . /app
WORKDIR /app
```

### CAD Service Architecture
```python
# app/services/cad/service.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
import cadquery as cq

@dataclass
class CADResult:
    geometry: cq.Workplane
    metadata: dict
    warnings: list[str]

class CADService:
    """Main CAD service for geometry operations."""
    
    def generate_from_template(
        self, 
        template_name: str, 
        parameters: dict
    ) -> CADResult:
        """Generate geometry from a template with parameters."""
        template = self.get_template(template_name)
        return template.generate(parameters)
    
    def generate_from_description(
        self, 
        parsed_description: dict
    ) -> CADResult:
        """Generate geometry from AI-parsed description."""
        # Map description to CAD operations
        operations = self.map_to_operations(parsed_description)
        return self.execute_operations(operations)
    
    def import_step(self, file_path: str) -> CADResult:
        """Import a STEP file."""
        result = cq.importers.importStep(file_path)
        return CADResult(
            geometry=result,
            metadata=self.extract_metadata(result),
            warnings=[]
        )
    
    def export(
        self, 
        geometry: cq.Workplane, 
        format: str,
        options: dict = None
    ) -> bytes:
        """Export geometry to specified format."""
        if format == "step":
            return self._export_step(geometry, options)
        elif format == "stl":
            return self._export_stl(geometry, options)
        elif format == "obj":
            return self._export_obj(geometry, options)
        else:
            raise ValueError(f"Unsupported format: {format}")
```

### Template Example: Project Box
```python
# app/services/cad/templates/project_box.py
import cadquery as cq
from ..base import Template, Parameter

class ProjectBoxTemplate(Template):
    name = "project_box"
    description = "Rectangular box with optional lid and mounting features"
    
    parameters = [
        Parameter("length", float, default=100, min=20, max=500, unit="mm"),
        Parameter("width", float, default=60, min=20, max=500, unit="mm"),
        Parameter("height", float, default=40, min=10, max=300, unit="mm"),
        Parameter("wall_thickness", float, default=2, min=0.8, max=10, unit="mm"),
        Parameter("corner_radius", float, default=3, min=0, max=20, unit="mm"),
        Parameter("include_lid", bool, default=True),
        Parameter("screw_posts", bool, default=True),
        Parameter("ventilation_slots", bool, default=False),
    ]
    
    def generate(self, params: dict) -> cq.Workplane:
        p = self.validate_params(params)
        
        # Create outer shell
        outer = (
            cq.Workplane("XY")
            .box(p.length, p.width, p.height)
            .edges("|Z")
            .fillet(p.corner_radius)
        )
        
        # Create inner cavity
        inner = (
            cq.Workplane("XY")
            .workplane(offset=p.wall_thickness)
            .box(
                p.length - 2 * p.wall_thickness,
                p.width - 2 * p.wall_thickness,
                p.height - p.wall_thickness
            )
            .edges("|Z")
            .fillet(max(0, p.corner_radius - p.wall_thickness))
        )
        
        # Boolean difference
        box = outer.cut(inner)
        
        # Add screw posts if requested
        if p.screw_posts:
            box = self._add_screw_posts(box, p)
        
        # Add ventilation if requested
        if p.ventilation_slots:
            box = self._add_ventilation(box, p)
        
        return box
    
    def _add_screw_posts(self, box, params):
        # Add cylindrical posts in corners
        post_diameter = 6
        post_height = params.height - params.wall_thickness - 2
        inset = params.wall_thickness + post_diameter / 2 + 2
        
        positions = [
            (params.length/2 - inset, params.width/2 - inset),
            (params.length/2 - inset, -params.width/2 + inset),
            (-params.length/2 + inset, params.width/2 - inset),
            (-params.length/2 + inset, -params.width/2 + inset),
        ]
        
        for x, y in positions:
            post = (
                cq.Workplane("XY")
                .workplane(offset=params.wall_thickness)
                .center(x, y)
                .circle(post_diameter / 2)
                .extrude(post_height)
                .faces(">Z")
                .hole(2.5, depth=post_height - 2)  # M3 hole
            )
            box = box.union(post)
        
        return box
```

### Geometry Validation
```python
# app/services/cad/validation.py
from dataclasses import dataclass

@dataclass
class ValidationResult:
    is_valid: bool
    is_printable: bool
    warnings: list[str]
    errors: list[str]
    metrics: dict

def validate_geometry(geometry: cq.Workplane) -> ValidationResult:
    """Validate geometry for 3D printability."""
    warnings = []
    errors = []
    
    # Check if manifold (watertight)
    if not is_manifold(geometry):
        errors.append("Geometry is not manifold (not watertight)")
    
    # Check minimum wall thickness
    min_thickness = measure_min_wall_thickness(geometry)
    if min_thickness < 0.8:
        warnings.append(f"Minimum wall thickness {min_thickness:.1f}mm may be too thin")
    
    # Check for overhangs
    max_overhang = measure_max_overhang(geometry)
    if max_overhang > 45:
        warnings.append(f"Overhang of {max_overhang:.0f}° may require supports")
    
    # Calculate metrics
    metrics = {
        "volume_mm3": calculate_volume(geometry),
        "surface_area_mm2": calculate_surface_area(geometry),
        "bounding_box": get_bounding_box(geometry),
        "min_wall_thickness": min_thickness,
        "max_overhang": max_overhang,
    }
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        is_printable=len(errors) == 0 and max_overhang <= 60,
        warnings=warnings,
        errors=errors,
        metrics=metrics,
    )
```

## POC Validation Tasks
Before finalizing this decision, complete the following POC:

- [ ] Install CadQuery in Docker container
- [ ] Generate simple box with parameters
- [ ] Import sample STEP file
- [ ] Export to STL with quality options
- [ ] Perform boolean operations
- [ ] Measure performance for typical operations
- [ ] Validate memory usage

## References
- [CadQuery Documentation](https://cadquery.readthedocs.io/)
- [CadQuery GitHub](https://github.com/CadQuery/cadquery)
- [OpenCASCADE](https://dev.opencascade.org/)
- [Build123d](https://build123d.readthedocs.io/) (alternative to evaluate)
