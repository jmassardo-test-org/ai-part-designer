"""Compilation engine for CAD v2.

The engine orchestrates the compilation of schemas into Build123d geometry.
It provides a unified interface for compiling different types of designs.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.cad_v2.schemas.enclosure import EnclosureSpec

if TYPE_CHECKING:
    from app.cad_v2.compiler.enclosure import EnclosureCompiler


class ExportFormat(StrEnum):
    """Supported export formats."""

    STEP = "step"
    STL = "stl"
    # TODO: Add OBJ format support in future release


@dataclass
class CompilationResult:
    """Result of schema compilation.

    Contains the compiled geometry and any warnings or errors
    encountered during compilation.
    """

    success: bool
    """Whether compilation succeeded."""

    parts: dict[str, Any] = field(default_factory=dict)
    """Compiled parts (name -> Build123d Part object)."""

    warnings: list[str] = field(default_factory=list)
    """Non-fatal warnings encountered during compilation."""

    errors: list[str] = field(default_factory=list)
    """Errors encountered (only populated if success=False)."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata about the compilation."""

    def export(
        self,
        output_dir: Path | str,
        format: ExportFormat = ExportFormat.STEP,
        _combined: bool = False,
    ) -> list[Path]:
        """Export compiled parts to files.

        Args:
            output_dir: Directory to write files to.
            format: Export format (STEP or STL).
            _combined: If True, export all parts as single file.

        Returns:
            List of paths to exported files.
        """
        if not self.success:
            raise RuntimeError("Cannot export failed compilation")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        exported: list[Path] = []

        try:
            from build123d import export_step, export_stl
        except ImportError:
            # Fallback for testing without build123d
            for name in self.parts:
                ext = "step" if format == ExportFormat.STEP else "stl"
                path = output_dir / f"{name}.{ext}"
                path.write_text(f"# Placeholder {ext} for {name}")
                exported.append(path)
            return exported

        for name, part in self.parts.items():
            if format == ExportFormat.STEP:
                path = output_dir / f"{name}.step"
                export_step(part, str(path))
            elif format == ExportFormat.STL:
                path = output_dir / f"{name}.stl"
                export_stl(part, str(path))
            else:
                raise ValueError(f"Unsupported format: {format}")

            exported.append(path)

        return exported

    def get_part(self, name: str) -> Any:
        """Get a compiled part by name.

        Args:
            name: Part name.

        Returns:
            Build123d Part object.

        Raises:
            KeyError: If part not found.
        """
        if name not in self.parts:
            raise KeyError(f"Part '{name}' not found. Available: {list(self.parts.keys())}")
        return self.parts[name]


class CompilationError(Exception):
    """Error during schema compilation."""

    def __init__(self, message: str, details: list[str] | None = None) -> None:
        self.details = details or []
        super().__init__(message)


class CompilationEngine:
    """Main compilation engine.

    Orchestrates the compilation of schemas into Build123d geometry.
    Uses specialized compilers for different schema types.
    """

    def __init__(self) -> None:
        """Initialize compilation engine."""
        self._enclosure_compiler: EnclosureCompiler | None = None

    @property
    def enclosure_compiler(self) -> "EnclosureCompiler":
        """Get or create enclosure compiler."""
        if self._enclosure_compiler is None:
            from app.cad_v2.compiler.enclosure import EnclosureCompiler

            self._enclosure_compiler = EnclosureCompiler()
        return self._enclosure_compiler

    def compile_enclosure(self, spec: EnclosureSpec) -> CompilationResult:
        """Compile an enclosure specification.

        Args:
            spec: Enclosure specification to compile.

        Returns:
            CompilationResult with body and optionally lid parts.

        Raises:
            CompilationError: If compilation fails.
        """
        return self.enclosure_compiler.compile(spec)

    def validate_spec(self, spec: EnclosureSpec) -> list[str]:
        """Validate a specification without compiling.

        Args:
            spec: Specification to validate.

        Returns:
            List of validation issues (empty if valid).
        """
        issues: list[str] = []

        # Check minimum dimensions
        if spec.exterior.width_mm < 10:
            issues.append("Enclosure width too small (minimum 10mm)")
        if spec.exterior.depth_mm < 10:
            issues.append("Enclosure depth too small (minimum 10mm)")
        if spec.exterior.height_mm < 5:
            issues.append("Enclosure height too small (minimum 5mm)")

        # Check wall thickness ratio
        wall = spec.walls.thickness.mm
        if wall > spec.exterior.width_mm / 4:
            issues.append(
                f"Wall thickness ({wall}mm) is more than 25% of width - "
                "may be too thick for practical use"
            )

        # Check corner radius
        if spec.corner_radius:
            max_radius = min(spec.exterior.width_mm, spec.exterior.depth_mm) / 2
            if spec.corner_radius.mm > max_radius:
                issues.append(
                    f"Corner radius ({spec.corner_radius.mm}mm) exceeds maximum "
                    f"({max_radius}mm based on dimensions)"
                )

        return issues


# Lazy import to avoid circular dependency
