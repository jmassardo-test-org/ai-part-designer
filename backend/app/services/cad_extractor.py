"""
CAD Dimension Extractor

Extracts dimensions and features from STEP and STL files.
Uses Build123d/OCP for STEP files and numpy-stl for STL analysis.

Migrated from CadQuery to Build123d.
"""

import math
from pathlib import Path

import numpy as np

from app.schemas.component_specs import (
    BoundingBox,
    CADExtraction,
    Dimensions,
    LengthUnit,
    MountingHole,
)

# =============================================================================
# Configuration
# =============================================================================

# Hole detection parameters
MIN_HOLE_DIAMETER = 1.5  # mm - smaller holes likely not mounting
MAX_HOLE_DIAMETER = 12.0  # mm - larger holes unlikely mounting
CYLINDRICAL_FACE_TOLERANCE = 0.01  # tolerance for detecting cylinders

# STL mesh analysis
CURVATURE_THRESHOLD = 0.1  # threshold for detecting curved regions


# =============================================================================
# STEP File Extractor (using Build123d/OCP)
# =============================================================================


class STEPExtractor:
    """Extract dimensions and features from STEP files using Build123d."""

    def __init__(self):
        self._b3d_available = False
        try:
            import build123d as b3d
            from OCP.BRepAdaptor import BRepAdaptor_Surface
            from OCP.GeomAbs import GeomAbs_Cylinder

            self._b3d_available = True
            self._b3d = b3d
        except ImportError:
            print("Build123d not available. STEP extraction disabled.")

    def extract(self, step_path: Path) -> CADExtraction:
        """
        Extract dimensions and features from a STEP file.

        Returns:
            CADExtraction with bounding box and detected holes
        """
        if not self._b3d_available:
            return self._create_empty_result("Build123d not installed")

        try:
            # Import the STEP file using Build123d
            result = self._b3d.import_step(str(step_path))

            # Get bounding box
            bbox = result.bounding_box()

            bounding_box = BoundingBox(
                min_x=bbox.min.X,
                min_y=bbox.min.Y,
                min_z=bbox.min.Z,
                max_x=bbox.max.X,
                max_y=bbox.max.Y,
                max_z=bbox.max.Z,
                unit=LengthUnit.MM,
            )

            # Detect cylindrical holes
            holes = self._detect_holes(result)

            # Check if watertight (simplified check)
            is_watertight = True  # STEP files are usually solid

            # Estimate volume
            try:
                volume = result.volume
            except Exception:
                volume = None

            return CADExtraction(
                bounding_box=bounding_box,
                detected_holes=holes,
                is_watertight=is_watertight,
                estimated_volume=volume,
                extraction_quality="good",
            )

        except Exception as e:
            return self._create_empty_result(f"STEP extraction error: {e!s}")

    def _detect_holes(self, result) -> list[MountingHole]:
        """Detect cylindrical holes that could be mounting holes."""
        if not self._b3d_available:
            return []

        holes = []

        try:
            from OCP.BRepAdaptor import BRepAdaptor_Surface
            from OCP.GeomAbs import GeomAbs_Cylinder
            from OCP.TopAbs import TopAbs_FACE
            from OCP.TopExp import TopExp_Explorer

            # Get the underlying OCP shape
            shape = result.wrapped

            # Iterate through all faces
            explorer = TopExp_Explorer(shape, TopAbs_FACE)

            while explorer.More():
                face = explorer.Current()
                adaptor = BRepAdaptor_Surface(face)

                # Check if face is cylindrical
                if adaptor.GetType() == GeomAbs_Cylinder:
                    cylinder = adaptor.Cylinder()
                    radius = cylinder.Radius()
                    diameter = radius * 2

                    # Filter by reasonable mounting hole sizes
                    if MIN_HOLE_DIAMETER <= diameter <= MAX_HOLE_DIAMETER:
                        # Get cylinder axis position
                        axis = cylinder.Axis()
                        location = axis.Location()

                        # Check if it's an internal cylinder (hole, not boss)
                        # This is simplified - real check would analyze face orientation

                        holes.append(
                            MountingHole(
                                x=location.X(),
                                y=location.Y(),
                                diameter=diameter,
                                depth=None,  # Would need more analysis
                                confidence=0.8,
                            )
                        )

                explorer.Next()

            # Remove duplicates (holes often have multiple cylindrical faces)
            holes = self._deduplicate_holes(holes)

        except Exception as e:
            print(f"Hole detection error: {e}")

        return holes

    def _deduplicate_holes(
        self,
        holes: list[MountingHole],
        tolerance: float = 0.5,
    ) -> list[MountingHole]:
        """Remove duplicate holes that are at the same position."""
        unique = []

        for hole in holes:
            is_duplicate = False
            for existing in unique:
                dist = math.sqrt((hole.x - existing.x) ** 2 + (hole.y - existing.y) ** 2)
                if dist < tolerance and abs(hole.diameter - existing.diameter) < tolerance:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique.append(hole)

        return unique

    def _create_empty_result(self, warning: str) -> CADExtraction:
        """Create empty result with warning."""
        return CADExtraction(
            bounding_box=BoundingBox(
                min_x=0,
                min_y=0,
                min_z=0,
                max_x=0,
                max_y=0,
                max_z=0,
            ),
            detected_holes=[],
            extraction_quality="poor",
            warnings=[warning],
        )


# =============================================================================
# STL File Extractor
# =============================================================================


