"""
Tests for CAD Drawing Generator Module.

Tests drawing view types, formats, paper sizes, and configuration dataclasses.
"""

from app.cad.drawing_generator import (
    PAPER_DIMENSIONS,
    DimensionStyle,
    DrawingConfig,
    DrawingFormat,
    DrawingView,
    DrawingViewType,
    PaperSize,
    TitleBlock,
)

# =============================================================================
# DrawingViewType Tests
# =============================================================================


class TestDrawingViewType:
    """Tests for DrawingViewType enum."""

    def test_front_view(self):
        """Test front view type."""
        assert DrawingViewType.FRONT == "front"

    def test_back_view(self):
        """Test back view type."""
        assert DrawingViewType.BACK == "back"

    def test_left_view(self):
        """Test left view type."""
        assert DrawingViewType.LEFT == "left"

    def test_right_view(self):
        """Test right view type."""
        assert DrawingViewType.RIGHT == "right"

    def test_top_view(self):
        """Test top view type."""
        assert DrawingViewType.TOP == "top"

    def test_bottom_view(self):
        """Test bottom view type."""
        assert DrawingViewType.BOTTOM == "bottom"

    def test_isometric_view(self):
        """Test isometric view type."""
        assert DrawingViewType.ISOMETRIC == "isometric"

    def test_section_view(self):
        """Test section view type."""
        assert DrawingViewType.SECTION == "section"

    def test_detail_view(self):
        """Test detail view type."""
        assert DrawingViewType.DETAIL == "detail"

    def test_all_views_are_strings(self):
        """Test all view types are strings."""
        for view_type in DrawingViewType:
            assert isinstance(view_type.value, str)


# =============================================================================
# DrawingFormat Tests
# =============================================================================


class TestDrawingFormat:
    """Tests for DrawingFormat enum."""

    def test_pdf_format(self):
        """Test PDF format."""
        assert DrawingFormat.PDF == "pdf"

    def test_dxf_format(self):
        """Test DXF format."""
        assert DrawingFormat.DXF == "dxf"

    def test_svg_format(self):
        """Test SVG format."""
        assert DrawingFormat.SVG == "svg"

    def test_png_format(self):
        """Test PNG format."""
        assert DrawingFormat.PNG == "png"

    def test_all_formats_are_strings(self):
        """Test all formats are strings."""
        for fmt in DrawingFormat:
            assert isinstance(fmt.value, str)


# =============================================================================
# PaperSize Tests
# =============================================================================


class TestPaperSize:
    """Tests for PaperSize enum."""

    def test_a_series_sizes(self):
        """Test A-series paper sizes."""
        assert PaperSize.A4 == "A4"
        assert PaperSize.A3 == "A3"
        assert PaperSize.A2 == "A2"
        assert PaperSize.A1 == "A1"
        assert PaperSize.A0 == "A0"

    def test_us_sizes(self):
        """Test US paper sizes."""
        assert PaperSize.LETTER == "letter"
        assert PaperSize.LEGAL == "legal"
        assert PaperSize.TABLOID == "tabloid"

    def test_all_sizes_are_strings(self):
        """Test all sizes are strings."""
        for size in PaperSize:
            assert isinstance(size.value, str)


# =============================================================================
# Paper Dimensions Tests
# =============================================================================


