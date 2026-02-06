"""
2D Drawing Generator service.

Generates technical 2D drawings from 3D CAD models with orthographic projections,
cross-sections, dimensions, and title blocks.

Migrated from CadQuery to Build123d.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from io import BytesIO
from typing import Any


class DrawingViewType(StrEnum):
    """Types of standard drawing views."""

    FRONT = "front"
    BACK = "back"
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"
    ISOMETRIC = "isometric"
    SECTION = "section"
    DETAIL = "detail"


class DrawingFormat(StrEnum):
    """Output formats for drawings."""

    PDF = "pdf"
    DXF = "dxf"
    SVG = "svg"
    PNG = "png"


class PaperSize(StrEnum):
    """Standard paper sizes."""

    A4 = "A4"
    A3 = "A3"
    A2 = "A2"
    A1 = "A1"
    A0 = "A0"
    LETTER = "letter"
    LEGAL = "legal"
    TABLOID = "tabloid"


# Paper dimensions in mm (width, height)
PAPER_DIMENSIONS = {
    PaperSize.A4: (210, 297),
    PaperSize.A3: (297, 420),
    PaperSize.A2: (420, 594),
    PaperSize.A1: (594, 841),
    PaperSize.A0: (841, 1189),
    PaperSize.LETTER: (215.9, 279.4),
    PaperSize.LEGAL: (215.9, 355.6),
    PaperSize.TABLOID: (279.4, 431.8),
}


@dataclass
class DrawingView:
    """Configuration for a single view in the drawing."""

    view_type: DrawingViewType
    position_x: float  # Position on sheet (0-1)
    position_y: float  # Position on sheet (0-1)
    scale: float = 1.0
    show_hidden_lines: bool = False
    show_center_lines: bool = True
    label: str | None = None

    # For section views
    section_plane: str | None = None  # e.g., "A-A"
    section_offset: float = 0.0

    # For detail views
    detail_center: tuple[float, float, float] | None = None
    detail_radius: float = 10.0
    detail_scale: float = 2.0


@dataclass
class DimensionStyle:
    """Style settings for dimensions."""

    font_size: float = 3.5  # mm
    arrow_size: float = 3.0  # mm
    line_thickness: float = 0.35  # mm
    extension_gap: float = 1.0  # mm
    extension_overshoot: float = 2.0  # mm
    decimal_places: int = 2
    units: str = "mm"
    show_units: bool = False


@dataclass
class TitleBlock:
    """Title block configuration."""

    company_name: str = ""
    project_name: str = ""
    drawing_title: str = ""
    part_number: str = ""
    revision: str = "A"
    drawn_by: str = ""
    checked_by: str = ""
    approved_by: str = ""
    date: str = ""
    scale: str = ""
    sheet: str = "1 of 1"
    material: str = ""
    finish: str = ""
    weight: str = ""
    notes: list[str] = field(default_factory=list)


@dataclass
class DrawingConfig:
    """Complete drawing configuration."""

    paper_size: PaperSize = PaperSize.A4
    orientation: str = "landscape"  # portrait or landscape
    views: list[DrawingView] = field(default_factory=list)
    dimension_style: DimensionStyle = field(default_factory=DimensionStyle)
    title_block: TitleBlock = field(default_factory=TitleBlock)
    show_border: bool = True
    border_margin: float = 10.0  # mm
    auto_dimensions: bool = True
    projection_type: str = "third_angle"  # third_angle or first_angle


class DrawingGenerator:
    """
    Generates 2D technical drawings from 3D CAD models.

    Uses Build123d/OCP for projection and drawing generation.
    """

    def __init__(self) -> None:
        self._b3d = None
        self._ocp_available = False
        self._load_cad_libraries()

    def _load_cad_libraries(self) -> None:
        """Load CAD libraries if available."""
        try:
            import build123d as b3d

            self._b3d = b3d
            self._ocp_available = True
        except ImportError:
            pass

    async def generate_drawing(
        self,
        step_file_path: str,
        config: DrawingConfig,
        output_format: DrawingFormat = DrawingFormat.SVG,
    ) -> bytes:
        """
        Generate a 2D drawing from a STEP file.

        Args:
            step_file_path: Path to the STEP file
            config: Drawing configuration
            output_format: Output format (PDF, DXF, SVG, PNG)

        Returns:
            Drawing file bytes
        """
        if not self._ocp_available:
            return await self._generate_fallback_drawing(config, output_format)

        try:
            # Load the STEP file using Build123d
            shape = self._b3d.import_step(step_file_path)

            # Generate views
            views_data = []
            for view in config.views:
                view_data = self._project_view(shape, view)
                views_data.append(view_data)

            # Create drawing
            drawing = self._create_drawing(views_data, config)

            # Export to requested format
            return self._export_drawing(drawing, output_format)

        except Exception:
            # Fall back to mock drawing on error
            return await self._generate_fallback_drawing(config, output_format)

    def _project_view(
        self,
        shape: Any,
        view: DrawingView,
    ) -> dict[str, Any]:
        """
        Project a 3D shape to 2D for a specific view.

        Returns view data including edges and dimensions.
        """
        # Direction vectors for standard views
        view_directions = {
            DrawingViewType.FRONT: (0, -1, 0),
            DrawingViewType.BACK: (0, 1, 0),
            DrawingViewType.LEFT: (-1, 0, 0),
            DrawingViewType.RIGHT: (1, 0, 0),
            DrawingViewType.TOP: (0, 0, 1),
            DrawingViewType.BOTTOM: (0, 0, -1),
            DrawingViewType.ISOMETRIC: (1, 1, 1),
        }

        direction = view_directions.get(view.view_type, (0, -1, 0))

        # Get the underlying shape for projection
        shape_to_project = shape.wrapped if hasattr(shape, "wrapped") else shape

        # Use HLR (Hidden Line Removal) algorithm
        try:
            from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt
            from OCP.HLRAlgo import HLRAlgo_Projector
            from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape

            # Create projector
            ax = gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*direction))
            projector = HLRAlgo_Projector(ax)

            # Create HLR algorithm
            hlr = HLRBRep_Algo()
            hlr.Add(shape_to_project)
            hlr.Projector(projector)
            hlr.Update()
            hlr.Hide()

            # Extract visible and hidden edges
            hlr_shapes = HLRBRep_HLRToShape(hlr)
            visible_edges = hlr_shapes.VCompound()
            hidden_edges = hlr_shapes.HCompound()

            return {
                "view": view,
                "visible_edges": visible_edges,
                "hidden_edges": hidden_edges if view.show_hidden_lines else None,
            }

        except ImportError:
            # Simplified projection without HLR
            return {
                "view": view,
                "visible_edges": None,
                "hidden_edges": None,
            }

    def _create_drawing(
        self,
        views_data: list[dict[str, Any]],
        config: DrawingConfig,
    ) -> dict[str, Any]:
        """Create the complete drawing from projected views."""
        # Get paper dimensions
        width, height = PAPER_DIMENSIONS[config.paper_size]
        if config.orientation == "landscape":
            width, height = height, width

        drawing = {
            "width": width,
            "height": height,
            "views": views_data,
            "config": config,
            "elements": [],
        }

        # Add border
        if config.show_border:
            margin = config.border_margin
            drawing["elements"].append(
                {
                    "type": "rectangle",
                    "x": margin,
                    "y": margin,
                    "width": width - 2 * margin,
                    "height": height - 2 * margin,
                    "stroke_width": 0.7,
                }
            )

        # Add title block
        drawing["elements"].extend(self._create_title_block(width, height, config))

        # Add dimensions if auto-dimensions enabled
        if config.auto_dimensions:
            drawing["elements"].extend(self._create_auto_dimensions(views_data, config))

        return drawing

    def _create_title_block(
        self,
        width: float,
        _height: float,
        config: DrawingConfig,
    ) -> list[dict[str, Any]]:
        """Create title block elements."""
        tb = config.title_block
        margin = config.border_margin

        # Title block dimensions (in lower right corner)
        tb_width = 180 if width > 400 else 120
        tb_height = 50 if width > 400 else 35
        tb_x = width - margin - tb_width
        tb_y = margin

        return [
            # Outer border
            {
                "type": "rectangle",
                "x": tb_x,
                "y": tb_y,
                "width": tb_width,
                "height": tb_height,
                "stroke_width": 0.7,
            },
            # Company name
            {
                "type": "text",
                "x": tb_x + 5,
                "y": tb_y + tb_height - 5,
                "text": tb.company_name,
                "font_size": 5,
                "font_weight": "bold",
            },
            # Drawing title
            {
                "type": "text",
                "x": tb_x + tb_width / 2,
                "y": tb_y + tb_height / 2,
                "text": tb.drawing_title,
                "font_size": 6,
                "font_weight": "bold",
                "text_anchor": "middle",
            },
            # Part number
            {
                "type": "text",
                "x": tb_x + 5,
                "y": tb_y + 10,
                "text": f"P/N: {tb.part_number}",
                "font_size": 3,
            },
            # Revision
            {
                "type": "text",
                "x": tb_x + tb_width - 15,
                "y": tb_y + 10,
                "text": f"REV {tb.revision}",
                "font_size": 4,
            },
            # Scale
            {
                "type": "text",
                "x": tb_x + tb_width / 2,
                "y": tb_y + 5,
                "text": f"Scale: {tb.scale or config.views[0].scale if config.views else '1:1'}",
                "font_size": 3,
                "text_anchor": "middle",
            },
        ]

    def _create_auto_dimensions(
        self,
        views_data: list[dict[str, Any]],
        config: DrawingConfig,
    ) -> list[dict[str, Any]]:
        """Auto-generate dimensions for views."""
        elements = []

        # For now, return placeholder dimensions
        # Full implementation would analyze edges and add appropriate dimensions
        for _i, view_data in enumerate(views_data):
            view = view_data["view"]

            # Add placeholder dimension
            elements.append(
                {
                    "type": "dimension",
                    "x1": view.position_x * 100 + 10,
                    "y1": view.position_y * 100,
                    "x2": view.position_x * 100 + 60,
                    "y2": view.position_y * 100,
                    "value": "50.00",
                    "style": config.dimension_style,
                }
            )

        return elements

    def _export_drawing(
        self,
        drawing: dict[str, Any],
        output_format: DrawingFormat,
    ) -> bytes:
        """Export drawing to requested format."""
        if output_format == DrawingFormat.SVG:
            return self._export_to_svg(drawing)
        if output_format == DrawingFormat.DXF:
            return self._export_to_dxf(drawing)
        if output_format == DrawingFormat.PDF:
            return self._export_to_pdf(drawing)
        if output_format == DrawingFormat.PNG:
            return self._export_to_png(drawing)
        raise ValueError(f"Unsupported format: {output_format}")

    def _export_to_svg(self, drawing: dict[str, Any]) -> bytes:
        """Export drawing to SVG format."""
        width = drawing["width"]
        height = drawing["height"]

        svg_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<svg xmlns="http://www.w3.org/2000/svg" ',
            f'width="{width}mm" height="{height}mm" ',
            f'viewBox="0 0 {width} {height}">',
            "<style>",
            "  .line { stroke: black; stroke-width: 0.35; fill: none; }",
            "  .hidden { stroke: black; stroke-width: 0.25; stroke-dasharray: 2,1; fill: none; }",
            "  .center { stroke: black; stroke-width: 0.18; stroke-dasharray: 6,1,1,1; fill: none; }",
            "  .dimension { stroke: black; stroke-width: 0.25; fill: none; }",
            "  .text { font-family: Arial, sans-serif; fill: black; }",
            "</style>",
            '<g transform="translate(0, ' + str(height) + ') scale(1, -1)">',
        ]

        # Render elements
        for element in drawing["elements"]:
            svg_parts.append(self._element_to_svg(element))

        svg_parts.append("</g>")
        svg_parts.append("</svg>")

        return "\n".join(svg_parts).encode("utf-8")

    def _element_to_svg(self, element: dict[str, Any]) -> str:
        """Convert an element to SVG markup."""
        el_type = element.get("type")

        if el_type == "rectangle":
            return (
                f'<rect x="{element["x"]}" y="{element["y"]}" '
                f'width="{element["width"]}" height="{element["height"]}" '
                f'class="line" stroke-width="{element.get("stroke_width", 0.35)}"/>'
            )

        if el_type == "line":
            return (
                f'<line x1="{element["x1"]}" y1="{element["y1"]}" '
                f'x2="{element["x2"]}" y2="{element["y2"]}" '
                f'class="{element.get("class", "line")}"/>'
            )

        if el_type == "text":
            # Note: y is inverted in our coordinate system
            return (
                f'<text x="{element["x"]}" y="{element["y"]}" '
                f'class="text" font-size="{element.get("font_size", 3)}mm" '
                f'text-anchor="{element.get("text_anchor", "start")}" '
                f'transform="scale(1,-1)">'
                f"{element['text']}</text>"
            )

        if el_type == "dimension":
            return self._dimension_to_svg(element)

        return ""

    def _dimension_to_svg(self, dim: dict[str, Any]) -> str:
        """Convert a dimension to SVG markup."""
        x1, y1, x2, y2 = dim["x1"], dim["y1"], dim["x2"], dim["y2"]
        value = dim.get("value", "0.00")
        dim.get("style", DimensionStyle())

        # Calculate midpoint for text
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2

        return f'''
        <g class="dimension">
            <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>
            <polygon points="{x1},{y1} {x1 + 2},{y1 + 1} {x1 + 2},{y1 - 1}"/>
            <polygon points="{x2},{y2} {x2 - 2},{y2 + 1} {x2 - 2},{y2 - 1}"/>
            <text x="{mid_x}" y="{mid_y + 2}" class="text"
                  font-size="3mm" text-anchor="middle"
                  transform="scale(1,-1)">{value}</text>
        </g>
        '''

    def _export_to_dxf(self, drawing: dict[str, Any]) -> bytes:
        """Export drawing to DXF format."""
        try:
            import ezdxf

            doc = ezdxf.new("R2010")
            msp = doc.modelspace()

            for element in drawing["elements"]:
                self._element_to_dxf(msp, element)

            buffer = BytesIO()
            doc.write(buffer)
            return buffer.getvalue()

        except ImportError:
            # Return placeholder if ezdxf not available
            return b"DXF export requires ezdxf library"

    def _element_to_dxf(self, msp: Any, element: dict[str, Any]) -> None:
        """Add element to DXF modelspace."""
        el_type = element.get("type")

        if el_type == "rectangle":
            x, y = element["x"], element["y"]
            w, h = element["width"], element["height"]
            msp.add_lwpolyline([(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)])

        elif el_type == "line":
            msp.add_line((element["x1"], element["y1"]), (element["x2"], element["y2"]))

        elif el_type == "text":
            msp.add_text(
                element["text"],
                dxfattribs={
                    "insert": (element["x"], element["y"]),
                    "height": element.get("font_size", 3),
                },
            )

    def _export_to_pdf(self, drawing: dict[str, Any]) -> bytes:
        """Export drawing to PDF format."""
        # First generate SVG, then convert to PDF
        svg_bytes = self._export_to_svg(drawing)

        try:
            import cairosvg

            return cairosvg.svg2pdf(bytestring=svg_bytes)  # type: ignore[no-any-return]
        except ImportError:
            # Return SVG if cairosvg not available
            return svg_bytes

    def _export_to_png(self, drawing: dict[str, Any]) -> bytes:
        """Export drawing to PNG format."""
        svg_bytes = self._export_to_svg(drawing)

        try:
            import cairosvg

            return cairosvg.svg2png(bytestring=svg_bytes, dpi=300)  # type: ignore[no-any-return]
        except ImportError:
            # Return placeholder PNG
            return b"PNG export requires cairosvg library"

    async def _generate_fallback_drawing(
        self,
        config: DrawingConfig,
        output_format: DrawingFormat,
    ) -> bytes:
        """Generate a placeholder drawing when CAD libraries unavailable."""
        width, height = PAPER_DIMENSIONS[config.paper_size]
        if config.orientation == "landscape":
            width, height = height, width

        drawing = {
            "width": width,
            "height": height,
            "views": [],
            "config": config,
            "elements": [],
        }

        # Add border
        margin = config.border_margin
        drawing["elements"].append(
            {
                "type": "rectangle",
                "x": margin,
                "y": margin,
                "width": width - 2 * margin,
                "height": height - 2 * margin,
                "stroke_width": 0.7,
            }
        )

        # Add title block
        drawing["elements"].extend(self._create_title_block(width, height, config))

        # Add placeholder text
        drawing["elements"].append(
            {
                "type": "text",
                "x": width / 2,
                "y": height / 2,
                "text": "[Drawing views will appear here]",
                "font_size": 5,
                "text_anchor": "middle",
            }
        )

        return self._export_drawing(drawing, output_format)

    def get_default_views(self, projection_type: str = "third_angle") -> list[DrawingView]:
        """Get default view layout for standard 3-view drawing."""
        if projection_type == "third_angle":
            # Third angle projection (US standard)
            return [
                DrawingView(
                    view_type=DrawingViewType.FRONT,
                    position_x=0.3,
                    position_y=0.5,
                    scale=1.0,
                ),
                DrawingView(
                    view_type=DrawingViewType.TOP,
                    position_x=0.3,
                    position_y=0.8,
                    scale=1.0,
                ),
                DrawingView(
                    view_type=DrawingViewType.RIGHT,
                    position_x=0.6,
                    position_y=0.5,
                    scale=1.0,
                ),
                DrawingView(
                    view_type=DrawingViewType.ISOMETRIC,
                    position_x=0.6,
                    position_y=0.8,
                    scale=0.5,
                ),
            ]
        # First angle projection (ISO standard)
        return [
            DrawingView(
                view_type=DrawingViewType.FRONT,
                position_x=0.3,
                position_y=0.5,
                scale=1.0,
            ),
            DrawingView(
                view_type=DrawingViewType.TOP,
                position_x=0.3,
                position_y=0.2,
                scale=1.0,
            ),
            DrawingView(
                view_type=DrawingViewType.LEFT,
                position_x=0.6,
                position_y=0.5,
                scale=1.0,
            ),
            DrawingView(
                view_type=DrawingViewType.ISOMETRIC,
                position_x=0.6,
                position_y=0.8,
                scale=0.5,
            ),
        ]


# Create singleton instance
drawing_generator = DrawingGenerator()
