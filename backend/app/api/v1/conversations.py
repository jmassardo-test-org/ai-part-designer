"""
Conversation API endpoints for chat-based CAD generation.

Provides REST API for iterative, conversational part design.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.ai.exceptions import AIConnectionError
from app.ai.generator import generate_from_description
from app.ai.iterative_reasoning import (
    PartUnderstanding,
    ReasoningState,
    apply_clarification_response,
    format_questions_for_user,
    format_understanding_summary,
    process_user_message,
)
from app.ai.reasoning import PartIntent
from app.api.deps import get_current_user, get_db
from app.models.conversation import (
    Conversation,
    ConversationMessage,
    ConversationStatus,
    MessageRole,
    MessageType,
)

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Helper Functions
# =============================================================================


def _understanding_to_intent(understanding: PartUnderstanding) -> PartIntent:
    """
    Convert a PartUnderstanding to a PartIntent for code generation.

    This bridges the iterative reasoning module with the code generation module,
    ensuring that the structured understanding is used directly without
    re-reasoning from raw text.

    Args:
        understanding: The accumulated understanding from conversation

    Returns:
        PartIntent suitable for code generation
    """
    # Extract dimensions as a flat dict of floats
    overall_dimensions: dict[str, float] = {}
    for _key, dim in understanding.dimensions.items():
        overall_dimensions[dim.name] = dim.value

    # Convert features to the format expected by PartIntent
    features: list[dict[str, Any]] = []
    for f in understanding.features:
        features.append(
            {
                "type": f.feature_type,
                "description": f.description,
                "parameters": f.parameters,
                "location": f.location,
                "count": f.count,
            }
        )

    # Get part type from classification
    part_type = "custom"
    primary_function = "General purpose part"
    if understanding.classification:
        part_type = understanding.classification.category.lower()
        primary_function = understanding.classification.subcategory or f"Standard {part_type}"

    return PartIntent(
        part_type=part_type,
        primary_function=primary_function,
        overall_dimensions=overall_dimensions,
        material_thickness=overall_dimensions.get("thickness"),
        features=features,
        constraints=understanding.constraints,
        referenced_hardware=understanding.hardware_references,
        confidence=understanding.classification.confidence if understanding.classification else 0.5,
        clarifications_needed=understanding.ambiguities,
        assumptions_made=understanding.assumptions,
    )


# =============================================================================
# Request/Response Models
# =============================================================================


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""

    design_id: UUID | None = Field(
        default=None,
        description="Optional design ID to attach context from existing model",
    )


class MessageRequest(BaseModel):
    """Request to send a message in a conversation."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User's message content",
    )


class MessageResponse(BaseModel):
    """A single message in the conversation."""

    id: UUID
    role: str
    message_type: str
    content: str
    extra_data: dict[str, Any] | None = None
    created_at: datetime


class ConversationResponse(BaseModel):
    """Full conversation with messages."""

    id: UUID
    status: str
    title: str | None
    messages: list[MessageResponse]
    understanding: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class ConversationListItem(BaseModel):
    """Summary of a conversation for listing."""

    id: UUID
    status: str
    title: str | None
    message_count: int
    created_at: datetime
    updated_at: datetime


class SendMessageResponse(BaseModel):
    """Response after sending a message."""

    user_message: MessageResponse
    assistant_message: MessageResponse
    # Additional assistant messages (e.g., confirmation before generation result)
    additional_messages: list[MessageResponse] = []
    conversation_status: str
    understanding: dict[str, Any] | None = None
    ready_to_generate: bool = False
    result: dict[str, Any] | None = None


class DirectGenerateRequest(BaseModel):
    """Request for direct AI generation (bypasses iterative reasoning)."""

    description: str = Field(..., description="Natural language description of the part")


class DirectGenerateResponse(BaseModel):
    """Response from direct AI generation."""

    success: bool
    job_id: str | None = None
    code: str | None = None
    downloads: dict[str, str] | None = None
    error: str | None = None
    retry_count: int = 0
    generation_time_ms: float = 0.0
    execution_time_ms: float = 0.0


# =============================================================================
# Helper Functions
# =============================================================================


def _message_to_response(msg: ConversationMessage) -> MessageResponse:
    """Convert a ConversationMessage to MessageResponse."""
    return MessageResponse(
        id=msg.id,
        role=msg.role,  # Now a string, not enum
        message_type=msg.message_type,  # Now a string, not enum
        content=msg.content,
        extra_data=msg.extra_data,
        created_at=msg.created_at,
    )