class TestPaperDimensions:
    """Tests for paper dimension constants."""

    def test_dimensions_exist(self):
        """Test paper dimensions dictionary exists."""
        assert PAPER_DIMENSIONS is not None
        assert isinstance(PAPER_DIMENSIONS, dict)

    def test_all_paper_sizes_have_dimensions(self):
        """Test all paper sizes have dimensions defined."""
        for paper_size in PaperSize:
            assert paper_size in PAPER_DIMENSIONS

    def test_dimensions_are_tuples(self):
        """Test dimensions are (width, height) tuples."""
        for _size, dims in PAPER_DIMENSIONS.items():
            assert isinstance(dims, tuple)
            assert len(dims) == 2
            assert isinstance(dims[0], (int, float))
            assert isinstance(dims[1], (int, float))

    def test_a4_dimensions(self):
        """Test A4 dimensions are correct."""
        assert PAPER_DIMENSIONS[PaperSize.A4] == (210, 297)

    def test_a3_dimensions(self):
        """Test A3 dimensions are correct."""
        assert PAPER_DIMENSIONS[PaperSize.A3] == (297, 420)

    def test_letter_dimensions(self):
        """Test Letter dimensions are correct."""
        width, height = PAPER_DIMENSIONS[PaperSize.LETTER]
        assert abs(width - 215.9) < 0.1
        assert abs(height - 279.4) < 0.1

    def test_dimensions_are_positive(self):
        """Test all dimensions are positive."""
        for dims in PAPER_DIMENSIONS.values():
            assert dims[0] > 0
            assert dims[1] > 0


# =============================================================================
# DrawingView Tests
# =============================================================================


class TestDrawingView:
    """Tests for DrawingView dataclass."""

    def test_basic_creation(self):
        """Test creating a basic drawing view."""
        view = DrawingView(
            view_type=DrawingViewType.FRONT,
            position_x=0.5,
            position_y=0.5,
        )

        assert view.view_type == DrawingViewType.FRONT
        assert view.position_x == 0.5
        assert view.position_y == 0.5

    def test_default_values(self):
        """Test default values are set correctly."""
        view = DrawingView(
            view_type=DrawingViewType.TOP,
            position_x=0,
            position_y=0,
        )

        assert view.scale == 1.0
        assert view.show_hidden_lines is False
        assert view.show_center_lines is True
        assert view.label is None
        assert view.section_plane is None
        assert view.section_offset == 0.0
        assert view.detail_center is None
        assert view.detail_radius == 10.0
        assert view.detail_scale == 2.0

    def test_section_view(self):
        """Test section view configuration."""
        view = DrawingView(
            view_type=DrawingViewType.SECTION,
            position_x=0.7,
            position_y=0.5,
            section_plane="A-A",
            section_offset=25.0,
        )

        assert view.view_type == DrawingViewType.SECTION
        assert view.section_plane == "A-A"
        assert view.section_offset == 25.0

    def test_detail_view(self):
        """Test detail view configuration."""
        view = DrawingView(
            view_type=DrawingViewType.DETAIL,
            position_x=0.8,
            position_y=0.8,
            detail_center=(50.0, 25.0, 0.0),
            detail_radius=15.0,
            detail_scale=4.0,
        )

        assert view.view_type == DrawingViewType.DETAIL
        assert view.detail_center == (50.0, 25.0, 0.0)
        assert view.detail_radius == 15.0
        assert view.detail_scale == 4.0


# =============================================================================
# DimensionStyle Tests
# =============================================================================


class TestDimensionStyle:
    """Tests for DimensionStyle dataclass."""

    def test_default_creation(self):
        """Test default dimension style."""
        style = DimensionStyle()

        assert style.font_size == 3.5
        assert style.arrow_size == 3.0
        assert style.line_thickness == 0.35
        assert style.extension_gap == 1.0
        assert style.extension_overshoot == 2.0
        assert style.decimal_places == 2
        assert style.units == "mm"
        assert style.show_units is False

    def test_custom_style(self):
        """Test custom dimension style."""
        style = DimensionStyle(
            font_size=5.0,
            decimal_places=3,
            units="in",
            show_units=True,
        )

        assert style.font_size == 5.0
        assert style.decimal_places == 3
        assert style.units == "in"
        assert style.show_units is True


# =============================================================================
# TitleBlock Tests
# =============================================================================


