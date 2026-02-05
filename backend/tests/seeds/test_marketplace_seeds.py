"""
Tests for marketplace seed data.

Verifies that marketplace seed data is consistent and valid.
"""

from __future__ import annotations

from uuid import UUID

# =============================================================================
# Marketplace Seed Data Tests
# =============================================================================


class TestMarketplaceSeedIntegrity:
    """Tests for marketplace seed data integrity."""

    def test_design_lists_have_required_fields(self):
        """Verify all design lists have required fields."""
        from app.seeds.marketplace import SAMPLE_DESIGN_LISTS

        required_fields = ["name", "description", "icon", "color"]

        for design_list in SAMPLE_DESIGN_LISTS:
            for field in required_fields:
                assert field in design_list, (
                    f"Design list '{design_list.get('name', 'unknown')}' missing field: {field}"
                )

    def test_design_list_names_are_unique(self):
        """Verify all design list names are unique."""
        from app.seeds.marketplace import SAMPLE_DESIGN_LISTS

        names = [dl.get("name") for dl in SAMPLE_DESIGN_LISTS if dl.get("name")]
        unique_names = set(names)

        assert len(names) == len(unique_names), "Duplicate names found in design lists"

    def test_design_list_colors_are_valid_hex(self):
        """Verify all design list colors are valid hex codes."""
        import re

        from app.seeds.marketplace import SAMPLE_DESIGN_LISTS

        hex_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")

        for design_list in SAMPLE_DESIGN_LISTS:
            color = design_list.get("color", "")
            assert hex_pattern.match(color), (
                f"Design list '{design_list.get('name')}' has invalid color: {color}"
            )

    def test_sample_files_have_required_fields(self):
        """Verify all sample files have required fields."""
        from app.seeds.marketplace import SAMPLE_FILES

        required_fields = [
            "filename",
            "original_filename",
            "mime_type",
            "size_bytes",
            "file_type",
            "status",
        ]

        for file_data in SAMPLE_FILES:
            for field in required_fields:
                assert field in file_data, (
                    f"File '{file_data.get('filename', 'unknown')}' missing field: {field}"
                )

    def test_sample_files_have_valid_types(self):
        """Verify all sample files have valid file types."""
        from app.seeds.marketplace import SAMPLE_FILES

        valid_types = ["cad", "image", "document", "other"]

        for file_data in SAMPLE_FILES:
            file_type = file_data.get("file_type")
            assert file_type in valid_types, (
                f"File '{file_data.get('filename')}' has invalid file_type: {file_type}"
            )

    def test_cad_files_have_cad_format(self):
        """Verify all CAD files have a cad_format specified."""
        from app.seeds.marketplace import SAMPLE_FILES

        valid_cad_formats = ["step", "stl", "iges", "obj", "3mf"]

        for file_data in SAMPLE_FILES:
            if file_data.get("file_type") == "cad":
                cad_format = file_data.get("cad_format")
                assert cad_format is not None, (
                    f"CAD file '{file_data.get('filename')}' missing cad_format"
                )
                assert cad_format in valid_cad_formats, (
                    f"CAD file '{file_data.get('filename')}' has invalid cad_format: {cad_format}"
                )

    def test_cad_files_have_geometry_info(self):
        """Verify all CAD files have geometry info."""
        from app.seeds.marketplace import SAMPLE_FILES

        for file_data in SAMPLE_FILES:
            if file_data.get("file_type") == "cad":
                geometry = file_data.get("geometry_info")
                assert geometry is not None, (
                    f"CAD file '{file_data.get('filename')}' missing geometry_info"
                )
                assert "bounding_box" in geometry, (
                    f"CAD file '{file_data.get('filename')}' geometry missing bounding_box"
                )

    def test_seed_marketplace_function_exists(self):
        """Verify seed_marketplace function is callable."""
        from app.seeds.marketplace import seed_marketplace

        assert callable(seed_marketplace), "seed_marketplace should be callable"


# =============================================================================
# Example Projects Seed Tests
# =============================================================================


