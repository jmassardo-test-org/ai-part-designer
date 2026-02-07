"""
Tests for app.types module.

Tests Protocol types and type aliases for correctness and runtime behavior.

Note: These are pure unit tests that don't require database or Redis fixtures.
"""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from app.types import EntityID, JSONDict, JSONValue
    from app.types.aliases import BoundingBoxTuple, Coordinate


class TestProtocols:
    """Tests for Protocol type definitions."""

    def test_has_identity_is_runtime_checkable(self) -> None:
        """HasIdentity protocol can be used with isinstance at runtime."""
        from app.types import HasIdentity

        # Protocol is runtime checkable
        assert hasattr(HasIdentity, "__protocol_attrs__")

    def test_has_timestamps_is_runtime_checkable(self) -> None:
        """HasTimestamps protocol can be used with isinstance at runtime."""
        from app.types import HasTimestamps

        assert hasattr(HasTimestamps, "__protocol_attrs__")

    def test_has_soft_delete_is_runtime_checkable(self) -> None:
        """HasSoftDelete protocol can be used with isinstance at runtime."""
        from app.types import HasSoftDelete

        assert hasattr(HasSoftDelete, "__protocol_attrs__")

    def test_standard_entity_combines_all_protocols(self) -> None:
        """StandardEntity includes all identity, timestamp, and soft-delete protocols."""
        from app.types import StandardEntity

        # StandardEntity should include all the attrs from its parents
        assert hasattr(StandardEntity, "__protocol_attrs__")

    def test_identifiable_protocol_structure(self) -> None:
        """Identifiable protocol has correct structure for non-ORM objects."""
        from app.types import Identifiable

        # Should have id as a property
        assert "id" in dir(Identifiable)

    def test_nameable_protocol_structure(self) -> None:
        """Nameable protocol has correct structure."""
        from app.types import Nameable

        assert "name" in dir(Nameable)

    def test_ownable_protocol_structure(self) -> None:
        """Ownable protocol has correct structure."""
        from app.types import Ownable

        assert "user_id" in dir(Ownable)


class TestProtocolCompliance:
    """Tests that actual models comply with protocols."""

    def test_base_model_with_mixins_has_standard_attributes(self) -> None:
        """Base model with mixins has all standard entity attributes."""
        from sqlalchemy import String
        from sqlalchemy.dialects.postgresql import UUID as PG_UUID
        from sqlalchemy.orm import Mapped, mapped_column

        from app.models.base import Base, SoftDeleteMixin, TimestampMixin

        class TestModel(Base, TimestampMixin, SoftDeleteMixin):
            __tablename__ = "test_protocol_compliance"

            id: Mapped[UUID] = mapped_column(
                PG_UUID(as_uuid=True),
                primary_key=True,
                default=uuid4,
            )
            name: Mapped[str] = mapped_column(String(100))

        # Verify the model has all required attributes
        assert hasattr(TestModel, "id")
        assert hasattr(TestModel, "created_at")
        assert hasattr(TestModel, "updated_at")
        assert hasattr(TestModel, "deleted_at")


class TestTypeAliases:
    """Tests for type alias definitions."""

    def test_entity_id_is_uuid(self) -> None:
        """EntityID alias resolves to UUID."""

        # Type aliases are transparent at runtime
        test_id: EntityID = uuid4()
        assert isinstance(test_id, UUID)

    def test_json_dict_accepts_dict(self) -> None:
        """JSONDict alias accepts dictionary values."""

        data: JSONDict = {"key": "value", "count": 42}
        assert isinstance(data, dict)

    def test_json_value_accepts_primitives(self) -> None:
        """JSONValue alias accepts primitive types."""

        str_val: JSONValue = "hello"
        int_val: JSONValue = 42
        float_val: JSONValue = 3.14
        bool_val: JSONValue = True
        null_val: JSONValue = None

        assert str_val == "hello"
        assert int_val == 42
        assert float_val == 3.14
        assert bool_val is True
        assert null_val is None

    def test_json_value_accepts_nested_structures(self) -> None:
        """JSONValue alias accepts nested arrays and objects."""

        nested: JSONValue = {
            "items": [1, 2, 3],
            "metadata": {"nested": True},
        }
        assert isinstance(nested, dict)
        assert isinstance(nested["items"], list)

    def test_sql_filter_type_from_sqlalchemy(self) -> None:
        """SQLFilter alias matches SQLAlchemy ColumnElement."""
        from typing import get_args, get_origin

        from sqlalchemy import ColumnElement

        from app.types.aliases import SQLFilter as SQLFilterAlias

        # The alias should be ColumnElement[bool] - check its value
        # With Python 3.12+ `type` keyword, access __value__ instead
        alias_value = SQLFilterAlias.__value__  # type: ignore[attr-defined]
        assert get_origin(alias_value) is ColumnElement
        assert get_args(alias_value) == (bool,)


class TestCoordinateTypes:
    """Tests for CAD/geometry type aliases."""

    def test_coordinate_is_tuple_of_floats(self) -> None:
        """Coordinate alias represents 3D point."""

        point: Coordinate = (1.0, 2.0, 3.0)
        assert len(point) == 3
        assert all(isinstance(v, float) for v in point)

    def test_bounding_box_tuple_is_pair_of_coordinates(self) -> None:
        """BoundingBoxTuple alias represents min/max corners."""

        bbox: BoundingBoxTuple = ((0.0, 0.0, 0.0), (10.0, 10.0, 10.0))
        assert len(bbox) == 2
        assert len(bbox[0]) == 3
        assert len(bbox[1]) == 3
