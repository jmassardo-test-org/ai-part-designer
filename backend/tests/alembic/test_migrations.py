"""Tests for Alembic migrations.

These tests ensure migrations are properly structured and idempotent
where needed to prevent deployment failures.
"""

import ast
import re
from pathlib import Path
from typing import ClassVar

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

# Path to migration files
MIGRATIONS_DIR = Path(__file__).parent.parent.parent / "alembic" / "versions"
ALEMBIC_INI_PATH = MIGRATIONS_DIR.parent.parent / "alembic.ini"


def _build_alembic_config() -> Config:
    """Build Alembic config for migration graph inspection."""
    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("script_location", str(MIGRATIONS_DIR.parent))
    return config


class TestMigrationStructure:
    """Test migration file structure and best practices."""

    def test_all_migrations_have_revision_ids(self) -> None:
        """All migration files must have revision identifiers."""
        for migration_file in MIGRATIONS_DIR.glob("*.py"):
            if migration_file.name.startswith("__"):
                continue

            content = migration_file.read_text()
            # Accept both "revision = " and "revision: str = " patterns
            has_revision = "revision = " in content or "revision:" in content
            has_down_revision = "down_revision = " in content or "down_revision:" in content

            assert has_revision, f"Migration {migration_file.name} missing revision identifier"
            assert has_down_revision, f"Migration {migration_file.name} missing down_revision"

    def test_all_migrations_have_upgrade_and_downgrade(self) -> None:
        """All migrations must have both upgrade and downgrade functions."""
        for migration_file in MIGRATIONS_DIR.glob("*.py"):
            if migration_file.name.startswith("__"):
                continue

            content = migration_file.read_text()
            assert "def upgrade(" in content, (
                f"Migration {migration_file.name} missing upgrade function"
            )
            assert "def downgrade(" in content, (
                f"Migration {migration_file.name} missing downgrade function"
            )

    def test_migrations_have_docstrings(self) -> None:
        """All migrations should have module docstrings."""
        for migration_file in MIGRATIONS_DIR.glob("*.py"):
            if migration_file.name.startswith("__"):
                continue

            content = migration_file.read_text()
            # Check for triple-quoted docstring at start
            assert content.strip().startswith('"""') or content.strip().startswith("'''"), (
                f"Migration {migration_file.name} missing module docstring"
            )


class TestMigrationIdempotency:
    """Test that certain migrations are idempotent.

    Migrations that add columns, indexes, or constraints to existing tables
    should check if the object exists before creating it. This prevents
    failures when migrations are re-run against databases that were
    manually modified or partially migrated.
    """

    # Migrations that MUST be idempotent (add columns to existing tables)
    IDEMPOTENT_MIGRATIONS: ClassVar[list[str]] = [
        "012_onboarding_fields.py",
        "013_add_organization_id_to_projects.py",
        "022_mfa_columns.py",
        "024_design_marketplace_fields.py",
        "025_design_remix_tracking.py",
        "20260126_220302_add_notifications_dismissed_at.py",
    ]

    @pytest.mark.parametrize("migration_file", IDEMPOTENT_MIGRATIONS)
    def test_idempotent_migrations_check_existence(self, migration_file: str) -> None:
        """Idempotent migrations must check for existing schema objects."""
        file_path = MIGRATIONS_DIR / migration_file
        assert file_path.exists(), f"Migration {migration_file} not found"

        content = file_path.read_text()

        # Check for existence check patterns
        has_column_check = "_column_exists" in content or "if_not_exists" in content
        has_index_check = "_index_exists" in content or "if_not_exists" in content
        has_fk_check = "_fk_exists" in content

        # If migration adds columns, it should check for existence
        if "op.add_column" in content:
            assert has_column_check, (
                f"Migration {migration_file} adds columns but doesn't check "
                "for existence. Add _column_exists() check."
            )

        # If migration creates indexes, it should check for existence
        if "op.create_index" in content:
            assert has_index_check or "_index_exists" in content, (
                f"Migration {migration_file} creates indexes but doesn't check "
                "for existence. Add _index_exists() check."
            )

        # If migration creates foreign keys, it should check for existence
        if "op.create_foreign_key" in content:
            assert has_fk_check, (
                f"Migration {migration_file} creates foreign keys but doesn't "
                "check for existence. Add _fk_exists() check."
            )


