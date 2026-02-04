"""
Tests for CAD Hardware Catalog.

Tests hardware specifications, dimensions, screw configurations,
and bill of materials generation.
"""

import pytest

from app.cad.hardware import (
    HardwareType,
    ScrewHead,
    ScrewDrive,
    HardwareSpec,
    METRIC_SOCKET_HEAD_SCREWS,
    COMMON_SCREW_LENGTHS,
)


# =============================================================================
# Hardware Type Tests
# =============================================================================

class TestHardwareType:
    """Tests for hardware type enum."""

    def test_hardware_types(self):
        """Test all hardware types exist."""
        assert HardwareType.SCREW == "screw"
        assert HardwareType.NUT == "nut"
        assert HardwareType.WASHER == "washer"
        assert HardwareType.THREADED_INSERT == "threaded_insert"
        assert HardwareType.STANDOFF == "standoff"
        assert HardwareType.GASKET == "gasket"

    def test_hardware_type_count(self):
        """Test expected number of hardware types."""
        assert len(HardwareType) >= 6


# =============================================================================
# Screw Head Tests
# =============================================================================

class TestScrewHead:
    """Tests for screw head styles."""

    def test_screw_head_styles(self):
        """Test all screw head styles exist."""
        assert ScrewHead.SOCKET_HEAD == "socket_head"
        assert ScrewHead.BUTTON_HEAD == "button_head"
        assert ScrewHead.FLAT_HEAD == "flat_head"
        assert ScrewHead.PAN_HEAD == "pan_head"
        assert ScrewHead.HEX_HEAD == "hex_head"

    def test_screw_head_count(self):
        """Test expected number of head styles."""
        assert len(ScrewHead) >= 5


# =============================================================================
# Screw Drive Tests
# =============================================================================

class TestScrewDrive:
    """Tests for screw drive types."""

    def test_screw_drive_types(self):
        """Test all screw drive types exist."""
        assert ScrewDrive.HEX == "hex"
        assert ScrewDrive.PHILLIPS == "phillips"
        assert ScrewDrive.TORX == "torx"
        assert ScrewDrive.SLOTTED == "slotted"


# =============================================================================
# Hardware Spec Tests
# =============================================================================

class TestHardwareSpec:
    """Tests for hardware specification dataclass."""

    def test_create_screw_spec(self):
        """Test creating a screw specification."""
        spec = HardwareSpec(
            type=HardwareType.SCREW,
            name="M3x10 Socket Head",
            description="M3 socket head cap screw, 10mm length",
            dimensions={
                "thread_diameter": 3.0,
                "head_diameter": 5.5,
                "head_height": 3.0,
                "length": 10.0,
            },
        )
        
        assert spec.type == HardwareType.SCREW
        assert spec.name == "M3x10 Socket Head"
        assert spec.dimensions["thread_diameter"] == 3.0

    def test_create_insert_spec(self):
        """Test creating a threaded insert specification."""
        spec = HardwareSpec(
            type=HardwareType.THREADED_INSERT,
            name="M3 Heat-Set Insert",
            description="M3 brass heat-set insert for 3D printing",
            dimensions={
                "thread": 3.0,
                "outer_diameter": 4.5,
                "length": 5.0,
            },
            material="Brass",
        )
        
        assert spec.type == HardwareType.THREADED_INSERT
        assert spec.material == "Brass"

    def test_default_material(self):
        """Test default material is Steel."""
        spec = HardwareSpec(
            type=HardwareType.SCREW,
            name="Test Screw",
            description="Test",
        )
        
        assert spec.material == "Steel"
        assert spec.finish == "Black Oxide"

    def test_get_dimension(self):
        """Test getting dimension value."""
        spec = HardwareSpec(
            type=HardwareType.SCREW,
            name="Test",
            description="Test",
            dimensions={"length": 20.0, "diameter": 5.0},
        )
        
        assert spec.get_dimension("length") == 20.0
        assert spec.get_dimension("diameter") == 5.0

    def test_get_dimension_default(self):
        """Test getting missing dimension returns default."""
        spec = HardwareSpec(
            type=HardwareType.SCREW,
            name="Test",
            description="Test",
            dimensions={},
        )
        
        assert spec.get_dimension("missing") == 0.0
        assert spec.get_dimension("missing", 10.0) == 10.0

    def test_mcmaster_part_number(self):
        """Test McMaster part number field."""
        spec = HardwareSpec(
            type=HardwareType.SCREW,
            name="M3x10 SHCS",
            description="Socket head cap screw",
            mcmaster_pn="91290A115",
        )
        
        assert spec.mcmaster_pn == "91290A115"

    def test_supplier_url(self):
        """Test supplier URL field."""
        spec = HardwareSpec(
            type=HardwareType.WASHER,
            name="M3 Washer",
            description="Standard washer",
            supplier_url="https://example.com/washer",
        )
        
        assert spec.supplier_url == "https://example.com/washer"


