"""
API package.

Provides REST API endpoints organized by version and domain.
"""

from app.api.v1 import api_router

__all__ = ["api_router"]