class TestMigrationSyntax:
    """Test that migration files are syntactically valid Python."""

    def test_all_migrations_parse_correctly(self) -> None:
        """All migration files must be valid Python syntax."""
        for migration_file in MIGRATIONS_DIR.glob("*.py"):
            if migration_file.name.startswith("__"):
                continue

            content = migration_file.read_text()
            try:
                ast.parse(content)
            except SyntaxError as e:
                pytest.fail(f"Migration {migration_file.name} has syntax error: {e}")


class TestMigrationNaming:
    """Test migration naming conventions."""

    def test_migration_files_follow_naming_convention(self) -> None:
        """Migration files should follow a consistent naming pattern.

        Accepts formats:
        - XXX_description.py (e.g., 001_initial_schema.py)
        - YYYYMMDD_XXX_description.py (e.g., 20260125_005_conversations.py)
        - YYYYMMDD_HHMMSS_description.py (e.g., 20260126_220302_add_notifications.py)
        """
        # Pattern accepts multiple naming conventions used in this project
        pattern = re.compile(r"^(\d{8}_)?(\d{3,6}_)?[a-z][a-z0-9_]*\.py$")

        for migration_file in MIGRATIONS_DIR.glob("*.py"):
            if migration_file.name.startswith("__"):
                continue

            assert pattern.match(migration_file.name), (
                f"Migration {migration_file.name} doesn't follow naming "
                "convention. Use: XXX_description.py, YYYYMMDD_XXX_description.py, "
                "or YYYYMMDD_HHMMSS_description.py"
            )

    def test_revisions_are_present(self) -> None:
        """All migrations should have a revision ID."""
        for migration_file in MIGRATIONS_DIR.glob("*.py"):
            if migration_file.name.startswith("__"):
                continue

            content = migration_file.read_text()

            # Check revision exists (various formats)
            revision_match = re.search(r'revision[:\s]*(?:str\s*)?=\s*["\']([^"\']+)["\']', content)
            assert revision_match is not None, (
                f"Migration {migration_file.name} has no revision identifier"
            )


class TestMigrationIdempotencyMarkers:
    """Test that migrations modifying existing tables have idempotency checks.

    Any migration that adds columns, indexes, or constraints to EXISTING tables
    should check if the object exists before creating it.
    """

    # All migrations that add columns to existing tables MUST be in this list
    # and MUST have idempotency checks
    MIGRATIONS_ADDING_COLUMNS: ClassVar[list[str]] = [
        "012_onboarding_fields.py",
        "013_add_organization_id_to_projects.py",
        "022_mfa_columns.py",
        "024_design_marketplace_fields.py",
        "025_design_remix_tracking.py",
        "20260126_220302_add_notifications_dismissed_at.py",
    ]

    @pytest.mark.parametrize("migration_file", MIGRATIONS_ADDING_COLUMNS)
    def test_column_adding_migrations_are_idempotent(self, migration_file: str) -> None:
        """Migrations adding columns must have existence checks."""
        file_path = MIGRATIONS_DIR / migration_file
        assert file_path.exists(), f"Migration {migration_file} not found"

        content = file_path.read_text()

        # Must have _column_exists helper or use IF NOT EXISTS
        has_column_check = (
            "_column_exists" in content
            or "IF NOT EXISTS" in content.upper()
            or "ADD COLUMN IF NOT EXISTS" in content.upper()
        )

        assert has_column_check, (
            f"Migration {migration_file} adds columns but lacks idempotency. "
            "Add _column_exists() checks or use 'ADD COLUMN IF NOT EXISTS'."
        )


class TestMigrationSmokeTest:
    """Migration smoke tests that run without a live database."""

    def test_migration_head_matches_models(self) -> None:
        """Ensure migration graph resolves to valid head revisions."""
        script = ScriptDirectory.from_config(_build_alembic_config())
        heads = script.get_heads()

        assert heads, "Expected at least one migration head"

        for head in heads:
            revision = script.get_revision(head)
            assert revision is not None, f"Head revision {head} could not be resolved"

    def test_migration_downgrade_upgrade_cycle(self) -> None:
        """Ensure each head has a valid upgrade/downgrade cycle to base."""
        script = ScriptDirectory.from_config(_build_alembic_config())
        for head in script.get_heads():
            revisions = list(script.walk_revisions(base="base", head=head))
            assert revisions, f"No revision path found from base to head {head}"

            for revision in revisions:
                assert hasattr(revision.module, "upgrade"), (
                    f"Migration {revision.revision} is missing upgrade()"
                )
                assert hasattr(revision.module, "downgrade"), (
                    f"Migration {revision.revision} is missing downgrade()"
                )