def _is_modification_request(message: str) -> bool:
    """
    Detect if a user message is a modification request.

    Modification requests typically contain action verbs that imply changing
    an existing part rather than creating something new.
    """
    modification_keywords = [
        "add ",
        "add a ",
        "add an ",
        "remove ",
        "remove the ",
        "delete ",
        "delete the ",
        "make it ",
        "make the ",
        "change ",
        "change the ",
        "increase ",
        "decrease ",
        "resize ",
        "move ",
        "move the ",
        "rotate ",
        "add hole",
        "add holes",
        "drill ",
        "cut ",
        "cut a ",
        "fillet ",
        "chamfer ",
        "round ",
        "taller",
        "shorter",
        "wider",
        "narrower",
        "longer",
        "deeper",
        "bigger",
        "smaller",
        "thicker",
        "thinner",
        "modify",
        "update",
        "adjust",
        "put a ",
        "include ",
        "attach ",
        "another ",
        "additional ",
        "extra ",
    ]

    message_lower = message.lower().strip()
    return any(
        message_lower.startswith(kw) or f" {kw}" in message_lower for kw in modification_keywords
    )


def _get_original_description(understanding: PartUnderstanding) -> str:
    """
    Get the original part description from understanding.

    This combines the initial messages before any modifications were requested.
    """
    if not understanding.user_messages:
        return ""

    # The first message is typically the original description
    # Look for the first substantial message
    for msg in understanding.user_messages:
        if len(msg) > 20 and not _is_modification_request(msg):
            return msg

    # Fall back to joining non-modification messages
    non_mod_messages = [m for m in understanding.user_messages if not _is_modification_request(m)]
    return " ".join(non_mod_messages) if non_mod_messages else understanding.user_messages[0]


async def _get_conversation(
    conversation_id: UUID,
    user_id: UUID,
    db: AsyncSession,
) -> Conversation:
    """Get a conversation by ID, ensuring user owns it."""
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return conversation


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: CreateConversationRequest = CreateConversationRequest(),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
    current_user: Annotated[User, Depends(get_current_user)] = ...,
) -> ConversationResponse:
    """
    Start a new conversation for CAD generation.
    
    Optionally attach context from an existing design for Q&A.
    """
    design_id = request.design_id
    
    # If design_id provided, verify access and extract context
    model_context_dict = None
    if design_id:
        from app.services.model_context import extract_model_context, get_design_by_id

        design = await get_design_by_id(design_id, current_user.id, db)
        if not design:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Design {design_id} not found or not accessible",
            )
        
        # Extract model context
        model_context = extract_model_context(design)
        model_context_dict = model_context.to_dict()
    
    conversation = Conversation(
        user_id=current_user.id,
        design_id=design_id,
        status=ConversationStatus.ACTIVE.value,
    )

    # Customize welcome message based on whether we have model context
    if model_context_dict:
        welcome_content = (
            f"Hi! I can help you with questions about your model '{model_context_dict['name']}'. "
            "Ask me about its dimensions, features, or how to modify it."
        )
    else:
        welcome_content = (
            "Hi! I'm here to help you design a CAD part. "
            "Describe what you'd like to create, including dimensions, features, and any specific requirements. "
            "I'll ask clarifying questions if I need more information."
        )

    welcome_msg = ConversationMessage(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT.value,
        message_type=MessageType.TEXT.value,
        content=welcome_content,
    )

    conversation.messages.append(welcome_msg)

    # Set initial understanding with model context if provided
    if model_context_dict:
        understanding = PartUnderstanding()
        understanding.model_context = model_context_dict
        conversation.intent_data = understanding.to_dict()

    db.add(conversation)
    await db.commit()

    # Fetch with eager loading to avoid lazy load issues
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation.id)
    )
    refreshed_conversation = result.scalars().first()
    assert refreshed_conversation is not None  # Just added, should exist

    return ConversationResponse(
        id=refreshed_conversation.id,
        status=refreshed_conversation.status,
        title=refreshed_conversation.title,
        messages=[_message_to_response(m) for m in refreshed_conversation.messages],
        understanding=refreshed_conversation.intent_data,
        result=None,
        created_at=refreshed_conversation.created_at,
        updated_at=refreshed_conversation.updated_at,
    )


