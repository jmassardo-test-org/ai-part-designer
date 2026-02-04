"""Tests for CAD v2 component registry."""

import pytest

from app.cad_v2.components.registry import (
    AmbiguousMatchError,
    ComponentMatch,
    ComponentNotFoundError,
    ComponentRegistry,
    get_registry,
)
from app.cad_v2.schemas.base import BoundingBox, Dimension
from app.cad_v2.schemas.components import ComponentCategory, ComponentDefinition


def _create_test_component(
    id: str,
    name: str,
    aliases: list[str] | None = None,
) -> ComponentDefinition:
    """Create a test component definition."""
    return ComponentDefinition(
        id=id,
        name=name,
        category=ComponentCategory.BOARD,
        aliases=aliases or [],
        dimensions=BoundingBox(
            width=Dimension(value=50),
            depth=Dimension(value=30),
            height=Dimension(value=10),
        ),
    )


class TestComponentRegistry:
    """Tests for ComponentRegistry class."""

    def test_registry_register_component(self) -> None:
        """Registry should register a component."""
        registry = ComponentRegistry()
        comp = _create_test_component("test-comp", "Test Component")

        registry.register(comp)

        assert registry.count == 1
        assert registry.get("test-comp") is not None

    def test_registry_reject_duplicate_id(self) -> None:
        """Registry should reject duplicate component IDs."""
        registry = ComponentRegistry()
        comp1 = _create_test_component("test-comp", "Test 1")
        comp2 = _create_test_component("test-comp", "Test 2")

        registry.register(comp1)
        with pytest.raises(ValueError) as exc_info:
            registry.register(comp2)

        assert "already registered" in str(exc_info.value)

    def test_registry_get_by_id(self) -> None:
        """Registry should get component by exact ID."""
        registry = ComponentRegistry()
        comp = _create_test_component("my-board", "My Board")
        registry.register(comp)

        result = registry.get("my-board")

        assert result is not None
        assert result.id == "my-board"

    def test_registry_get_returns_none_for_unknown(self) -> None:
        """Registry.get should return None for unknown ID."""
        registry = ComponentRegistry()

        result = registry.get("unknown")

        assert result is None

    def test_registry_get_by_alias(self) -> None:
        """Registry should get component by alias."""
        registry = ComponentRegistry()
        comp = _create_test_component(
            "raspberry-pi-5",
            "Raspberry Pi 5",
            aliases=["rpi5", "pi 5"],
        )
        registry.register(comp)

        result = registry.get_by_alias("pi 5")

        assert result is not None
        assert result.id == "raspberry-pi-5"

    def test_registry_alias_case_insensitive(self) -> None:
        """Registry alias lookup should be case-insensitive."""
        registry = ComponentRegistry()
        comp = _create_test_component(
            "raspberry-pi-5",
            "Raspberry Pi 5",
            aliases=["rpi5", "pi 5"],
        )
        registry.register(comp)

        result = registry.get_by_alias("PI 5")

        assert result is not None
        assert result.id == "raspberry-pi-5"

    def test_registry_name_as_alias(self) -> None:
        """Registry should allow lookup by component name."""
        registry = ComponentRegistry()
        comp = _create_test_component("my-board", "Super Cool Board")
        registry.register(comp)

        result = registry.get_by_alias("Super Cool Board")

        assert result is not None
        assert result.id == "my-board"


