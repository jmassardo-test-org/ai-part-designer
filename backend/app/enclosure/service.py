"""
Enclosure Generation Service

Core service for generating enclosures around reference components
using AI-powered Build123d code generation.

Migrated from CadQuery to Build123d.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field

import build123d as b3d
from build123d import (
    Align,
    Axis,
    Box,
    BuildPart,
    Cylinder,
    Location,
    Mode,
    Part,
)

from app.ai.exceptions import AIGenerationError
from app.ai.providers import get_ai_provider
from app.cad.exceptions import CADError
from app.cad.export import export_step as app_export_step
from app.cad.export import export_stl as app_export_stl
from app.enclosure.cutouts import CutoutGenerator
from app.enclosure.prompts import (
    ComponentData,
    EnclosurePromptBuilder,
)
from app.enclosure.schemas import (
    ComponentPosition,
    Cutout,
    EnclosureOptions,
    EnclosureResult,
    EnclosureStyle,
    SpatialLayout,
    Standoff,
)
from app.enclosure.standoffs import StandoffGenerator
from app.schemas.component_specs import (
    Dimensions,
    LengthUnit,
    Position3D,
)

logger = logging.getLogger(__name__)


@dataclass
class GeneratedEnclosure:
    """Internal result of enclosure code generation."""

    base: Part
    lid: Part | None
    build123d_code: str
    standoffs: list[Standoff]
    cutouts: list[Cutout]
    warnings: list[str] = field(default_factory=list)


class EnclosureGenerationService:
    """
    Service for generating enclosures around components.

    Uses AI to generate Build123d code based on component specifications,
    then executes the code to produce the CAD geometry.
    """

    def __init__(self) -> None:
        self.standoff_generator = StandoffGenerator()
        self.cutout_generator = CutoutGenerator()

    async def generate_enclosure(
        self,
        components: list[ComponentData],
        style: EnclosureStyle,
        options: EnclosureOptions,
        layout: SpatialLayout | None = None,
    ) -> EnclosureResult:
        """
        Generate an enclosure for the given components.

        Args:
            components: List of components with specifications
            style: Enclosure style parameters
            options: Generation options
            layout: Optional spatial layout (auto-calculated if None)

        Returns:
            EnclosureResult with generated geometry and file paths

        Raises:
            AIGenerationError: If AI code generation fails
            CADError: If Build123d execution fails
        """
        start_time = time.time()
        job_id = uuid.uuid4()
        warnings: list[str] = []

        logger.info(f"Starting enclosure generation job {job_id} with {len(components)} components")

        try:
            # Step 1: Calculate internal dimensions
            internal_dims = self._calculate_internal_dimensions(components, options, layout)
            logger.debug(f"Internal dimensions: {internal_dims}")

            # Step 2: Auto-layout if not provided
            if layout is None or layout.auto_arrange:
                layout = self._auto_arrange_components(components, internal_dims, options)
                logger.debug("Auto-arranged components")

            # Step 3: Calculate external dimensions
            external_dims = self._calculate_external_dimensions(internal_dims, style)

            # Step 4: Generate standoff positions
            standoffs = self._generate_standoffs(components, layout, options)
            logger.debug(f"Generated {len(standoffs)} standoffs")

            # Step 5: Generate cutout positions
            cutouts = self._generate_cutouts(components, layout, style, options)
            logger.debug(f"Generated {len(cutouts)} cutouts")

            # Step 6: Build AI prompt
            prompt_builder = EnclosurePromptBuilder(
                components=components,
                style=style,
                options=options,
                layout=layout,
            )
            messages = prompt_builder.build_messages()

            # Step 7: Generate Build123d code via AI
            build123d_code = await self._generate_code(messages)
            logger.debug("Generated Build123d code")

            # Step 8: Execute Build123d code
            base, lid = self._execute_code(build123d_code)
            logger.debug("Executed Build123d code successfully")

            # Step 9: Export to files
            app_export_step(base)
            app_export_stl(base)

            if lid is not None and options.generate_lid_separately:
                app_export_step(lid)
                app_export_stl(lid)

            # Step 10: Build result
            generation_time = (time.time() - start_time) * 1000

            result = EnclosureResult(
                job_id=job_id,
                external_dimensions=external_dims,
                internal_dimensions=internal_dims,
                standoffs=standoffs,
                cutouts=cutouts,
                component_positions=[
                    ComponentPosition(
                        component_id=uuid.UUID(c.id) if c.id else uuid.uuid4(),
                        position=c.position or Position3D(x=0, y=0, z=options.pcb_standoff_height),
                    )
                    for c in components
                ],
                cadquery_code=build123d_code,  # Keep field name for compatibility
                generation_time_ms=generation_time,
                warnings=warnings,
            )

            logger.info(f"Enclosure generation completed in {generation_time:.0f}ms")

            return result

        except Exception as e:
            logger.error(f"Enclosure generation failed: {e}")
            raise

    def _calculate_internal_dimensions(
        self,
        components: list[ComponentData],
        options: EnclosureOptions,
        layout: SpatialLayout | None,
    ) -> Dimensions:
        """Calculate required internal dimensions from components."""
        if layout and layout.internal_dimensions:
            return layout.internal_dimensions

        clearance = options.component_clearance
        standoff_height = options.pcb_standoff_height
        lid_clearance = options.lid_clearance

        max_x = 0.0
        max_y = 0.0
        max_z = 0.0

        for comp in components:
            dims = comp.dimensions.to_mm()
            pos = comp.position or Position3D(x=clearance, y=clearance, z=standoff_height)

            # Component bounding box
            comp_max_x = pos.x + dims.length + clearance
            comp_max_y = pos.y + dims.width + clearance
            comp_max_z = pos.z + dims.height

            # Account for clearance zones
            for zone in comp.clearance_zones:
                zone_top = zone.bounds.max_z + zone.minimum_clearance
                comp_max_z = max(comp_max_z, zone_top)

            max_x = max(max_x, comp_max_x)
            max_y = max(max_y, comp_max_y)
            max_z = max(max_z, comp_max_z)

        # Add clearance on minimum side
        max_x += clearance
        max_y += clearance
        max_z += lid_clearance

        return Dimensions(
            length=round(max_x, 1),
            width=round(max_y, 1),
            height=round(max_z, 1),
            unit=LengthUnit.MM,
        )

    def _calculate_external_dimensions(
        self,
        internal: Dimensions,
        style: EnclosureStyle,
    ) -> Dimensions:
        """Calculate external dimensions from internal + wall thickness."""
        return Dimensions(
            length=internal.length + 2 * style.wall_thickness,
            width=internal.width + 2 * style.wall_thickness,
            height=internal.height + style.floor_thickness + style.lid_thickness,
            unit=LengthUnit.MM,
        )

    def _auto_arrange_components(
        self,
        components: list[ComponentData],
        internal_dims: Dimensions,
        options: EnclosureOptions,
    ) -> SpatialLayout:
        """
        Auto-arrange components in the enclosure.

        Simple bin-packing algorithm for now.
        """
        positions: list[ComponentPosition] = []
        clearance = options.component_clearance
        standoff_height = options.pcb_standoff_height

        # Simple row-based packing
        current_x = clearance
        current_y = clearance
        row_height = 0.0

        for comp in components:
            dims = comp.dimensions.to_mm()

            # Check if fits in current row
            if current_x + dims.length + clearance > internal_dims.length:
                # Move to next row
                current_x = clearance
                current_y += row_height + clearance
                row_height = 0.0

            # Place component
            pos = Position3D(
                x=current_x,
                y=current_y,
                z=standoff_height,
            )
            comp.position = pos

            positions.append(
                ComponentPosition(
                    component_id=uuid.UUID(comp.id) if comp.id else uuid.uuid4(),
                    position=pos,
                )
            )

            # Update position
            current_x += dims.length + clearance
            row_height = max(row_height, dims.width)

        return SpatialLayout(
            components=positions,
            auto_arrange=True,
        )

    def _generate_standoffs(
        self,
        components: list[ComponentData],
        _layout: SpatialLayout,
        options: EnclosureOptions,
    ) -> list[Standoff]:
        """Generate standoff specifications for all components."""
        standoffs: list[Standoff] = []

        for comp in components:
            comp_pos = comp.position or Position3D(x=0, y=0, z=options.pcb_standoff_height)

            for hole in comp.mounting_holes:
                standoff = self.standoff_generator.calculate_standoff(
                    hole=hole,
                    component_position=comp_pos,
                    standoff_height=options.pcb_standoff_height,
                    component_id=uuid.UUID(comp.id) if comp.id else None,
                )
                standoffs.append(standoff)

        return standoffs

    def _generate_cutouts(
        self,
        components: list[ComponentData],
        _layout: SpatialLayout,
        style: EnclosureStyle,
        options: EnclosureOptions,
    ) -> list[Cutout]:
        """Generate cutout specifications for all connectors."""
        if not options.auto_cutouts:
            return []

        cutouts: list[Cutout] = []

        for comp in components:
            comp_pos = comp.position or Position3D(x=0, y=0, z=0)

            for conn in comp.connectors:
                cutout = self.cutout_generator.calculate_cutout(
                    connector=conn,
                    component_position=comp_pos,
                    wall_thickness=style.wall_thickness,
                    tolerance=options.cutout_tolerance,
                    component_id=uuid.UUID(comp.id) if comp.id else None,
                )
                cutouts.append(cutout)

        return cutouts

    async def _generate_code(
        self,
        messages: list[dict[str, str]],
    ) -> str:
        """Generate Build123d code using AI."""
        provider = get_ai_provider()

        try:
            response = await provider.complete(
                messages=messages,
                max_tokens=4000,
                temperature=0.2,
            )

            code = response.strip()

            # Clean up code if wrapped in markdown
            if code.startswith("```python"):
                code = code[9:]
            if code.startswith("```"):
                code = code[3:]
            if code.endswith("```"):
                code = code[:-3]

            return code.strip()

        except Exception as e:
            raise AIGenerationError(f"Failed to generate enclosure code: {e}")

    def _execute_code(
        self,
        code: str,
    ) -> tuple[Part, Part | None]:
        """
        Execute generated Build123d code.

        Returns:
            Tuple of (base, lid) Parts
        """
        # Create execution namespace with Build123d
        namespace = {
            "b3d": b3d,
            "Part": Part,
            "Box": Box,
            "Cylinder": Cylinder,
            "BuildPart": BuildPart,
            "Location": Location,
            "Axis": Axis,
            "Mode": Mode,
            "Align": Align,
            "__builtins__": {
                "range": range,
                "len": len,
                "int": int,
                "float": float,
                "round": round,
                "min": min,
                "max": max,
                "abs": abs,
                "list": list,
                "tuple": tuple,
                "dict": dict,
                "True": True,
                "False": False,
                "None": None,
            },
        }

        try:
            # Execute the generated code
            exec(code, namespace)  # nosec B102 - intentional exec for AI-generated enclosure code in sandboxed namespace

            # Call the generate_enclosure function
            if "generate_enclosure" not in namespace:
                raise CADError("Generated code must define 'generate_enclosure()' function")

            result = namespace["generate_enclosure"]()

            # Handle different return types
            if isinstance(result, tuple) and len(result) == 2:
                base, lid = result
            elif isinstance(result, Part):
                base = result
                lid = None
            else:
                raise CADError(
                    f"generate_enclosure() must return (base, lid) tuple "
                    f"or single Part, got {type(result)}"
                )

            return base, lid

        except SyntaxError as e:
            raise CADError(f"Syntax error in generated code: {e}")
        except Exception as e:
            raise CADError(f"Error executing generated code: {e}")

    def calculate_internal_dimensions(
        self,
        components: list[ComponentData],
        options: EnclosureOptions,
    ) -> Dimensions:
        """
        Public method to calculate internal dimensions.

        Useful for preview before generation.
        """
        return self._calculate_internal_dimensions(components, options, None)

    def position_mounting_standoffs(
        self,
        component: ComponentData,
        position: Position3D,
        standoff_height: float = 5.0,
    ) -> list[Standoff]:
        """
        Generate standoff positions for a single component.

        Public method for component-level standoff calculation.
        """
        standoffs: list[Standoff] = []

        for hole in component.mounting_holes:
            standoff = self.standoff_generator.calculate_standoff(
                hole=hole,
                component_position=position,
                standoff_height=standoff_height,
                component_id=uuid.UUID(component.id) if component.id else None,
            )
            standoffs.append(standoff)

        return standoffs


# Singleton instance
_enclosure_service: EnclosureGenerationService | None = None


def get_enclosure_service() -> EnclosureGenerationService:
    """Get or create the enclosure generation service."""
    global _enclosure_service
    if _enclosure_service is None:
        _enclosure_service = EnclosureGenerationService()
    return _enclosure_service
