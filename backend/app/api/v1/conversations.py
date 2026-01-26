"""
Conversation API endpoints for chat-based CAD generation.

Provides REST API for iterative, conversational part design.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.conversation import (
    Conversation,
    ConversationMessage,
    ConversationStatus,
    MessageRole,
    MessageType,
)
from app.ai.iterative_reasoning import (
    process_user_message,
    apply_clarification_response,
    format_questions_for_user,
    format_understanding_summary,
    PartUnderstanding,
    ReasoningState,
)
from app.ai.generator import generate_from_description

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

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
    conversation_status: str
    understanding: dict[str, Any] | None = None
    ready_to_generate: bool = False
    result: dict[str, Any] | None = None


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
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ConversationResponse:
    """
    Start a new conversation for CAD generation.
    """
    conversation = Conversation(
        user_id=current_user.id,
        status=ConversationStatus.ACTIVE.value,
    )
    
    # Add welcome message
    welcome_msg = ConversationMessage(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT.value,
        message_type=MessageType.TEXT.value,
        content=(
            "Hi! I'm here to help you design a CAD part. "
            "Describe what you'd like to create, including dimensions, features, and any specific requirements. "
            "I'll ask clarifying questions if I need more information."
        ),
    )
    
    conversation.messages.append(welcome_msg)
    
    db.add(conversation)
    await db.commit()
    
    # Fetch with eager loading to avoid lazy load issues
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation.id)
    )
    conversation = result.scalars().first()
    
    return ConversationResponse(
        id=conversation.id,
        status=conversation.status,
        title=conversation.title,
        messages=[_message_to_response(m) for m in conversation.messages],
        understanding=None,
        result=None,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
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
                description = " ".join(understanding.user_messages)
                gen_result = await generate_from_description(description)
                
                # Build download URLs from the generated files
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
        
    except Exception as e:
        logger.error(f"Reasoning failed: {e}")
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
    
    return SendMessageResponse(
        user_message=_message_to_response(user_msg),
        assistant_message=_message_to_response(assistant_msg),
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
        gen_result = await generate_from_description(description)
        
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
