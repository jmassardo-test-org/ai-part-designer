"""
OCP Compatibility Layer.

This module patches OCP 7.9.x compatibility issues with Build123d.

OCP 7.9.x removed the HashCode() method from TopoDS_Shape in favor of
the Python standard __hash__ method. However, Build123d still uses
HashCode() internally for edge/face enumeration.

This module provides a compatibility shim that adds HashCode() back
by delegating to the native __hash__() method.

IMPORTANT: This module must be imported before any build123d usage.
It is automatically imported by the app.cad package __init__.py.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_patched = False


def apply_ocp_compat_patch() -> bool:
    """
    Apply the OCP compatibility patch.

    Adds HashCode() method to TopoDS_Shape if not present, mapping
    it to the __hash__() method that exists in OCP 7.9.x.

    This is idempotent - calling multiple times has no effect.

    Returns:
        True if patch was applied, False if already patched or not needed.
    """
    global _patched

    if _patched:
        return False

    try:
        from OCP.TopoDS import TopoDS_Shape

        # Check if HashCode already exists
        if hasattr(TopoDS_Shape, "HashCode") and callable(getattr(TopoDS_Shape, "HashCode", None)):
            logger.debug("OCP TopoDS_Shape.HashCode() already exists, no patch needed")
            _patched = True
            return False

        # Check if __hash__ exists (required for our patch)
        if not hasattr(TopoDS_Shape, "__hash__"):
            logger.warning("OCP TopoDS_Shape has no __hash__ method, cannot patch")
            return False

        # Define the compatibility shim
        def _hash_code_compat(self: TopoDS_Shape, upper_bound: int = 2147483647) -> int:
            """
            Compatibility shim for HashCode().

            Maps to Python's __hash__() and applies modulo for upper_bound.

            Args:
                upper_bound: Maximum hash value (default matches OCCT convention)

            Returns:
                Integer hash code in range [0, upper_bound)
            """
            return hash(self) % upper_bound

        # Apply the patch
        TopoDS_Shape.HashCode = _hash_code_compat
        _patched = True

        logger.info("Applied OCP 7.9.x compatibility patch: TopoDS_Shape.HashCode()")
        return True

    except ImportError as e:
        logger.error(f"Failed to import OCP for compatibility patch: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to apply OCP compatibility patch: {e}")
        return False


def is_patched() -> bool:
    """Check if the compatibility patch has been applied."""
    return _patched


# Auto-apply patch on module import
apply_ocp_compat_patch()