class TestExamplesSeedIntegrity:
    """Tests for example projects seed data integrity."""

    def test_example_projects_have_required_fields(self):
        """Verify all example projects have required fields."""
        from app.seeds.examples import EXAMPLE_PROJECTS

        required_fields = ["id", "name", "description"]

        for project in EXAMPLE_PROJECTS:
            for field in required_fields:
                assert field in project, (
                    f"Project '{project.get('name', 'unknown')}' missing field: {field}"
                )

    def test_example_project_ids_are_valid_uuids(self):
        """Verify all example project IDs are valid UUID strings."""
        from app.seeds.examples import EXAMPLE_PROJECTS

        for project in EXAMPLE_PROJECTS:
            project_id = project.get("id")
            assert project_id is not None, f"Project '{project.get('name')}' has no id"
            # Should be a valid UUID string format
            UUID(project_id)  # Will raise if invalid

    def test_example_project_ids_are_unique(self):
        """Verify all example project IDs are unique."""
        from app.seeds.examples import EXAMPLE_PROJECTS

        ids = [p.get("id") for p in EXAMPLE_PROJECTS if p.get("id")]
        unique_ids = set(ids)

        assert len(ids) == len(unique_ids), "Duplicate IDs found in example projects"

    def test_example_projects_have_designs(self):
        """Verify all example projects have at least one design."""
        from app.seeds.examples import EXAMPLE_PROJECTS

        for project in EXAMPLE_PROJECTS:
            designs = project.get("designs", [])
            assert len(designs) > 0, f"Project '{project.get('name')}' has no designs"

    def test_example_designs_have_required_fields(self):
        """Verify all example designs have required fields."""
        from app.seeds.examples import EXAMPLE_PROJECTS

        required_fields = ["name"]

        for project in EXAMPLE_PROJECTS:
            for design in project.get("designs", []):
                for field in required_fields:
                    assert field in design, (
                        f"Design in '{project.get('name')}' missing field: {field}"
                    )

    def test_seed_example_projects_function_exists(self):
        """Verify seed_example_projects function is callable."""
        from app.seeds.examples import seed_example_projects

        assert callable(seed_example_projects), "seed_example_projects should be callable"

    def test_copy_example_project_function_exists(self):
        """Verify copy_example_project function is callable."""
        from app.seeds.examples import copy_example_project

        assert callable(copy_example_project), "copy_example_project should be callable"


# =============================================================================
# Starter Designs Seed Tests
# =============================================================================


class TestStartersSeedIntegrity:
    """Tests for starter designs seed data integrity."""

    def test_starter_designs_have_required_fields(self):
        """Verify all starter designs have required fields."""
        from app.seeds.starters import STARTER_DESIGNS

        required_fields = ["id", "name", "description", "category", "tags"]

        for starter in STARTER_DESIGNS:
            for field in required_fields:
                assert field in starter, (
                    f"Starter '{starter.get('name', 'unknown')}' missing field: {field}"
                )

    def test_starter_ids_are_valid_uuids(self):
        """Verify all starter IDs are valid UUIDs."""
        from app.seeds.starters import STARTER_DESIGNS

        for starter in STARTER_DESIGNS:
            starter_id = starter.get("id")
            assert isinstance(starter_id, UUID), (
                f"Starter '{starter.get('name')}' id should be a UUID"
            )

    def test_starter_ids_are_unique(self):
        """Verify all starter IDs are unique."""
        from app.seeds.starters import STARTER_DESIGNS

        ids = [s.get("id") for s in STARTER_DESIGNS if s.get("id")]
        unique_ids = set(ids)

        assert len(ids) == len(unique_ids), "Duplicate IDs found in starter designs"

    def test_starters_have_enclosure_specs(self):
        """Verify all starters have enclosure specifications."""
        from app.seeds.starters import STARTER_DESIGNS

        for starter in STARTER_DESIGNS:
            spec = starter.get("enclosure_spec")
            assert spec is not None, f"Starter '{starter.get('name')}' missing enclosure_spec"

    def test_enclosure_specs_have_exterior_dimensions(self):
        """Verify all enclosure specs have exterior dimensions."""
        from app.seeds.starters import STARTER_DESIGNS

        for starter in STARTER_DESIGNS:
            spec = starter.get("enclosure_spec", {})
            exterior = spec.get("exterior")
            assert exterior is not None, (
                f"Starter '{starter.get('name')}' enclosure_spec missing exterior"
            )

            for dim in ["width", "depth", "height"]:
                assert dim in exterior, f"Starter '{starter.get('name')}' exterior missing {dim}"

    def test_seed_starters_function_exists(self):
        """Verify seed_starters function is callable."""
        from app.seeds.starters import seed_starters

        assert callable(seed_starters), "seed_starters should be callable"


# =============================================================================
# Components V2 Seed Tests
# =============================================================================


class TestComponentsV2SeedIntegrity:
    """Tests for CAD v2 components seed data integrity."""

    def test_seed_components_v2_function_exists(self):
        """Verify seed_components_v2 function is callable."""
        from app.seeds.components_v2 import seed_components_v2

        assert callable(seed_components_v2), "seed_components_v2 should be callable"

    def test_component_to_dict_function_exists(self):
        """Verify component_to_dict function is callable."""
        from app.seeds.components_v2 import component_to_dict

        assert callable(component_to_dict), "component_to_dict should be callable"
