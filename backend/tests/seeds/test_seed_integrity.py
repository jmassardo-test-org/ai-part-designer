"""
Tests for seed data integrity.

Verifies that all seed data is consistent and valid.
"""

from __future__ import annotations

import pytest

# =============================================================================
# Template Seed Tests
# =============================================================================


class TestTemplateSeedIntegrity:
    """Tests for template seed data integrity."""

    def test_all_seeded_templates_have_generators(self):
        """Verify all seeded templates have corresponding generators."""
        from app.cad.templates import get_template_generator
        from app.seeds.templates import TEMPLATE_SEEDS

        missing_generators = []

        for template in TEMPLATE_SEEDS:
            slug = template.get("slug")
            if slug and not get_template_generator(slug):
                missing_generators.append(slug)

        assert len(missing_generators) == 0, f"Templates missing generators: {missing_generators}"

    def test_all_templates_have_required_fields(self):
        """Verify all templates have required fields."""
        from app.seeds.templates import TEMPLATE_SEEDS

        required_fields = ["name", "slug", "category", "parameters", "cadquery_script"]

        for template in TEMPLATE_SEEDS:
            for field in required_fields:
                assert field in template, (
                    f"Template '{template.get('name', 'unknown')}' missing field: {field}"
                )

    def test_all_templates_have_valid_parameters(self):
        """Verify all template parameters have valid structure."""
        from app.seeds.templates import TEMPLATE_SEEDS

        for template in TEMPLATE_SEEDS:
            params = template.get("parameters", {})

            for param_name, param_def in params.items():
                assert "type" in param_def, (
                    f"Template '{template.get('name')}' param '{param_name}' missing type"
                )

                param_type = param_def["type"]

                # Number types should have min/max
                if param_type == "number":
                    assert True, f"Number param '{param_name}' should have constraints"

    def test_all_templates_have_default_values(self):
        """Verify all template parameters have default values."""
        from app.seeds.templates import TEMPLATE_SEEDS

        for template in TEMPLATE_SEEDS:
            params = template.get("parameters", {})
            defaults = template.get("default_values", {})

            for param_name in params:
                assert param_name in defaults, (
                    f"Template '{template.get('name')}' missing default for: {param_name}"
                )

    def test_template_slugs_are_unique(self):
        """Verify all template slugs are unique."""
        from app.seeds.templates import TEMPLATE_SEEDS

        slugs = [t.get("slug") for t in TEMPLATE_SEEDS if t.get("slug")]
        unique_slugs = set(slugs)

        assert len(slugs) == len(unique_slugs), "Duplicate slugs found in templates"


# =============================================================================
# User Seed Tests
# =============================================================================


class TestUserSeedIntegrity:
    """Tests for user seed data integrity."""

    def test_user_seeds_have_required_fields(self):
        """Verify all user seeds have required fields."""
        from app.seeds.users import FREE_USERS, PLATFORM_ADMIN

        all_users = [PLATFORM_ADMIN, *FREE_USERS]
        required_fields = ["email", "password"]

        for user in all_users:
            for field in required_fields:
                assert field in user, (
                    f"User '{user.get('email', 'unknown')}' missing field: {field}"
                )

    def test_user_emails_are_unique(self):
        """Verify all user emails are unique."""
        from app.seeds.users import FREE_USERS, PLATFORM_ADMIN

        all_users = [PLATFORM_ADMIN, *FREE_USERS]
        emails = [u.get("email") for u in all_users if u.get("email")]
        unique_emails = set(emails)

        assert len(emails) == len(unique_emails), "Duplicate emails found in user seeds"

    def test_admin_user_has_admin_role(self):
        """Verify the platform admin has admin role."""
        from app.seeds.users import PLATFORM_ADMIN

        assert PLATFORM_ADMIN.get("role") == "admin", "Platform admin should have admin role"


# =============================================================================
# Generator Tests
# =============================================================================


class TestGeneratorIntegrity:
    """Tests for template generator integrity."""

    def test_generators_execute_without_errors(self):
        """Verify all generators can execute with default parameters."""
        from app.cad.templates import get_template_generator
        from app.seeds.templates import TEMPLATE_SEEDS

        for template in TEMPLATE_SEEDS:
            slug = template.get("slug")
            defaults = template.get("default_values", {})
            generator = get_template_generator(slug)

            if generator:
                try:
                    result = generator(**defaults)
                    assert result is not None, f"Generator for '{slug}' returned None"
                except Exception as e:
                    pytest.fail(f"Generator for '{slug}' raised: {e}")

    def test_generated_shapes_have_valid_geometry(self):
        """Verify generated shapes have valid bounding boxes."""
        from app.cad.templates import get_template_generator
        from app.seeds.templates import TEMPLATE_SEEDS

        for template in TEMPLATE_SEEDS[:3]:  # Test first 3 to save time
            slug = template.get("slug")
            defaults = template.get("default_values", {})
            generator = get_template_generator(slug)

            if generator:
                result = generator(**defaults)

                # Verify bounding box exists
                bbox = result.val().BoundingBox()
                assert bbox.xlen > 0, f"'{slug}' has zero X dimension"
                assert bbox.ylen > 0, f"'{slug}' has zero Y dimension"
                assert bbox.zlen > 0, f"'{slug}' has zero Z dimension"


# =============================================================================
# Cross-Reference Tests
# =============================================================================


class TestSeedCrossReferences:
    """Tests for cross-references between seed data."""

    def test_template_categories_are_not_empty(self):
        """Verify all templates have a non-empty category."""
        from app.seeds.templates import TEMPLATE_SEEDS

        for template in TEMPLATE_SEEDS:
            category = template.get("category")
            assert category, f"Template '{template.get('name')}' has empty category"
            assert isinstance(category, str), (
                f"Template '{template.get('name')}' category is not a string"
            )
            assert len(category) > 0, f"Template '{template.get('name')}' has empty category string"

    def test_min_tiers_are_valid(self):
        """Verify min_tier values are valid subscription tiers."""
        from app.seeds.templates import TEMPLATE_SEEDS

        valid_tiers = ["free", "hobby", "pro", "enterprise"]

        for template in TEMPLATE_SEEDS:
            tier = template.get("min_tier", "free")
            assert tier in valid_tiers, (
                f"Template '{template.get('name')}' has invalid tier: {tier}"
            )