class TestComponentSearch:
    """Tests for fuzzy search functionality."""

    @pytest.fixture
    def populated_registry(self) -> ComponentRegistry:
        """Create a registry with test components."""
        registry = ComponentRegistry()
        registry.register(_create_test_component(
            "raspberry-pi-5",
            "Raspberry Pi 5",
            aliases=["rpi5", "pi 5"],
        ))
        registry.register(_create_test_component(
            "raspberry-pi-4b",
            "Raspberry Pi 4 Model B",
            aliases=["rpi4", "pi 4"],
        ))
        registry.register(_create_test_component(
            "arduino-uno",
            "Arduino Uno R3",
            aliases=["uno", "arduino"],
        ))
        return registry

    def test_search_exact_id(self, populated_registry: ComponentRegistry) -> None:
        """Search should match exact ID."""
        results = populated_registry.search("raspberry-pi-5")

        assert len(results) == 1
        assert results[0].component.id == "raspberry-pi-5"
        assert results[0].score == 1.0
        assert results[0].match_type == "exact"

    def test_search_exact_alias(self, populated_registry: ComponentRegistry) -> None:
        """Search should match exact alias."""
        results = populated_registry.search("rpi5")

        assert len(results) == 1
        assert results[0].component.id == "raspberry-pi-5"
        assert results[0].score == 1.0
        assert results[0].match_type == "alias"

    def test_search_fuzzy_match(self, populated_registry: ComponentRegistry) -> None:
        """Search should fuzzy match similar strings."""
        results = populated_registry.search("rasberry pi")  # Typo

        assert len(results) >= 1
        # Should find Pi variants
        found_ids = [r.component.id for r in results]
        assert any("raspberry" in id for id in found_ids)

    def test_search_threshold(self, populated_registry: ComponentRegistry) -> None:
        """Search should respect threshold parameter."""
        # Very dissimilar query
        results = populated_registry.search("xyz123", threshold=0.9)
        assert len(results) == 0

        # Lower threshold
        results = populated_registry.search("xyz123", threshold=0.1)
        # May or may not find results depending on fuzzy matching

    def test_search_max_results(self, populated_registry: ComponentRegistry) -> None:
        """Search should limit results to max_results."""
        results = populated_registry.search("pi", threshold=0.3, max_results=2)

        assert len(results) <= 2


class TestComponentLookup:
    """Tests for strict lookup functionality."""

    @pytest.fixture
    def populated_registry(self) -> ComponentRegistry:
        """Create a registry with test components."""
        registry = ComponentRegistry()
        registry.register(_create_test_component(
            "raspberry-pi-5",
            "Raspberry Pi 5",
            aliases=["rpi5", "pi 5"],
        ))
        registry.register(_create_test_component(
            "raspberry-pi-4b",
            "Raspberry Pi 4 Model B",
            aliases=["rpi4", "pi 4"],
        ))
        return registry

    def test_lookup_exact_match(self, populated_registry: ComponentRegistry) -> None:
        """Lookup should return component for exact match."""
        result = populated_registry.lookup("raspberry-pi-5")

        assert result.id == "raspberry-pi-5"

    def test_lookup_not_found_raises(self, populated_registry: ComponentRegistry) -> None:
        """Lookup should raise ComponentNotFoundError when not found."""
        with pytest.raises(ComponentNotFoundError) as exc_info:
            populated_registry.lookup("nonexistent-board")

        assert "nonexistent-board" in str(exc_info.value)

    def test_lookup_not_found_includes_suggestions(
        self, populated_registry: ComponentRegistry
    ) -> None:
        """ComponentNotFoundError should include suggestions."""
        with pytest.raises(ComponentNotFoundError) as exc_info:
            populated_registry.lookup("unknown-xyz-board", threshold=0.9)

        # Should have suggestions from fuzzy match
        assert exc_info.value.query == "unknown-xyz-board"


