"""
Tests for AI processing worker tasks.

Tests AI generation, moderation, and suggestion functionality.
"""

from __future__ import annotations

import pytest

# =============================================================================
# Content Moderation Tests
# =============================================================================


class TestContentModeration:
    """Tests for content moderation functionality."""

    @pytest.mark.asyncio
    async def test_moderation_approves_safe_content(self):
        """Test that safe content is approved."""
        from app.worker.tasks.ai import _check_content_moderation

        result = await _check_content_moderation("Create a box with dimensions 50x50x50mm")

        assert result["flagged"] is False
        assert result["decision"] == "approved"

    @pytest.mark.asyncio
    async def test_moderation_flags_weapon_content(self):
        """Test that weapon-related content is flagged."""
        from app.worker.tasks.ai import _check_content_moderation

        result = await _check_content_moderation("Create a gun handle")

        assert result["flagged"] is True
        assert result["decision"] == "rejected"
        assert result["categories"]["weapons"]["flagged"] is True

    @pytest.mark.asyncio
    async def test_moderation_flags_violence_content(self):
        """Test that violence-related content is flagged."""
        from app.worker.tasks.ai import _check_content_moderation

        result = await _check_content_moderation("Design something to harm people")

        assert result["flagged"] is True
        assert result["categories"]["violence"]["flagged"] is True

    @pytest.mark.asyncio
    async def test_moderation_returns_category_scores(self):
        """Test that moderation returns category scores."""
        from app.worker.tasks.ai import _check_content_moderation

        result = await _check_content_moderation("A simple bracket")

        assert "categories" in result
        assert "weapons" in result["categories"]
        assert "violence" in result["categories"]
        assert "score" in result["categories"]["weapons"]


class TestModerateContentTask:
    """Tests for the moderate_content Celery task."""

    def test_task_has_correct_name(self):
        """Test that task has expected name."""
        from app.worker.tasks.ai import moderate_content

        assert moderate_content.name == "app.worker.tasks.ai.moderate_content"

    def test_moderate_content_returns_decision(self):
        """Test that task returns moderation decision."""
        from app.worker.tasks.ai import moderate_content

        result = moderate_content.run("Create a mounting bracket")

        assert "flagged" in result
        assert "decision" in result
        assert "categories" in result

    def test_moderate_content_safe_prompt(self):
        """Test moderation of safe content."""
        from app.worker.tasks.ai import moderate_content

        result = moderate_content.run("Design a phone stand with adjustable angle")

        assert result["flagged"] is False
        assert result["decision"] == "approved"

    def test_moderate_content_with_content_type(self):
        """Test moderation with content type parameter."""
        from app.worker.tasks.ai import moderate_content

        result = moderate_content.run("A simple code snippet", content_type="code")

        assert result is not None


# =============================================================================
# AI Generation Task Tests
# =============================================================================


class TestGenerateFromPromptTask:
    """Tests for the generate_from_prompt Celery task."""

    def test_task_has_correct_name(self):
        """Test that task has expected name."""
        from app.worker.tasks.ai import generate_from_prompt

        assert generate_from_prompt.name == "app.worker.tasks.ai.generate_from_prompt"

    def test_task_has_retry_config(self):
        """Test that task has retry configuration."""
        from app.worker.tasks.ai import generate_from_prompt

        assert generate_from_prompt.max_retries == 2
        assert generate_from_prompt.default_retry_delay == 30

    def test_task_signature(self):
        """Test that task has expected parameters."""
        import inspect

        from app.worker.tasks.ai import generate_from_prompt

        sig = inspect.signature(generate_from_prompt.run)
        params = list(sig.parameters.keys())

        assert "job_id" in params
        assert "prompt" in params
        assert "_context" in params  # Note: underscore prefix indicates optional/reserved
        assert "user_id" in params


class TestGenerateFromPromptWithMocks:
    """Tests for generate_from_prompt with mocked dependencies."""

    @pytest.mark.asyncio
    async def test_generation_rejects_flagged_content(self, db_session):
        """Test that flagged content causes generation to fail."""
        from app.worker.tasks.ai import _check_content_moderation

        result = await _check_content_moderation("Create a weapon")

        assert result["flagged"] is True

    @pytest.mark.asyncio
    async def test_generation_accepts_safe_content(self, db_session):
        """Test that safe content passes moderation."""
        from app.worker.tasks.ai import _check_content_moderation

        result = await _check_content_moderation("Create a rectangular enclosure 100x80x40mm")

        assert result["flagged"] is False


# =============================================================================
# Suggest Modifications Task Tests
# =============================================================================


class TestSuggestModificationsTask:
    """Tests for the suggest_modifications Celery task."""

    def test_task_has_correct_name(self):
        """Test that task has expected name."""
        from app.worker.tasks.ai import suggest_modifications

        assert suggest_modifications.name == "app.worker.tasks.ai.suggest_modifications"

    def test_task_signature(self):
        """Test that task has expected parameters."""
        import inspect

        from app.worker.tasks.ai import suggest_modifications

        sig = inspect.signature(suggest_modifications.run)
        params = list(sig.parameters.keys())

        assert "design_id" in params
        assert "user_request" in params


# =============================================================================
# AI Client Integration Tests
# =============================================================================


class TestAIClientIntegration:
    """Tests for AI client integration in worker tasks."""

    def test_ai_client_import(self):
        """Test that AI client imports correctly."""
        from app.ai.client import get_ai_client

        assert get_ai_client is not None

    def test_ai_generator_import(self):
        """Test that AI generator imports correctly."""
        from app.ai.generator import GenerationResult, generate_from_description

        assert generate_from_description is not None
        assert GenerationResult is not None

    def test_generation_result_attributes(self):
        """Test GenerationResult dataclass attributes."""
        import dataclasses

        from app.ai.generator import GenerationResult

        fields = {f.name for f in dataclasses.fields(GenerationResult)}

        assert "description" in fields
        assert "shape" in fields
        assert "generated_code" in fields
        assert "step_data" in fields
        assert "stl_data" in fields


# =============================================================================
# WebSocket Notification Integration Tests
# =============================================================================


class TestAITaskWebSocketIntegration:
    """Tests for WebSocket notifications in AI tasks."""

    def test_job_progress_notification_structure(self):
        """Test job progress notification has correct structure."""
        # Verify function signature
        import inspect

        from app.worker.ws_utils import send_job_progress

        sig = inspect.signature(send_job_progress)
        params = list(sig.parameters.keys())

        assert "user_id" in params
        assert "job_id" in params
        assert "progress" in params
        assert "status" in params

    def test_job_complete_notification_structure(self):
        """Test job complete notification has correct structure."""
        import inspect

        from app.worker.ws_utils import send_job_complete

        sig = inspect.signature(send_job_complete)
        params = list(sig.parameters.keys())

        assert "user_id" in params
        assert "job_id" in params
        assert "result" in params

    def test_job_failed_notification_structure(self):
        """Test job failed notification has correct structure."""
        import inspect

        from app.worker.ws_utils import send_job_failed

        sig = inspect.signature(send_job_failed)
        params = list(sig.parameters.keys())

        assert "user_id" in params
        assert "job_id" in params
        assert "error" in params