# =============================================================================
# Metric Screw Catalog Tests
# =============================================================================

class TestMetricScrewCatalog:
    """Tests for metric screw dimensions catalog."""

    def test_m3_dimensions(self):
        """Test M3 screw dimensions."""
        dims = METRIC_SOCKET_HEAD_SCREWS["M3"]
        
        thread_dia, head_dia, head_height, hex_size = dims
        assert thread_dia == 3.0
        assert head_dia == 5.5
        assert head_height == 3.0
        assert hex_size == 2.5

    def test_m4_dimensions(self):
        """Test M4 screw dimensions."""
        dims = METRIC_SOCKET_HEAD_SCREWS["M4"]
        
        thread_dia, head_dia, head_height, hex_size = dims
        assert thread_dia == 4.0
        assert head_dia == 7.0

    def test_m5_dimensions(self):
        """Test M5 screw dimensions."""
        dims = METRIC_SOCKET_HEAD_SCREWS["M5"]
        
        assert dims[0] == 5.0  # thread diameter

    def test_common_sizes_exist(self):
        """Test all common metric sizes exist."""
        common_sizes = ["M2", "M2.5", "M3", "M4", "M5", "M6", "M8", "M10"]
        
        for size in common_sizes:
            assert size in METRIC_SOCKET_HEAD_SCREWS

    def test_dimensions_tuple_structure(self):
        """Test all dimension tuples have 4 elements."""
        for size, dims in METRIC_SOCKET_HEAD_SCREWS.items():
            assert len(dims) == 4, f"{size} should have 4 dimension values"

    def test_head_larger_than_thread(self):
        """Test head diameter is larger than thread diameter."""
        for size, dims in METRIC_SOCKET_HEAD_SCREWS.items():
            thread_dia, head_dia = dims[0], dims[1]
            assert head_dia > thread_dia, f"{size} head should be larger than thread"


# =============================================================================
# Common Screw Lengths Tests
# =============================================================================

class TestCommonScrewLengths:
    """Tests for common screw length catalog."""

    def test_lengths_are_sorted(self):
        """Test lengths are in ascending order."""
        assert COMMON_SCREW_LENGTHS == sorted(COMMON_SCREW_LENGTHS)

    def test_common_lengths_exist(self):
        """Test common lengths are included."""
        assert 6 in COMMON_SCREW_LENGTHS
        assert 10 in COMMON_SCREW_LENGTHS
        assert 20 in COMMON_SCREW_LENGTHS
        assert 30 in COMMON_SCREW_LENGTHS

    def test_all_lengths_positive(self):
        """Test all lengths are positive."""
        for length in COMMON_SCREW_LENGTHS:
            assert length > 0

    def test_minimum_length(self):
        """Test minimum length is reasonable."""
        assert min(COMMON_SCREW_LENGTHS) >= 4

    def test_maximum_length(self):
        """Test maximum length is reasonable."""
        assert max(COMMON_SCREW_LENGTHS) <= 100


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_dimensions(self):
        """Test spec with no dimensions."""
        spec = HardwareSpec(
            type=HardwareType.GASKET,
            name="Custom Gasket",
            description="Custom gasket",
            dimensions={},
        )
        
        assert len(spec.dimensions) == 0

    def test_custom_properties(self):
        """Test custom properties field."""
        spec = HardwareSpec(
            type=HardwareType.SCREW,
            name="Special Screw",
            description="Special screw with extra props",
            properties={
                "torque_nm": 1.5,
                "temperature_rating": 150,
                "corrosion_resistant": True,
            },
        )
        
        assert spec.properties["torque_nm"] == 1.5
        assert spec.properties["corrosion_resistant"] is True

    def test_standoff_spec(self):
        """Test standoff specification."""
        spec = HardwareSpec(
            type=HardwareType.STANDOFF,
            name="M3x10 Standoff",
            description="Female-female standoff",
            dimensions={
                "thread": 3.0,
                "outer_diameter": 5.0,
                "length": 10.0,
            },
        )
        
        assert spec.type == HardwareType.STANDOFF
        assert spec.get_dimension("length") == 10.0