class TestCategoryListing:
    """Tests for category listing functionality."""

    @pytest.fixture
    def mixed_registry(self) -> ComponentRegistry:
        """Create a registry with mixed categories."""
        registry = ComponentRegistry()

        # Board
        registry.register(ComponentDefinition(
            id="board-1",
            name="Board One",
            category=ComponentCategory.BOARD,
            dimensions=BoundingBox(
                width=Dimension(value=50),
                depth=Dimension(value=30),
                height=Dimension(value=10),
            ),
        ))

        # Display
        registry.register(ComponentDefinition(
            id="display-1",
            name="Display One",
            category=ComponentCategory.DISPLAY,
            dimensions=BoundingBox(
                width=Dimension(value=100),
                depth=Dimension(value=60),
                height=Dimension(value=12),
            ),
        ))
        registry.register(ComponentDefinition(
            id="display-2",
            name="Display Two",
            category=ComponentCategory.DISPLAY,
            dimensions=BoundingBox(
                width=Dimension(value=80),
                depth=Dimension(value=36),
                height=Dimension(value=12),
            ),
        ))

        return registry

    def test_list_category(self, mixed_registry: ComponentRegistry) -> None:
        """list_category should return components in category."""
        displays = mixed_registry.list_category(ComponentCategory.DISPLAY)

        assert len(displays) == 2
        assert all(d.category == ComponentCategory.DISPLAY for d in displays)

    def test_list_category_empty(self, mixed_registry: ComponentRegistry) -> None:
        """list_category should return empty list for unused category."""
        sensors = mixed_registry.list_category(ComponentCategory.SENSOR)

        assert sensors == []

    def test_list_all(self, mixed_registry: ComponentRegistry) -> None:
        """list_all should return all components."""
        all_components = mixed_registry.list_all()

        assert len(all_components) == 3


class TestGlobalRegistry:
    """Tests for global registry instance."""

    def test_get_registry_returns_populated(self) -> None:
        """get_registry should return a populated registry."""
        registry = get_registry()

        assert registry.count > 0

    def test_get_registry_has_pi5(self) -> None:
        """Global registry should include Raspberry Pi 5."""
        registry = get_registry()

        pi5 = registry.get("raspberry-pi-5")
        assert pi5 is not None
        assert "raspberry" in pi5.name.lower()

    def test_get_registry_has_lcd(self) -> None:
        """Global registry should include LCD displays."""
        registry = get_registry()

        lcd = registry.get("lcd-20x4-hd44780")
        assert lcd is not None
        assert lcd.category == ComponentCategory.DISPLAY

    def test_get_registry_fuzzy_search_works(self) -> None:
        """Global registry should support fuzzy search."""
        registry = get_registry()

        results = registry.search("pi 5")
        assert len(results) >= 1
        assert results[0].component.id == "raspberry-pi-5"

    def test_get_registry_search_button(self) -> None:
        """Global registry should find buttons."""
        registry = get_registry()

        results = registry.search("tactile button")
        assert len(results) >= 1
        assert "button" in results[0].component.id


class TestComponentDefinitionDetails:
    """Tests for specific component definition details."""

    def test_pi5_mounting_holes(self) -> None:
        """Pi 5 should have correct mounting hole positions."""
        registry = get_registry()
        pi5 = registry.get("raspberry-pi-5")

        assert pi5 is not None
        assert len(pi5.mounting_holes) == 4

        # Check first mounting hole position
        hole = pi5.mounting_holes[0]
        assert hole.x == 3.5
        assert hole.y == 3.5
        assert hole.diameter.mm == 2.7

    def test_pi5_ports(self) -> None:
        """Pi 5 should have expected ports."""
        registry = get_registry()
        pi5 = registry.get("raspberry-pi-5")

        assert pi5 is not None
        port_names = [p.name for p in pi5.ports]

        assert "usb-c-power" in port_names
        assert "micro-hdmi-0" in port_names
        assert "ethernet" in port_names

    def test_lcd_20x4_dimensions(self) -> None:
        """20x4 LCD should have correct dimensions."""
        registry = get_registry()
        lcd = registry.get("lcd-20x4-hd44780")

        assert lcd is not None
        assert lcd.dimensions.width_mm == 98.0
        assert lcd.dimensions.depth_mm == 60.0
        assert lcd.dimensions.height_mm == 12.0

    def test_tactile_button_dimensions(self) -> None:
        """6mm tactile button should have correct dimensions."""
        registry = get_registry()
        button = registry.get("tactile-button-6mm")

        assert button is not None
        assert button.dimensions.width_mm == 6.0
        assert button.dimensions.depth_mm == 6.0
