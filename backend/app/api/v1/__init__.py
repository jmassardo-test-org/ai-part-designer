"""
API v1 package.

Aggregates all v1 route modules into a single router.
"""

from fastapi import APIRouter

from app.api.v1.abuse import router as abuse_router
from app.api.v1.admin import router as admin_router
from app.api.v1.alignment import router as alignment_router
from app.api.v1.annotations import router as annotations_router
from app.api.v1.assemblies import router as assemblies_router
from app.api.v1.auth import router as auth_router
from app.api.v1.bom import router as bom_router
from app.api.v1.comments import router as comments_router
from app.api.v1.components import library_router as library_router
from app.api.v1.components import router as components_router
from app.api.v1.contact import router as contact_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.designs import router as designs_router
from app.api.v1.drawings import router as drawings_router
from app.api.v1.enclosures import router as enclosures_router
from app.api.v1.exports import router as exports_router
from app.api.v1.extraction import router as extraction_router
from app.api.v1.files import router as files_router
from app.api.v1.generate import router as generate_router
from app.api.v1.health import router as health_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.layouts import router as layouts_router
from app.api.v1.mfa import router as mfa_router
from app.api.v1.moderation import router as moderation_router
from app.api.v1.modify import router as modify_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.oauth import router as oauth_router
from app.api.v1.onboarding import router as onboarding_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.projects import router as projects_router
from app.api.v1.ratings import router as ratings_router
from app.api.v1.refine import router as refine_router
from app.api.v1.shares import router as shares_router
from app.api.v1.subscriptions import router as subscriptions_router
from app.api.v1.teams import router as teams_router
from app.api.v1.template_comments import router as template_comments_router
from app.api.v1.templates import router as templates_router
from app.api.v1.trash import router as trash_router
from app.api.v1.usage import router as usage_router
from app.api.v1.versions import router as versions_router
from app.api.v1.webhooks import router as webhooks_router
from app.api.v1.ws import router as ws_router

api_router = APIRouter(prefix="/api/v1")

# Include all routers
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(generate_router, prefix="/generate", tags=["generate"])
api_router.include_router(templates_router, prefix="/templates", tags=["templates"])
api_router.include_router(jobs_router, prefix="/jobs", tags=["jobs"])
api_router.include_router(files_router, prefix="/files", tags=["files"])
api_router.include_router(modify_router, prefix="/cad", tags=["cad-modification"])
api_router.include_router(versions_router, tags=["version-history"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(trash_router, tags=["trash"])
api_router.include_router(shares_router, tags=["shares"])
api_router.include_router(comments_router, tags=["comments"])
api_router.include_router(projects_router, tags=["projects"])
api_router.include_router(dashboard_router, tags=["dashboard"])
api_router.include_router(assemblies_router, tags=["assemblies"])
api_router.include_router(bom_router, tags=["bom"])
api_router.include_router(components_router, tags=["components"])
api_router.include_router(library_router, tags=["component-library"])
api_router.include_router(abuse_router, tags=["admin-abuse"])
api_router.include_router(enclosures_router, tags=["enclosures"])
api_router.include_router(layouts_router, tags=["layouts"])
api_router.include_router(exports_router, prefix="/exports", tags=["data-export"])
api_router.include_router(conversations_router, prefix="/conversations", tags=["conversations"])
api_router.include_router(designs_router, tags=["designs"])
api_router.include_router(usage_router, prefix="/usage", tags=["usage-billing"])
api_router.include_router(organizations_router, tags=["organizations"])
api_router.include_router(annotations_router, tags=["annotations"])
api_router.include_router(notifications_router, tags=["notifications"])
api_router.include_router(refine_router, tags=["refine"])
api_router.include_router(drawings_router, tags=["drawings"])
api_router.include_router(subscriptions_router, tags=["subscriptions"])
api_router.include_router(webhooks_router, tags=["webhooks"])
api_router.include_router(oauth_router, prefix="/auth", tags=["oauth"])
api_router.include_router(mfa_router, prefix="/auth", tags=["mfa"])
api_router.include_router(onboarding_router, tags=["onboarding"])
api_router.include_router(ws_router, tags=["websocket"])
api_router.include_router(extraction_router, prefix="/extraction", tags=["extraction"])
api_router.include_router(alignment_router, prefix="/cad/align", tags=["cad-alignment"])
api_router.include_router(contact_router, tags=["contact"])
api_router.include_router(teams_router, tags=["teams"])
api_router.include_router(ratings_router, tags=["ratings"])
api_router.include_router(template_comments_router, tags=["template-comments"])
api_router.include_router(moderation_router, tags=["moderation"])

__all__ = ["api_router"]
