"""
Design Refinement API endpoints.

Handles iterative design refinement with AI.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models import (
    Design,
    DesignContext,
    DesignRefinementJob,
    User,
)

router = APIRouter(prefix="/designs/{design_id}/refine", tags=["refine"])


# --- Schemas ---


class RefineRequest(BaseModel):
    """Request to refine a design."""

    instruction: str = Field(..., min_length=1, max_length=2000)
    apply_immediately: bool = Field(
        default=True,
        description="If true, apply changes immediately. If false, return preview.",
    )


class RefinePreviewResponse(BaseModel):
    """Preview of refinement changes."""

    ai_response: str
    suggested_parameters: dict[str, Any]
    current_parameters: dict[str, Any]
    changes_summary: list[str]
    estimated_time_seconds: int


class RefineResponse(BaseModel):
    """Result of refinement."""

    success: bool
    job_id: str | None = None
    message: str
    ai_response: str | None = None
    new_version_id: str | None = None
    old_parameters: dict[str, Any] | None = None
    new_parameters: dict[str, Any] | None = None


class ConversationMessage(BaseModel):
    """A message in the design conversation."""

    role: str
    content: str
    timestamp: str
    parameters: dict[str, Any] | None = None


class DesignContextResponse(BaseModel):
    """Design context response."""

    id: str
    design_id: str
    messages: list[ConversationMessage]
    parameters: dict[str, Any]
    iteration_count: int
    last_instruction: str | None
    created_at: str
    updated_at: str


class RefineJobResponse(BaseModel):
    """Refinement job status."""

    id: str
    design_id: str
    instruction: str
    status: str
    old_parameters: dict[str, Any] | None
    new_parameters: dict[str, Any] | None
    ai_response: str | None
    result_version_id: str | None
    error_message: str | None
    created_at: str
    started_at: str | None
    completed_at: str | None


# --- Helper Functions ---


async def get_design_or_404(
    design_id: UUID,
    db: AsyncSession,
    user: User,
) -> Design:
    """Get design or raise 404, checking ownership."""
    result = await db.execute(
        select(Design)
        .where(Design.id == design_id)
        .options(
            selectinload(Design.project),
            selectinload(Design.context),
        )
    )
    design = result.scalar_one_or_none()

    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found",
        )

    if design.project.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return design


async def get_or_create_context(
    design: Design,
    db: AsyncSession,
) -> DesignContext:
    """Get or create design context."""
    if design.context:
        return design.context

    # Create new context
    context = DesignContext(
        design_id=design.id,
        parameters=design.extra_data.get("parameters", {}),
    )

    # Add initial system message
    context.add_system_message(f"Design '{design.name}' created from {design.source_type}.")

    db.add(context)
    await db.commit()
    await db.refresh(context)

    return context


async def refine_design_ai(
    instruction: str,
    context: DesignContext,
) -> tuple[str, dict[str, Any]]:
    """
    Call AI to interpret instruction and return parameter changes.

    Returns (ai_response, new_parameters).
    """
    # TODO: Replace with actual AI call
    # For now, return a mock response

    current_params = context.parameters.copy()

    # Simple parameter modification based on keywords
    instruction_lower = instruction.lower()

    if "taller" in instruction_lower or "higher" in instruction_lower:
        if "height" in current_params:
            current_params["height"] = current_params["height"] * 1.2
        response = "I'll increase the height by 20%."
    elif "shorter" in instruction_lower or "lower" in instruction_lower:
        if "height" in current_params:
            current_params["height"] = current_params["height"] * 0.8
        response = "I'll decrease the height by 20%."
    elif "wider" in instruction_lower:
        if "width" in current_params:
            current_params["width"] = current_params["width"] * 1.2
        response = "I'll increase the width by 20%."
    elif "narrower" in instruction_lower or "thinner" in instruction_lower:
        if "width" in current_params:
            current_params["width"] = current_params["width"] * 0.8
        response = "I'll decrease the width by 20%."
    elif "longer" in instruction_lower:
        if "length" in current_params:
            current_params["length"] = current_params["length"] * 1.2
        response = "I'll increase the length by 20%."
    elif "shorter" in instruction_lower:
        if "length" in current_params:
            current_params["length"] = current_params["length"] * 0.8
        response = "I'll decrease the length by 20%."
    else:
        response = f"I understand you want to: {instruction}. I'll process this change."

    return response, current_params


# --- Endpoints ---


@router.get("/context", response_model=DesignContextResponse)
async def get_design_context(
    design_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DesignContextResponse:
    """Get the conversation context for a design."""
    design = await get_design_or_404(design_id, db, current_user)
    context = await get_or_create_context(design, db)

    return DesignContextResponse(
        id=str(context.id),
        design_id=str(context.design_id),
        messages=[
            ConversationMessage(
                role=m["role"],
                content=m["content"],
                timestamp=m["timestamp"],
                parameters=m.get("parameters"),
            )
            for m in context.messages
        ],
        parameters=context.parameters,
        iteration_count=context.iteration_count,
        last_instruction=context.last_instruction,
        created_at=context.created_at.isoformat(),
        updated_at=context.updated_at.isoformat(),
    )


@router.post("", response_model=RefineResponse)
async def refine_design(
    design_id: UUID,
    request: RefineRequest,
    _background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RefineResponse:
    """
    Refine a design with a natural language instruction.

    The AI interprets the instruction, determines parameter changes,
    and creates a new version of the design.
    """
    design = await get_design_or_404(design_id, db, current_user)
    context = await get_or_create_context(design, db)

    # Record user message
    context.add_user_message(request.instruction)

    try:
        # Get AI response and new parameters
        ai_response, new_parameters = await refine_design_ai(
            request.instruction,
            context,
        )

        # Record assistant response
        context.add_assistant_message(ai_response, new_parameters)

        if request.apply_immediately:
            # Create new version with updated parameters
            old_params = context.parameters.copy()

            # Update context with new iteration
            context.increment_iteration(request.instruction, new_parameters)

            # Update design extra_data with new parameters
            design.extra_data = {
                **design.extra_data,
                "parameters": new_parameters,
            }

            await db.commit()

            return RefineResponse(
                success=True,
                message="Design refined successfully",
                ai_response=ai_response,
                old_parameters=old_params,
                new_parameters=new_parameters,
            )
        # Return preview only
        await db.commit()

        return RefineResponse(
            success=True,
            message="Preview generated. Call again with apply_immediately=true to apply.",
            ai_response=ai_response,
            old_parameters=context.parameters,
            new_parameters=new_parameters,
        )

    except Exception as e:
        context.add_system_message(f"Refinement failed: {e!s}")
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refine design: {e!s}",
        )


@router.post("/preview", response_model=RefinePreviewResponse)
async def preview_refinement(
    design_id: UUID,
    request: RefineRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RefinePreviewResponse:
    """
    Preview refinement changes without applying them.
    """
    design = await get_design_or_404(design_id, db, current_user)
    context = await get_or_create_context(design, db)

    # Get AI response and new parameters
    ai_response, new_parameters = await refine_design_ai(
        request.instruction,
        context,
    )

    # Calculate changes
    changes = []
    for key, new_value in new_parameters.items():
        old_value = context.parameters.get(key)
        if old_value != new_value:
            changes.append(f"{key}: {old_value} → {new_value}")

    return RefinePreviewResponse(
        ai_response=ai_response,
        suggested_parameters=new_parameters,
        current_parameters=context.parameters,
        changes_summary=changes,
        estimated_time_seconds=5,
    )


@router.delete("/context", status_code=status.HTTP_204_NO_CONTENT)
async def reset_context(
    design_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Reset the conversation context for a design.

    This clears all conversation history but preserves current parameters.
    """
    design = await get_design_or_404(design_id, db, current_user)

    if design.context:
        # Reset messages but keep parameters
        design.context.messages = []
        design.context.iteration_count = 0
        design.context.last_instruction = None
        design.context.add_system_message(f"Conversation reset for design '{design.name}'.")
        await db.commit()


@router.get("/jobs", response_model=list[RefineJobResponse])
async def list_refinement_jobs(
    design_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[RefineJobResponse]:
    """List refinement jobs for a design."""
    await get_design_or_404(design_id, db, current_user)

    result = await db.execute(
        select(DesignRefinementJob)
        .where(DesignRefinementJob.design_id == design_id)
        .order_by(DesignRefinementJob.created_at.desc())
        .limit(20)
    )
    jobs = result.scalars().all()

    return [RefineJobResponse(**job.to_dict()) for job in jobs]


@router.get("/jobs/{job_id}", response_model=RefineJobResponse)
async def get_refinement_job(
    design_id: UUID,
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RefineJobResponse:
    """Get a specific refinement job."""
    await get_design_or_404(design_id, db, current_user)

    result = await db.execute(
        select(DesignRefinementJob).where(
            DesignRefinementJob.id == job_id,
            DesignRefinementJob.design_id == design_id,
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refinement job not found",
        )

    return RefineJobResponse(**job.to_dict())