@router.get("/", response_model=list[ConversationListItem])
async def list_conversations(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = 20,
    offset: int = 0,
) -> list[ConversationListItem]:
    """
    List user's conversations.
    """
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    conversations = result.scalars().all()

    return [
        ConversationListItem(
            id=c.id,
            status=c.status,  # Now a string
            title=c.title,
            message_count=len(c.messages),
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in conversations
    ]


@router.post("/direct-generate", response_model=DirectGenerateResponse)
async def direct_generate(
    request: DirectGenerateRequest,
    _db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> DirectGenerateResponse:
    """
    Generate a CAD part directly from natural language description.

    This bypasses the iterative reasoning system and goes straight to AI code generation.
    Use this for quick prototyping or when you know exactly what you want.

    The AI will:
    1. Parse your description
    2. Generate CadQuery code
    3. Execute and validate the code
    4. Return downloadable files
    """
    import tempfile
    import uuid
    from pathlib import Path

    from app.ai.direct_generation import generate_directly
    from app.cad.export import ExportQuality, export_step, export_stl

    logger.info(f"Direct generation request: {request.description[:100]}...")

    try:
        # Generate directly with AI
        result = await generate_directly(request.description)

        if not result.is_successful:
            return DirectGenerateResponse(
                success=False,
                error=result.error,
                code=result.code,
                retry_count=result.retry_count,
                generation_time_ms=result.generation_time_ms,
            )

        # Export to files
        job_id = str(uuid.uuid4())
        output_dir = Path(tempfile.gettempdir()) / "cad_exports"
        output_dir.mkdir(parents=True, exist_ok=True)

        base_name = f"custom_{job_id[:8]}"
        step_path = output_dir / f"{base_name}.step"
        stl_path = output_dir / f"{base_name}.stl"

        step_data = export_step(result.shape)
        stl_data = export_stl(result.shape, quality=ExportQuality.STANDARD)

        from app.core.file_encryption import encrypt_and_write

        await encrypt_and_write(step_path, step_data)
        await encrypt_and_write(stl_path, stl_data)

        logger.info(f"Direct generation successful: job_id={job_id}")

        return DirectGenerateResponse(
            success=True,
            job_id=job_id,
            code=result.code,
            downloads={
                "step": f"/api/v1/generate/{job_id}/download/step",
                "stl": f"/api/v1/generate/{job_id}/download/stl",
            },
            retry_count=result.retry_count,
            generation_time_ms=result.generation_time_ms,
            execution_time_ms=result.execution_time_ms,
        )

    except Exception as e:
        logger.exception(f"Direct generation failed: {e}")
        return DirectGenerateResponse(
            success=False,
            error=str(e),
        )


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ConversationResponse:
    """
    Get a conversation by ID with all messages.
    """
    conversation = await _get_conversation(conversation_id, current_user.id, db)

    return ConversationResponse(
        id=conversation.id,
        status=conversation.status,  # Now a string
        title=conversation.title,
        messages=[_message_to_response(m) for m in conversation.messages],
        understanding=conversation.intent_data,
        result=conversation.result_data,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@router.post("/{conversation_id}/messages", response_model=SendMessageResponse)
async def send_message(
    conversation_id: UUID,
    request: MessageRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SendMessageResponse:
    """
    Send a message in a conversation and get AI response.

    This is the main interaction point. The AI will:
    1. Process the message through iterative reasoning
    2. Ask clarifying questions if needed
    3. Generate the CAD when ready

    Even after completion, users can send messages to request modifications.
    """
    conversation = await _get_conversation(conversation_id, current_user.id, db)

    # Allow messages even after completion (for modifications)
    # Only block if failed
    if conversation.status == ConversationStatus.FAILED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conversation has failed and cannot continue",
        )

    # If completed, reset to active for modifications
    if conversation.status == ConversationStatus.COMPLETED.value:
        conversation.status = ConversationStatus.ACTIVE.value

    # Save user message
    user_msg = ConversationMessage(
        conversation_id=conversation.id,
        role=MessageRole.USER.value,  # Use .value for string storage
        message_type=MessageType.TEXT.value,  # Use .value for string storage
        content=request.content,
    )
    conversation.messages.append(user_msg)

    # Load or create understanding
    if conversation.intent_data:
        understanding = PartUnderstanding.from_dict(conversation.intent_data)
    else:
        understanding = None

    # Track additional messages (e.g., confirmation before generation)
    confirmation_msg = None

    # Process through reasoning engine
    try:
        if understanding and understanding.state == ReasoningState.NEEDS_CLARIFICATION:
            # User is responding to clarification
            understanding = await apply_clarification_response(request.content, understanding)
        else:
            # New or continuing input
            understanding = await process_user_message(request.content, understanding)

        # Save updated understanding
        conversation.intent_data = understanding.to_dict()

        # Determine response based on state
        if understanding.state == ReasoningState.NEEDS_CLARIFICATION:
            # Need more info - ask questions
            response_content = format_questions_for_user(understanding)
            msg_type = MessageType.CLARIFICATION.value
            conversation.status = ConversationStatus.CLARIFYING.value
            ready_to_generate = False
            result = None
            skip_generic_msg = False

        elif understanding.state == ReasoningState.READY_TO_PLAN:
            # Have enough info - show confirmation and generate
            confirmation = format_understanding_summary(understanding)
            response_content = f"{confirmation}\n\nI'll start generating your part now..."
            msg_type = MessageType.CONFIRMATION.value
            conversation.status = ConversationStatus.GENERATING.value
            ready_to_generate = True

            # Save confirmation message FIRST (before generation)
            confirmation_msg = ConversationMessage(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT.value,
                message_type=msg_type,
                content=response_content,
                extra_data={"state": understanding.state.value},
            )
            conversation.messages.append(confirmation_msg)

            # Generate the CAD
            try:
                # Check if this is a modification of an existing part
                is_modification = conversation.result_data is not None and _is_modification_request(
                    request.content
                )

                gen_result: Any  # Can be ModificationResult or DirectResult

                if is_modification:
                    # result_data is guaranteed to be not None when is_modification is True
                    assert conversation.result_data is not None
                    # Get original code for modification
                    original_code = conversation.result_data.get("generated_code")

                    logger.info(f"Processing modification request: {request.content}")
                    logger.info(f"Original code available: {bool(original_code)}")

                    if not original_code:
                        # Fallback: regenerate from scratch with modification included
                        full_description = (
                            " ".join(understanding.user_messages) + " " + request.content
                        )
                        from app.ai.direct_generation import generate_directly

                        code_result = await generate_directly(full_description)
                    else:
                        # Use direct modification
                        from app.ai.direct_generation import modify_directly

                        code_result = await modify_directly(
                            original_code=original_code,
                            modification_request=request.content,
                        )

                    if not code_result.is_successful:
                        raise Exception(code_result.error or "Modification failed")

                    # Export the modified shape
                    import tempfile
                    import uuid
                    from pathlib import Path

                    from app.cad.export import ExportQuality, export_step, export_stl

                    job_id = str(uuid.uuid4())
                    output_dir = Path(tempfile.gettempdir()) / "cad_exports"
                    output_dir.mkdir(parents=True, exist_ok=True)

                    # Use same naming pattern as generator.py: custom_{job_id[:8]}.{ext}
                    base_name = f"custom_{job_id[:8]}"
                    step_path = output_dir / f"{base_name}.step"
                    stl_path = output_dir / f"{base_name}.stl"

                    step_data = export_step(code_result.shape)
                    stl_data = export_stl(code_result.shape, quality=ExportQuality.STANDARD)

                    from app.core.file_encryption import encrypt_and_write

                    await encrypt_and_write(step_path, step_data)
                    await encrypt_and_write(stl_path, stl_data)

                    # Get existing values from result_data (guaranteed non-None by assertion above)
                    existing_dims = conversation.result_data.get("dimensions", {})
                    existing_shape_type = conversation.result_data.get("shape", "custom")

                    # Build a result similar to generate_from_description
                    class ModificationResult:
                        def __init__(self) -> None:
                            self.job_id = job_id
                            self.step_path = step_path
                            self.stl_path = stl_path
                            self.is_successful = True
                            self.shape_type = existing_shape_type
                            self.dimensions = existing_dims
                            self.confidence = 0.9
                            self.warnings: list[str] = []
                            self.generated_code = code_result.code  # Store for future mods

                        def get_stats(self) -> dict[str, Any]:
                            return {
                                "job_id": self.job_id,
                                "generation_time_ms": code_result.generation_time_ms,
                                "execution_time_ms": code_result.execution_time_ms,
                                "modification": True,
                                "retry_count": code_result.retry_count,
                            }

                    gen_result = ModificationResult()
                else:
                    # Use direct AI generation - simpler and more flexible
                    import tempfile
                    import uuid as uuid_module
                    from pathlib import Path

                    from app.ai.direct_generation import generate_directly
                    from app.cad.export import ExportQuality, export_step, export_stl

                    description = " ".join(understanding.user_messages)
                    logger.info(f"Direct generation for: {description[:100]}...")

                    direct_result = await generate_directly(description)

                    if not direct_result.is_successful:
                        raise Exception(direct_result.error or "Generation failed")

                    # Export to files
                    job_id = str(uuid_module.uuid4())
                    output_dir = Path(tempfile.gettempdir()) / "cad_exports"
                    output_dir.mkdir(parents=True, exist_ok=True)

                    base_name = f"custom_{job_id[:8]}"
                    step_path = output_dir / f"{base_name}.step"
                    stl_path = output_dir / f"{base_name}.stl"

                    step_data = export_step(direct_result.shape)
                    stl_data = export_stl(direct_result.shape, quality=ExportQuality.STANDARD)

                    from app.core.file_encryption import encrypt_and_write

                    await encrypt_and_write(step_path, step_data)
                    await encrypt_and_write(stl_path, stl_data)

                    # Capture dimensions before class definition (understanding is guaranteed non-None here)
                    assert understanding is not None
                    captured_dimensions = {k: v.value for k, v in understanding.dimensions.items()}

                    # Create a simple result object
                    class DirectResult:
                        def __init__(self) -> None:
                            self.job_id = job_id
                            self.step_path = step_path
                            self.stl_path = stl_path
                            self.is_successful = True
                            self.shape_type = "custom"
                            self.dimensions = captured_dimensions
                            self.confidence = 0.9
                            self.warnings: list[str] = []
                            self.generated_code = direct_result.code

                        def get_stats(self) -> dict[str, Any]:
                            return {
                                "job_id": self.job_id,
                                "generation_time_ms": direct_result.generation_time_ms,
                                "execution_time_ms": direct_result.execution_time_ms,
                                "retry_count": direct_result.retry_count,
                            }

                    gen_result = DirectResult()

                # Build download URLs from the generated files
                downloads = {}
                if gen_result.step_path:
                    downloads["step"] = f"/api/v1/generate/{gen_result.job_id}/download/step"
                if gen_result.stl_path:
                    downloads["stl"] = f"/api/v1/generate/{gen_result.job_id}/download/stl"

                # Get generated code if available (for modifications)
                generated_code = None
                if hasattr(gen_result, "generated_code") and gen_result.generated_code:
                    generated_code = gen_result.generated_code

                result = {
                    "status": "completed" if gen_result.is_successful else "failed",
                    "job_id": gen_result.job_id,
                    "downloads": downloads,
                    "shape": gen_result.shape_type,
                    "dimensions": gen_result.dimensions,
                    "confidence": gen_result.confidence,
                    "warnings": gen_result.warnings,
                    "stats": gen_result.get_stats(),
                    "generated_code": generated_code,  # Store for future modifications
                }

                conversation.status = ConversationStatus.COMPLETED.value
                conversation.result_data = result
                conversation.result_job_id = gen_result.job_id

                # Add result message (this is the assistant_msg for this case)
                assistant_msg = ConversationMessage(
                    conversation_id=conversation.id,
                    role=MessageRole.ASSISTANT.value,
                    message_type=MessageType.RESULT.value,
                    content="Your part has been generated! You can download the files below.",
                    extra_data=result,
                )
                conversation.messages.append(assistant_msg)

                # Skip the generic assistant_msg addition below
                skip_generic_msg = True

            except Exception as e:
                logger.error(f"Generation failed: {e}")
                result = {"error": str(e)}
                conversation.status = ConversationStatus.FAILED.value
                # Update response_content for error message
                response_content = f"I encountered an error generating your part: {e}"
                msg_type = MessageType.ERROR.value
                ready_to_generate = False
                skip_generic_msg = False
        else:
            # Unexpected state
            response_content = format_understanding_summary(understanding)
            msg_type = MessageType.TEXT.value
            ready_to_generate = understanding.completeness_score >= 0.7
            result = None
            skip_generic_msg = False

    except AIConnectionError as e:
        logger.error(f"AI service not configured: {e}")
        response_content = (
            "The AI service is not configured. Please set up your ANTHROPIC_API_KEY "
            "in the .env file and restart the services. Contact your administrator if "
            "you need help with setup."
        )
        msg_type = MessageType.ERROR.value
        ready_to_generate = False
        result = None
        skip_generic_msg = False
    except Exception as e:
        import traceback

        logger.error(f"Reasoning failed: {e}")
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        response_content = f"I had trouble understanding that. Could you rephrase? Error: {e}"
        msg_type = MessageType.ERROR.value
        ready_to_generate = False
        result = None
        skip_generic_msg = False

    # Save assistant response (unless we already added it above)
    if not skip_generic_msg:
        assistant_msg = ConversationMessage(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT.value,
            message_type=msg_type,
            content=response_content,
            extra_data={"state": understanding.state.value if understanding else None},
        )
        conversation.messages.append(assistant_msg)

    # Update title from first user message if not set
    if not conversation.title and request.content:
        conversation.title = request.content[:100]

    await db.commit()

    # Build additional messages list (e.g., confirmation before result)
    additional_messages = []
    if confirmation_msg:
        additional_messages.append(_message_to_response(confirmation_msg))

    return SendMessageResponse(
        user_message=_message_to_response(user_msg),
        assistant_message=_message_to_response(assistant_msg),
        additional_messages=additional_messages,
        conversation_status=conversation.status,  # Now a string
        understanding=understanding.to_dict() if understanding else None,
        ready_to_generate=ready_to_generate,
        result=result,
    )


@router.post("/{conversation_id}/generate", response_model=SendMessageResponse)
async def trigger_generation(
    conversation_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SendMessageResponse:
    """
    Manually trigger generation if the conversation is ready.

    Use this when the user wants to proceed despite missing optional info.
    """
    conversation = await _get_conversation(conversation_id, current_user.id, db)

    if not conversation.intent_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No understanding built yet. Send some messages first.",
        )

    understanding = PartUnderstanding.from_dict(conversation.intent_data)

    # Check minimum completeness
    if understanding.completeness_score < 0.3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not enough information to generate. Please provide more details.",
        )

    # Generate
    conversation.status = ConversationStatus.GENERATING.value

    user_msg = ConversationMessage(
        conversation_id=conversation.id,
        role=MessageRole.USER.value,
        message_type=MessageType.TEXT.value,
        content="[Generate with current understanding]",
    )
    conversation.messages.append(user_msg)

    try:
        description = " ".join(understanding.user_messages)
        precomputed_intent = _understanding_to_intent(understanding)
        logger.info(
            f"Manual generation with precomputed intent: "
            f"type={precomputed_intent.part_type}, "
            f"dims={precomputed_intent.overall_dimensions}"
        )
        gen_result = await generate_from_description(
            description,
            precomputed_intent=precomputed_intent,
        )

        # Build download URLs
        downloads = {}
        if gen_result.step_path:
            downloads["step"] = f"/api/v1/files/{gen_result.job_id}/model.step"
        if gen_result.stl_path:
            downloads["stl"] = f"/api/v1/files/{gen_result.job_id}/model.stl"

        result = {
            "status": "completed" if gen_result.is_successful else "failed",
            "job_id": gen_result.job_id,
            "downloads": downloads,
            "shape": gen_result.shape_type,
            "dimensions": gen_result.dimensions,
            "confidence": gen_result.confidence,
            "warnings": gen_result.warnings,
            "stats": gen_result.get_stats(),
        }

        conversation.status = ConversationStatus.COMPLETED.value
        conversation.result_data = result
        conversation.result_job_id = gen_result.job_id

        assistant_msg = ConversationMessage(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT.value,
            message_type=MessageType.RESULT.value,
            content="Your part has been generated! You can download the files below.",
            extra_data=result,
        )

    except Exception as e:
        logger.error(f"Generation failed: {e}")
        result = {"error": str(e)}
        conversation.status = ConversationStatus.FAILED.value

        assistant_msg = ConversationMessage(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT.value,
            message_type=MessageType.ERROR.value,
            content=f"Generation failed: {e}",
            extra_data=result,
        )

    conversation.messages.append(assistant_msg)
    await db.commit()

    return SendMessageResponse(
        user_message=_message_to_response(user_msg),
        assistant_message=_message_to_response(assistant_msg),
        conversation_status=conversation.status,  # Now a string, no .value needed
        understanding=understanding.to_dict(),
        ready_to_generate=False,
        result=result,
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """
    Delete a conversation.
    """
    conversation = await _get_conversation(conversation_id, current_user.id, db)
    await db.delete(conversation)
    await db.commit()
