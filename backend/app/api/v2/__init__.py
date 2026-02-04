"""
API v2 package - CAD v2 System.

Uses the new declarative schema + Build123d architecture.
Includes marketplace, lists, saves, and starters for community features.
"""

from fastapi import APIRouter

from app.api.v2.components import router as components_router
from app.api.v2.designs import router as designs_router
from app.api.v2.downloads import router as downloads_router
from app.api.v2.enclosures import router as enclosures_router
from app.api.v2.generate import router as generate_router
from app.api.v2.lists import router as lists_router
from app.api.v2.marketplace import router as marketplace_router
from app.api.v2.saves import router as saves_router
from app.api.v2.starters import router as starters_router

api_router = APIRouter(prefix="/api/v2")

# Include v2 routers
api_router.include_router(generate_router, prefix="/generate", tags=["v2-generate"])
api_router.include_router(designs_router, prefix="/designs", tags=["v2-designs"])
api_router.include_router(enclosures_router, prefix="/enclosures", tags=["v2-enclosures"])
api_router.include_router(components_router, prefix="/components", tags=["v2-components"])
api_router.include_router(downloads_router, prefix="/downloads", tags=["v2-downloads"])

# Community feature routers
api_router.include_router(marketplace_router, prefix="/marketplace", tags=["v2-marketplace"])
api_router.include_router(lists_router, prefix="/lists", tags=["v2-lists"])
api_router.include_router(saves_router, prefix="/saves", tags=["v2-saves"])
api_router.include_router(starters_router, prefix="/starters", tags=["v2-starters"])

__all__ = ["api_router"]
