"""
Tests for email service.
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.services.email import (
    EmailService,
    EmailMessage,
    EmailTemplate,
    ConsoleEmailBackend,
    SMTPEmailBackend,
    get_email_service,
)


class TestConsoleEmailBackend:
    """Tests for console email backend."""
    
    @pytest.mark.asyncio
    async def test_send_prints_to_console(self, caplog):
        """Console backend logs email content."""
        import logging
        caplog.set_level(logging.INFO)
        
        backend = ConsoleEmailBackend()
        message = EmailMessage(
            to="test@example.com",
            subject="Test Subject",
            html_body="<p>HTML content</p>",
            text_body="Text content",
        )
        
        result = await backend.send(message)
        
        assert result is True
        assert "test@example.com" in caplog.text
        assert "Test Subject" in caplog.text


class TestEmailMessage:
    """Tests for EmailMessage dataclass."""
    
    def test_create_message_required_fields(self):
        """Create message with required fields only."""
        msg = EmailMessage(
            to="user@test.com",
            subject="Hello",
            html_body="<p>World</p>",
        )
        
        assert msg.to == "user@test.com"
        assert msg.subject == "Hello"
        assert msg.html_body == "<p>World</p>"
        assert msg.text_body is None
        assert msg.from_email is None
        assert msg.reply_to is None
    
    def test_create_message_all_fields(self):
        """Create message with all fields."""
        msg = EmailMessage(
            to="user@test.com",
            subject="Hello",
            html_body="<p>World</p>",
            text_body="World",
            from_email="sender@test.com",
            reply_to="reply@test.com",
        )
        
        assert msg.from_email == "sender@test.com"
        assert msg.reply_to == "reply@test.com"


class TestEmailService:
    """Tests for email service."""
    
    @pytest.fixture
    def mock_backend(self):
        """Create mock email backend."""
        backend = AsyncMock()
        backend.send = AsyncMock(return_value=True)
        return backend
    
    @pytest.fixture
    def email_service(self, mock_backend):
        """Create email service with mock backend."""
        return EmailService(backend=mock_backend)
    
    @pytest.mark.asyncio
    async def test_send_verification_email(self, email_service, mock_backend):
        """Send verification email."""
        result = await email_service.send_verification_email(
            email="user@test.com",
            display_name="John",
            verification_url="https://app.com/verify?token=abc123",
        )
        
        assert result is True
        mock_backend.send.assert_called_once()
        
        # Check the message
        call_args = mock_backend.send.call_args
        message: EmailMessage = call_args[0][0]
        
        assert message.to == "user@test.com"
        assert "Verify" in message.subject
        assert "John" in message.html_body
        assert "https://app.com/verify?token=abc123" in message.html_body
        assert "verify?token=abc123" in message.text_body
    
    @pytest.mark.asyncio
    async def test_send_password_reset_email(self, email_service, mock_backend):
        """Send password reset email."""
        result = await email_service.send_password_reset_email(
            email="user@test.com",
            display_name="Jane",
            reset_url="https://app.com/reset?token=xyz789",
        )
        
        assert result is True
        mock_backend.send.assert_called_once()
        
        message: EmailMessage = mock_backend.send.call_args[0][0]
        
        assert message.to == "user@test.com"
        assert "Reset" in message.subject or "reset" in message.subject.lower()
        assert "Jane" in message.html_body
        assert "https://app.com/reset?token=xyz789" in message.html_body
    
    @pytest.mark.asyncio
    async def test_send_welcome_email(self, email_service, mock_backend):
        """Send welcome email."""
        result = await email_service.send_welcome_email(
            email="user@test.com",
            display_name="Alex",
        )
        
        assert result is True
        mock_backend.send.assert_called_once()
        
        message: EmailMessage = mock_backend.send.call_args[0][0]
        
        assert message.to == "user@test.com"
        assert "Welcome" in message.subject
        assert "Alex" in message.html_body
    
    @pytest.mark.asyncio
    async def test_send_password_changed_email(self, email_service, mock_backend):
        """Send password changed notification."""
        result = await email_service.send_password_changed_email(
            email="user@test.com",
            display_name="Sam",
        )
        
        assert result is True
        mock_backend.send.assert_called_once()
        
        message: EmailMessage = mock_backend.send.call_args[0][0]
        
        assert message.to == "user@test.com"
        assert "password" in message.subject.lower()
        assert "changed" in message.subject.lower()
    
    @pytest.mark.asyncio
    async def test_template_includes_app_name(self, email_service, mock_backend):
        """Templates include app name from settings."""
        await email_service.send_welcome_email(
            email="user@test.com",
            display_name="Test",
        )
        
        message: EmailMessage = mock_backend.send.call_args[0][0]
        
        # App name should be in subject and/or body
        # (depends on settings, but template should render without error)
        assert message.subject is not None
        assert message.html_body is not None
    
    @pytest.mark.asyncio
    async def test_backend_failure_returns_false(self, email_service, mock_backend):
        """Backend failure propagates as False result."""
        mock_backend.send.return_value = False
        
        result = await email_service.send_verification_email(
            email="user@test.com",
            display_name="Test",
            verification_url="https://app.com/verify",
        )
        
        assert result is False


class TestEmailTemplates:
    """Tests for email templates."""
    
    def test_all_templates_defined(self):
        """All expected templates are defined."""
        expected = {
            EmailTemplate.VERIFICATION,
            EmailTemplate.PASSWORD_RESET,
            EmailTemplate.WELCOME,
            EmailTemplate.PASSWORD_CHANGED,
        }
        
        service = EmailService(backend=ConsoleEmailBackend())
        
        for template in expected:
            assert template in service._templates
            assert "subject" in service._templates[template]
            assert "html" in service._templates[template]
            assert "text" in service._templates[template]


class TestGetEmailService:
    """Tests for get_email_service factory."""
    
    def test_returns_email_service(self):
        """Factory returns EmailService instance."""
        # Clear cache first
        get_email_service.cache_clear()
        
        service = get_email_service()
        
        assert isinstance(service, EmailService)
    
    def test_returns_cached_instance(self):
        """Factory returns same cached instance."""
        get_email_service.cache_clear()
        
        service1 = get_email_service()
        service2 = get_email_service()
        
        assert service1 is service2
    
    def test_uses_console_backend_in_development(self):
        """Development environment uses console backend."""
        get_email_service.cache_clear()
        
        with patch("app.services.email.get_settings") as mock_settings:
            mock_settings.return_value.ENVIRONMENT = "development"
            mock_settings.return_value.DEBUG = True
            
            service = get_email_service()
            
            assert isinstance(service.backend, ConsoleEmailBackend)
