"""
Dashboard API endpoints.

Provides aggregated data for the user dashboard including:
- Recent designs
- Usage statistics
- Activity summary
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.design import Design
from app.models.job import Job


router = APIRouter()


# =============================================================================
# Response Schemas
# =============================================================================

class DashboardStats(BaseModel):
    """User dashboard statistics."""
    total_projects: int = Field(description="Total number of projects")
    total_designs: int = Field(description="Total number of designs")
    designs_this_month: int = Field(description="Designs created this month")
    generations_this_month: int = Field(description="AI generations this month")
    exports_this_month: int = Field(description="Exports this month")


class RecentDesign(BaseModel):
    """Brief design info for dashboard."""
    id: str
    name: str
    project_id: str
    project_name: str
    thumbnail_url: Optional[str]
    source_type: str
    status: str
    created_at: str
    updated_at: str


class RecentActivity(BaseModel):
    """Activity item for dashboard."""
    id: str
    type: str  # design_created, design_exported, project_created, etc.
    title: str
    description: str
    timestamp: str
    metadata: dict = Field(default_factory=dict)


class DashboardResponse(BaseModel):
    """Complete dashboard data response."""
    stats: DashboardStats
    recent_designs: list[RecentDesign]
    recent_activity: list[RecentActivity]


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    """
    Get dashboard data for the current user.
    
    Returns aggregated statistics, recent designs, and activity.
    """
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Get project count
    project_count_query = (
        select(func.count())
        .where(Project.user_id == current_user.id)
        .where(Project.deleted_at.is_(None))
    )
    project_count_result = await db.execute(project_count_query)
    total_projects = project_count_result.scalar() or 0
    
    # Get design count
    design_count_query = (
        select(func.count())
        .select_from(Design)
        .join(Project, Design.project_id == Project.id)
        .where(Project.user_id == current_user.id)
        .where(Design.deleted_at.is_(None))
    )
    design_count_result = await db.execute(design_count_query)
    total_designs = design_count_result.scalar() or 0
    
    # Get designs created this month
    designs_month_query = (
        select(func.count())
        .select_from(Design)
        .join(Project, Design.project_id == Project.id)
        .where(Project.user_id == current_user.id)
        .where(Design.deleted_at.is_(None))
        .where(Design.created_at >= month_start)
    )
    designs_month_result = await db.execute(designs_month_query)
    designs_this_month = designs_month_result.scalar() or 0
    
    # Get AI generations this month
    generations_query = (
        select(func.count())
        .where(Job.user_id == current_user.id)
        .where(Job.job_type == "ai_generation")
        .where(Job.status == "completed")
        .where(Job.created_at >= month_start)
    )
    generations_result = await db.execute(generations_query)
    generations_this_month = generations_result.scalar() or 0
    
    # Get exports this month
    exports_query = (
        select(func.count())
        .where(Job.user_id == current_user.id)
        .where(Job.job_type.in_(["export", "format_conversion"]))
        .where(Job.status == "completed")
        .where(Job.created_at >= month_start)
    )
    exports_result = await db.execute(exports_query)
    exports_this_month = exports_result.scalar() or 0
    
    stats = DashboardStats(
        total_projects=total_projects,
        total_designs=total_designs,
        designs_this_month=designs_this_month,
        generations_this_month=generations_this_month,
        exports_this_month=exports_this_month,
    )
    
    # Get recent designs
    recent_designs_query = (
        select(Design, Project.name.label("project_name"))
        .join(Project, Design.project_id == Project.id)
        .where(Project.user_id == current_user.id)
        .where(Design.deleted_at.is_(None))
        .order_by(Design.updated_at.desc())
        .limit(5)
    )
    recent_designs_result = await db.execute(recent_designs_query)
    recent_designs_rows = recent_designs_result.all()
    
    recent_designs = []
    for row in recent_designs_rows:
        design = row[0]
        project_name = row[1]
        thumbnail_url = None
        if design.extra_data:
            thumbnail_url = design.extra_data.get("thumbnail_url")
        
        recent_designs.append(RecentDesign(
            id=str(design.id),
            name=design.name,
            project_id=str(design.project_id),
            project_name=project_name,
            thumbnail_url=thumbnail_url,
            source_type=design.source_type,
            status=design.status,
            created_at=design.created_at.isoformat(),
            updated_at=design.updated_at.isoformat(),
        ))
    
    # Build recent activity from various sources
    recent_activity = []
    
    # Recent designs as activity
    for design in recent_designs[:3]:
        recent_activity.append(RecentActivity(
            id=f"design-{design.id}",
            type="design_created" if design.source_type == "ai_generated" else "design_updated",
            title=design.name,
            description=f"{'Generated' if design.source_type == 'ai_generated' else 'Updated'} in {design.project_name}",
            timestamp=design.updated_at,
            metadata={"design_id": design.id, "project_id": design.project_id},
        ))
    
    # Recent completed jobs as activity
    recent_jobs_query = (
        select(Job)
        .where(Job.user_id == current_user.id)
        .where(Job.status == "completed")
        .order_by(Job.completed_at.desc())
        .limit(5)
    )
    recent_jobs_result = await db.execute(recent_jobs_query)
    recent_jobs = recent_jobs_result.scalars().all()
    
    for job in recent_jobs:
        if job.job_type == "ai_generation":
            activity_type = "generation_completed"
            title = "AI Generation Completed"
            description = "Generated a new 3D model"
        elif job.job_type in ("export", "format_conversion"):
            activity_type = "export_completed"
            title = "Export Completed"
            description = f"Exported to {job.input_params.get('format', 'file')}"
        else:
            continue
        
        recent_activity.append(RecentActivity(
            id=f"job-{job.id}",
            type=activity_type,
            title=title,
            description=description,
            timestamp=job.completed_at.isoformat() if job.completed_at else job.created_at.isoformat(),
            metadata={"job_id": str(job.id)},
        ))
    
    # Sort activity by timestamp and limit
    recent_activity.sort(key=lambda a: a.timestamp, reverse=True)
    recent_activity = recent_activity[:10]
    
    return DashboardResponse(
        stats=stats,
        recent_designs=recent_designs,
        recent_activity=recent_activity,
    )


@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardStats:
    """
    Get just the dashboard statistics.
    
    Lighter endpoint for refreshing stats without full dashboard data.
    """
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Get project count
    project_count_query = (
        select(func.count())
        .where(Project.user_id == current_user.id)
        .where(Project.deleted_at.is_(None))
    )
    project_count_result = await db.execute(project_count_query)
    total_projects = project_count_result.scalar() or 0
    
    # Get design count
    design_count_query = (
        select(func.count())
        .select_from(Design)
        .join(Project, Design.project_id == Project.id)
        .where(Project.user_id == current_user.id)
        .where(Design.deleted_at.is_(None))
    )
    design_count_result = await db.execute(design_count_query)
    total_designs = design_count_result.scalar() or 0
    
    # Get designs created this month
    designs_month_query = (
        select(func.count())
        .select_from(Design)
        .join(Project, Design.project_id == Project.id)
        .where(Project.user_id == current_user.id)
        .where(Design.deleted_at.is_(None))
        .where(Design.created_at >= month_start)
    )
    designs_month_result = await db.execute(designs_month_query)
    designs_this_month = designs_month_result.scalar() or 0
    
    # Get AI generations this month
    generations_query = (
        select(func.count())
        .where(Job.user_id == current_user.id)
        .where(Job.job_type == "ai_generation")
        .where(Job.status == "completed")
        .where(Job.created_at >= month_start)
    )
    generations_result = await db.execute(generations_query)
    generations_this_month = generations_result.scalar() or 0
    
    # Get exports this month
    exports_query = (
        select(func.count())
        .where(Job.user_id == current_user.id)
        .where(Job.job_type.in_(["export", "format_conversion"]))
        .where(Job.status == "completed")
        .where(Job.created_at >= month_start)
    )
    exports_result = await db.execute(exports_query)
    exports_this_month = exports_result.scalar() or 0
    
    return DashboardStats(
        total_projects=total_projects,
        total_designs=total_designs,
        designs_this_month=designs_this_month,
        generations_this_month=generations_this_month,
        exports_this_month=exports_this_month,
    )


@router.get("/dashboard/recent-designs")
async def get_recent_designs(
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[RecentDesign]:
    """
    Get recent designs for the current user.
    """
    query = (
        select(Design, Project.name.label("project_name"))
        .join(Project, Design.project_id == Project.id)
        .where(Project.user_id == current_user.id)
        .where(Design.deleted_at.is_(None))
        .order_by(Design.updated_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    rows = result.all()
    
    designs = []
    for row in rows:
        design = row[0]
        project_name = row[1]
        thumbnail_url = None
        if design.extra_data:
            thumbnail_url = design.extra_data.get("thumbnail_url")
        
        designs.append(RecentDesign(
            id=str(design.id),
            name=design.name,
            project_id=str(design.project_id),
            project_name=project_name,
            thumbnail_url=thumbnail_url,
            source_type=design.source_type,
            status=design.status,
            created_at=design.created_at.isoformat(),
            updated_at=design.updated_at.isoformat(),
        ))
    
    return designs
