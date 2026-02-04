"""
Tests for conversations API endpoints.

Tests conversation CRUD and message operations.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.models.conversation import Conversation, ConversationMessage, ConversationStatus, MessageRole, MessageType


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
async def test_conversation(db_session: AsyncSession, test_user):
    """Create a test conversation for the test user."""
    conv = Conversation(
        id=uuid4(),
        user_id=test_user.id,
        title="Test Conversation",
        status=ConversationStatus.ACTIVE.value if hasattr(ConversationStatus.ACTIVE, 'value') else "active",
    )
    db_session.add(conv)
    await db_session.commit()
    await db_session.refresh(conv)
    
    yield conv
    
    # Cleanup
    try:
        await db_session.delete(conv)
        await db_session.commit()
    except Exception:
        pass


@pytest.fixture
async def test_conversation_with_messages(db_session: AsyncSession, test_user):
    """Create a test conversation with some messages."""
    conv = Conversation(
        id=uuid4(),
        user_id=test_user.id,
        title="Conversation with Messages",
        status="active",
    )
    db_session.add(conv)
    await db_session.flush()
    
    # Add messages
    messages = [
        ConversationMessage(
            id=uuid4(),
            conversation_id=conv.id,
            role="user",
            message_type="text",
            content="I need a small box for electronics",
        ),
        ConversationMessage(
            id=uuid4(),
            conversation_id=conv.id,
            role="assistant",
            message_type="text",
            content="I can help you design that. What dimensions do you need?",
        ),
    ]
    for msg in messages:
        db_session.add(msg)
    
    await db_session.commit()
    await db_session.refresh(conv)
    
    yield conv
    
    # Cleanup
    try:
        for msg in messages:
            await db_session.delete(msg)
        await db_session.delete(conv)
        await db_session.commit()
    except Exception:
        pass


# =============================================================================
# List Conversations Tests
# =============================================================================

class TestListConversations:
    """Tests for GET /api/v1/conversations/."""

    async def test_list_conversations_success(
        self, client: AsyncClient, auth_headers: dict, test_conversation
    ):
        """Should return list of user's conversations."""
        response = await client.get("/api/v1/conversations/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_list_conversations_unauthenticated(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.get("/api/v1/conversations/")
        assert response.status_code == 401


# =============================================================================
# Create Conversation Tests
# =============================================================================

class TestCreateConversation:
    """Tests for POST /api/v1/conversations/."""

    async def test_create_conversation_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should create a new conversation."""
        response = await client.post(
            "/api/v1/conversations/",
            headers=auth_headers,
            json={}  # Empty body - minimal creation
        )
        
        # Could be 201 or 200
        assert response.status_code in [200, 201]
        data = response.json()
        assert "id" in data
        assert "status" in data
        
        # Cleanup - delete the conversation
        conv_id = data["id"]
        await client.delete(f"/api/v1/conversations/{conv_id}", headers=auth_headers)


# =============================================================================
# Get Conversation Tests
# =============================================================================

class TestGetConversation:
    """Tests for GET /api/v1/conversations/{conversation_id}."""

    async def test_get_conversation_success(
        self, client: AsyncClient, auth_headers: dict, test_conversation
    ):
        """Should return conversation details."""
        response = await client.get(
            f"/api/v1/conversations/{test_conversation.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_conversation.id)

    async def test_get_conversation_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return 404 for non-existent conversation."""
        response = await client.get(
            "/api/v1/conversations/00000000-0000-0000-0000-000000000000",
            headers=auth_headers
        )
        
        assert response.status_code == 404

    async def test_get_conversation_with_messages(
        self, client: AsyncClient, auth_headers: dict, test_conversation_with_messages
    ):
        """Should return conversation with its messages."""
        response = await client.get(
            f"/api/v1/conversations/{test_conversation_with_messages.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert len(data["messages"]) >= 2


# =============================================================================
# Delete Conversation Tests
# =============================================================================

class TestDeleteConversation:
    """Tests for DELETE /api/v1/conversations/{conversation_id}."""

    async def test_delete_conversation_success(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user
    ):
        """Should delete conversation."""
        # Create a conversation to delete
        conv = Conversation(
            id=uuid4(),
            user_id=test_user.id,
            title="To Delete",
            status="active",
        )
        db_session.add(conv)
        await db_session.commit()
        
        response = await client.delete(
            f"/api/v1/conversations/{conv.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204

    async def test_delete_conversation_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return 404 for non-existent conversation."""
        response = await client.delete(
            "/api/v1/conversations/00000000-0000-0000-0000-000000000000",
            headers=auth_headers
        )
        
        assert response.status_code == 404


# =============================================================================
# Modification Detection Helper Tests
# =============================================================================

class TestModificationDetection:
    """Tests for the modification detection helper functions."""

    def test_is_modification_request_add(self):
        """Test that 'add a hole' is detected as modification."""
        from app.api.v1.conversations import _is_modification_request
        
        assert _is_modification_request("add a 10mm hole in the center")
        assert _is_modification_request("add holes to the corners")
        assert _is_modification_request("Add a fillet")
    
    def test_is_modification_request_remove(self):
        """Test that 'remove' requests are detected as modifications."""
        from app.api.v1.conversations import _is_modification_request
        
        assert _is_modification_request("remove the hole")
        assert _is_modification_request("delete the fillet")
    
    def test_is_modification_request_resize(self):
        """Test that resize requests are detected as modifications."""
        from app.api.v1.conversations import _is_modification_request
        
        assert _is_modification_request("make it taller")
        assert _is_modification_request("make it wider")
        assert _is_modification_request("increase the height")
        assert _is_modification_request("decrease the width")
    
    def test_is_modification_request_change(self):
        """Test that 'change' and 'modify' are detected as modifications."""
        from app.api.v1.conversations import _is_modification_request
        
        assert _is_modification_request("change the diameter to 20mm")
        assert _is_modification_request("modify the dimensions")
    
    def test_is_modification_request_additional(self):
        """Test that 'additional' and 'another' are detected as modifications."""
        from app.api.v1.conversations import _is_modification_request
        
        assert _is_modification_request("add another cube")
        assert _is_modification_request("add an additional hole")
    
    def test_is_not_modification_request_new_part(self):
        """Test that new part descriptions are NOT detected as modifications."""
        from app.api.v1.conversations import _is_modification_request
        
        assert not _is_modification_request("Create a box 100mm long")
        assert not _is_modification_request("I need a cylinder")
        assert not _is_modification_request("Design a bracket")
        assert not _is_modification_request("Make a 50mm cube")  # "Make a" is different from "make it"
    
    def test_get_original_description(self):
        """Test extraction of original description from understanding."""
        from app.api.v1.conversations import _get_original_description
        from app.ai.iterative_reasoning import PartUnderstanding
        
        understanding = PartUnderstanding()
        understanding.user_messages = [
            "Create a box 100mm long, 50mm wide, 30mm tall",
            "add a 10mm hole",
            "make it taller",
        ]
        
        original = _get_original_description(understanding)
        assert "Create a box" in original
        assert "add a 10mm hole" not in original
    
    def test_get_original_description_empty(self):
        """Test that empty understanding returns empty string."""
        from app.api.v1.conversations import _get_original_description
        from app.ai.iterative_reasoning import PartUnderstanding
        
        understanding = PartUnderstanding()
        original = _get_original_description(understanding)
        assert original == ""


class TestUnderstandingToIntent:
    """Tests for _understanding_to_intent helper function."""
    
    def test_understanding_to_intent_cylinder(self):
        """Test that cylinder understanding is correctly converted to intent."""
        from app.api.v1.conversations import _understanding_to_intent
        from app.ai.iterative_reasoning import (
            PartUnderstanding,
            PartClassification,
            ExtractedDimension,
            ExtractedFeature,
        )
        
        understanding = PartUnderstanding()
        understanding.classification = PartClassification(
            category="cylinder",
            subcategory="Standard Cylinder",
            confidence=0.95,
            reasoning="User requested a cylinder",
        )
        understanding.dimensions = {
            "diameter": ExtractedDimension(name="diameter", value=50.8, unit="mm"),
            "height": ExtractedDimension(name="height", value=101.6, unit="mm"),
        }
        understanding.features = [
            ExtractedFeature(
                feature_type="hole",
                description="center through hole",
                parameters={"diameter": 10},
                location="center",
                count=1,
            )
        ]
        
        intent = _understanding_to_intent(understanding)
        
        assert intent.part_type == "cylinder"
        assert intent.overall_dimensions["diameter"] == 50.8
        assert intent.overall_dimensions["height"] == 101.6
        assert len(intent.features) == 1
        assert intent.features[0]["type"] == "hole"
        assert intent.confidence == 0.95
    
    def test_understanding_to_intent_bracket(self):
        """Test that bracket understanding is correctly converted to intent."""
        from app.api.v1.conversations import _understanding_to_intent
        from app.ai.iterative_reasoning import (
            PartUnderstanding,
            PartClassification,
            ExtractedDimension,
        )
        
        understanding = PartUnderstanding()
        understanding.classification = PartClassification(
            category="bracket",
            subcategory="L-bracket",
            confidence=0.90,
        )
        understanding.dimensions = {
            "flange_length": ExtractedDimension(name="flange_length", value=50, unit="mm"),
            "thickness": ExtractedDimension(name="thickness", value=3, unit="mm"),
        }
        
        intent = _understanding_to_intent(understanding)
        
        assert intent.part_type == "bracket"
        assert intent.primary_function == "L-bracket"
        assert intent.overall_dimensions["flange_length"] == 50
        assert intent.overall_dimensions["thickness"] == 3
        assert intent.material_thickness == 3
    
    def test_understanding_to_intent_with_assumptions(self):
        """Test that assumptions are preserved in intent conversion."""
        from app.api.v1.conversations import _understanding_to_intent
        from app.ai.iterative_reasoning import PartUnderstanding, PartClassification
        
        understanding = PartUnderstanding()
        understanding.classification = PartClassification(category="box", confidence=0.8)
        understanding.assumptions = ["Using default wall thickness of 3mm"]
        understanding.ambiguities = ["Hole diameter not specified"]
        
        intent = _understanding_to_intent(understanding)
        
        assert "Using default wall thickness of 3mm" in intent.assumptions_made
        assert "Hole diameter not specified" in intent.clarifications_needed
    
    def test_understanding_to_intent_no_classification(self):
        """Test handling when classification is missing."""
        from app.api.v1.conversations import _understanding_to_intent
        from app.ai.iterative_reasoning import PartUnderstanding
        
        understanding = PartUnderstanding()
        understanding.classification = None
        
        intent = _understanding_to_intent(understanding)
        
        assert intent.part_type == "custom"
        assert intent.confidence == 0.5


# =============================================================================
# SendMessageResponse Schema Tests
# =============================================================================

class TestSendMessageResponseSchema:
    """Tests for SendMessageResponse schema with additional_messages field."""

    def test_send_message_response_includes_additional_messages_field(self):
        """Verify SendMessageResponse has additional_messages field with correct default."""
        from app.api.v1.conversations import SendMessageResponse, MessageResponse
        from datetime import datetime
        from uuid import uuid4
        
        user_msg = MessageResponse(
            id=uuid4(),
            role="user",
            message_type="text",
            content="Create a box",
            created_at=datetime.utcnow(),
        )
        assistant_msg = MessageResponse(
            id=uuid4(),
            role="assistant",
            message_type="result",
            content="Part generated",
            created_at=datetime.utcnow(),
        )
        
        # Without additional_messages
        response = SendMessageResponse(
            user_message=user_msg,
            assistant_message=assistant_msg,
            conversation_status="completed",
        )
        
        assert response.additional_messages == []

    def test_send_message_response_with_additional_messages(self):
        """Verify additional_messages can be populated correctly."""
        from app.api.v1.conversations import SendMessageResponse, MessageResponse
        from datetime import datetime
        from uuid import uuid4
        
        user_msg = MessageResponse(
            id=uuid4(),
            role="user",
            message_type="text",
            content="Create a cylinder",
            created_at=datetime.utcnow(),
        )
        confirmation_msg = MessageResponse(
            id=uuid4(),
            role="assistant",
            message_type="confirmation",
            content="Here's what I understand: You want a cylinder...",
            created_at=datetime.utcnow(),
        )
        assistant_msg = MessageResponse(
            id=uuid4(),
            role="assistant",
            message_type="result",
            content="Part generated",
            created_at=datetime.utcnow(),
        )
        
        response = SendMessageResponse(
            user_message=user_msg,
            assistant_message=assistant_msg,
            additional_messages=[confirmation_msg],
            conversation_status="completed",
            ready_to_generate=True,
            result={"status": "completed"},
        )
        
        assert len(response.additional_messages) == 1
        assert response.additional_messages[0].message_type == "confirmation"
        assert "Here's what I understand" in response.additional_messages[0].content
