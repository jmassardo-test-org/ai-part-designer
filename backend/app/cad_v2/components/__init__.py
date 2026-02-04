# CAD v2 Component Library
#
# Pre-defined component definitions with accurate dimensions,
# mounting patterns, and port locations.

from app.cad_v2.components.registry import ComponentRegistry, get_registry

__all__ = [
    "ComponentRegistry",
    "get_registry",
]