class TestTitleBlock:
    """Tests for TitleBlock dataclass."""

    def test_default_creation(self):
        """Test default title block."""
        title_block = TitleBlock()

        assert title_block.company_name == ""
        assert title_block.project_name == ""
        assert title_block.drawing_title == ""
        assert title_block.part_number == ""
        assert title_block.revision == "A"
        assert title_block.drawn_by == ""
        assert title_block.notes == []

    def test_custom_title_block(self):
        """Test custom title block."""
        title_block = TitleBlock(
            company_name="ACME Corp",
            project_name="Widget Assembly",
            drawing_title="Main Housing",
            part_number="WID-001-A",
            revision="C",
            drawn_by="John Doe",
            material="Aluminum 6061",
            notes=["All dimensions in mm", "Deburr all edges"],
        )

        assert title_block.company_name == "ACME Corp"
        assert title_block.project_name == "Widget Assembly"
        assert title_block.drawing_title == "Main Housing"
        assert title_block.part_number == "WID-001-A"
        assert title_block.revision == "C"
        assert title_block.material == "Aluminum 6061"
        assert len(title_block.notes) == 2


# =============================================================================
# DrawingConfig Tests
# =============================================================================


class TestDrawingConfig:
    """Tests for DrawingConfig dataclass."""

    def test_default_config(self):
        """Test default drawing configuration."""
        config = DrawingConfig()

        assert config.paper_size == PaperSize.A4
        assert config.orientation == "landscape"
        assert config.views == []
        assert isinstance(config.dimension_style, DimensionStyle)
        assert isinstance(config.title_block, TitleBlock)
        assert config.show_border is True
        assert config.border_margin == 10.0
        assert config.auto_dimensions is True
        assert config.projection_type == "third_angle"

    def test_config_with_views(self):
        """Test configuration with views."""
        views = [
            DrawingView(DrawingViewType.FRONT, 0.3, 0.5),
            DrawingView(DrawingViewType.TOP, 0.3, 0.8),
            DrawingView(DrawingViewType.RIGHT, 0.7, 0.5),
        ]
        config = DrawingConfig(
            paper_size=PaperSize.A3,
            views=views,
        )

        assert config.paper_size == PaperSize.A3
        assert len(config.views) == 3

    def test_config_with_custom_title_block(self):
        """Test configuration with custom title block."""
        title_block = TitleBlock(
            company_name="Test Co",
            drawing_title="Test Part",
        )
        config = DrawingConfig(title_block=title_block)

        assert config.title_block.company_name == "Test Co"
        assert config.title_block.drawing_title == "Test Part"

    def test_first_angle_projection(self):
        """Test first angle projection setting."""
        config = DrawingConfig(projection_type="first_angle")

        assert config.projection_type == "first_angle"


# =============================================================================
# Edge Cases
# =============================================================================


class TestDrawingEdgeCases:
    """Tests for edge cases in drawing generator."""

    def test_zero_position_view(self):
        """Test view at zero position."""
        view = DrawingView(
            view_type=DrawingViewType.FRONT,
            position_x=0.0,
            position_y=0.0,
        )

        assert view.position_x == 0.0
        assert view.position_y == 0.0

    def test_maximum_position_view(self):
        """Test view at maximum position."""
        view = DrawingView(
            view_type=DrawingViewType.FRONT,
            position_x=1.0,
            position_y=1.0,
        )

        assert view.position_x == 1.0
        assert view.position_y == 1.0

    def test_very_small_scale(self):
        """Test very small scale value."""
        view = DrawingView(
            view_type=DrawingViewType.FRONT,
            position_x=0.5,
            position_y=0.5,
            scale=0.01,
        )

        assert view.scale == 0.01

    def test_large_scale(self):
        """Test large scale value."""
        view = DrawingView(
            view_type=DrawingViewType.DETAIL,
            position_x=0.5,
            position_y=0.5,
            scale=10.0,
            detail_scale=20.0,
        )

        assert view.scale == 10.0
        assert view.detail_scale == 20.0

    def test_empty_notes_list(self):
        """Test title block with empty notes."""
        title_block = TitleBlock()

        assert title_block.notes == []
        title_block.notes.append("Test note")
        assert len(title_block.notes) == 1

    def test_portrait_orientation(self):
        """Test portrait orientation."""
        config = DrawingConfig(orientation="portrait")

        assert config.orientation == "portrait"

    def test_no_border(self):
        """Test configuration without border."""
        config = DrawingConfig(show_border=False)

        assert config.show_border is False