class STLExtractor:
    """Extract dimensions from STL mesh files."""

    def __init__(self):
        self._stl_available = False
        try:
            from stl import mesh

            self._stl_available = True
            self._mesh = mesh
        except ImportError:
            print("numpy-stl not available. STL extraction disabled.")

    def extract(self, stl_path: Path) -> CADExtraction:
        """
        Extract dimensions and analyze STL mesh.

        Returns:
            CADExtraction with bounding box and mesh statistics
        """
        if not self._stl_available:
            return self._create_empty_result("numpy-stl not installed")

        try:
            # Load STL file
            mesh_data = self._mesh.Mesh.from_file(str(stl_path))

            # Get bounding box from mesh vertices
            min_coords = mesh_data.vectors.min(axis=(0, 1))
            max_coords = mesh_data.vectors.max(axis=(0, 1))

            bounding_box = BoundingBox(
                min_x=float(min_coords[0]),
                min_y=float(min_coords[1]),
                min_z=float(min_coords[2]),
                max_x=float(max_coords[0]),
                max_y=float(max_coords[1]),
                max_z=float(max_coords[2]),
                unit=LengthUnit.MM,
            )

            # Mesh statistics
            vertex_count = len(mesh_data.vectors) * 3
            face_count = len(mesh_data.vectors)

            # Check if watertight (simplified - check if normals are consistent)
            is_watertight = self._check_watertight(mesh_data)

            # Estimate volume
            volume = self._calculate_volume(mesh_data)

            # Try to detect holes (more difficult in STL)
            holes = self._detect_holes_mesh(mesh_data)

            return CADExtraction(
                bounding_box=bounding_box,
                detected_holes=holes,
                vertex_count=vertex_count,
                face_count=face_count,
                is_watertight=is_watertight,
                estimated_volume=volume,
                extraction_quality="good" if is_watertight else "partial",
            )

        except Exception as e:
            return self._create_empty_result(f"STL extraction error: {e!s}")

    def _check_watertight(self, mesh_data) -> bool:
        """Check if mesh is watertight (simplified check)."""
        try:
            # A watertight mesh should have consistent normals
            # and the sum of signed volumes should match total volume
            # This is a simplified heuristic
            normals = mesh_data.normals

            # Check for zero-length normals (degenerate faces)
            lengths = np.linalg.norm(normals, axis=1)
            return not np.any(lengths < 0.001)
        except Exception:
            return False

    def _calculate_volume(self, mesh_data) -> float | None:
        """Calculate mesh volume using signed tetrahedron method."""
        try:
            # For each triangle, calculate signed volume of tetrahedron with origin
            volumes = []

            for triangle in mesh_data.vectors:
                v0, v1, v2 = triangle
                volume = np.dot(v0, np.cross(v1, v2)) / 6.0
                volumes.append(volume)

            total_volume = abs(sum(volumes))
            return float(total_volume)
        except Exception:
            return None

    def _detect_holes_mesh(self, mesh_data) -> list[MountingHole]:
        """
        Attempt to detect holes in STL mesh using curvature analysis.

        This is more difficult than STEP analysis and less accurate.
        """
        holes = []

        try:
            # Analyze vertex curvature to find circular regions
            # This is a simplified approach - full implementation would use
            # more sophisticated mesh analysis

            # For now, we'll return empty list and rely on datasheet extraction
            # or manual input for STL files
            pass

        except Exception as e:
            print(f"STL hole detection error: {e}")

        return holes

    def _create_empty_result(self, warning: str) -> CADExtraction:
        """Create empty result with warning."""
        return CADExtraction(
            bounding_box=BoundingBox(
                min_x=0,
                min_y=0,
                min_z=0,
                max_x=0,
                max_y=0,
                max_z=0,
            ),
            detected_holes=[],
            extraction_quality="poor",
            warnings=[warning],
        )


# =============================================================================
# Unified CAD Extractor
# =============================================================================


class CADDimensionExtractor:
    """Unified extractor for STEP and STL files."""

    def __init__(self):
        self.step_extractor = STEPExtractor()
        self.stl_extractor = STLExtractor()

    def extract(self, cad_path: Path) -> CADExtraction:
        """
        Extract dimensions from a CAD file.

        Automatically detects file type and uses appropriate extractor.
        """
        suffix = cad_path.suffix.lower()

        if suffix in {".step", ".stp"}:
            return self.step_extractor.extract(cad_path)
        if suffix == ".stl":
            return self.stl_extractor.extract(cad_path)
        if suffix in {".iges", ".igs"}:
            # IGES support could be added
            return CADExtraction(
                bounding_box=BoundingBox(
                    min_x=0,
                    min_y=0,
                    min_z=0,
                    max_x=0,
                    max_y=0,
                    max_z=0,
                ),
                extraction_quality="poor",
                warnings=["IGES format not yet supported"],
            )
        return CADExtraction(
            bounding_box=BoundingBox(
                min_x=0,
                min_y=0,
                min_z=0,
                max_x=0,
                max_y=0,
                max_z=0,
            ),
            extraction_quality="poor",
            warnings=[f"Unknown CAD format: {suffix}"],
        )

    def extract_from_step(self, step_path: Path) -> CADExtraction:
        """Extract from STEP file specifically."""
        return self.step_extractor.extract(step_path)

    def extract_from_stl(self, stl_path: Path) -> CADExtraction:
        """Extract from STL file specifically."""
        return self.stl_extractor.extract(stl_path)

    def get_dimensions(self, cad_path: Path) -> Dimensions:
        """Get just the dimensions from a CAD file."""
        result = self.extract(cad_path)
        bbox = result.bounding_box

        return Dimensions(
            length=bbox.width,
            width=bbox.depth,
            height=bbox.height,
            unit=bbox.unit,
        )


# =============================================================================
# Singleton Instance
# =============================================================================

cad_extractor = CADDimensionExtractor()
