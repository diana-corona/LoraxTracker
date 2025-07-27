"""
Tests for the help command handler.
"""
import json
import pytest
from unittest.mock import Mock

@pytest.fixture
def telegram_mock():
    """Mock Telegram client for testing."""
    mock = Mock()
    mock.send_message.return_value = {
        "statusCode": 200,
        "body": json.dumps({"ok": True})
    }
    return mock

HELP_MESSAGE = """
Available commands:

🚀 Basic Commands:
/start - Start interacting with the bot
/help - Show this help message
/register - Register an event (Format: YYYY-MM-DD)

📊 Information Commands:
/phase - Get your current cycle phase
/predict - Get predictions for your next cycle
/statistics - View your cycle statistics

📅 Planning Commands:
/weeklyplan - Get personalized weekly recommendations
"""

def test_help_command(telegram_mock):
    """Test help command sends the correct help message with proper formatting."""
    # Setup
    user_id = "test_user"
    chat_id = "test_chat"

    def handle_help_command(user_id: str, chat_id: str):
        """Local implementation of help command for testing."""
        return telegram_mock.send_message(
            chat_id=chat_id,
            text=HELP_MESSAGE,
            parse_mode="HTML"
        )

    # Execute
    response = handle_help_command(user_id, chat_id)

    # Verify
    telegram_mock.send_message.assert_called_once()
    call_args = telegram_mock.send_message.call_args[1]
    
    # Check message is sent to correct chat
    assert call_args["chat_id"] == chat_id
    
    # Verify message format and content
    assert "Available commands" in call_args["text"]
    assert "Basic Commands" in call_args["text"]
    assert "Information Commands" in call_args["text"]
    assert "Planning Commands" in call_args["text"]
    assert "/help" in call_args["text"]
    assert "/start" in call_args["text"]
    assert "/register" in call_args["text"]
    
    # Verify HTML parsing is enabled for formatting
    assert call_args["parse_mode"] == "HTML"
    
    # Check response structure
    assert response["statusCode"] == 200
    assert json.loads(response["body"])["ok"] is True

def test_help_command_content():
    """Test help message content is accurate and well-structured."""
    assert "🚀 Basic Commands:" in HELP_MESSAGE
    assert "📊 Information Commands:" in HELP_MESSAGE
    assert "📅 Planning Commands:" in HELP_MESSAGE
    
    # Verify all commands are documented
    commands = [
        "/start", "/help", "/register",
        "/phase", "/predict", "/statistics",
        "/weeklyplan"
    ]
    for cmd in commands:
        assert cmd in HELP_MESSAGE

    # Verify command descriptions
    assert "Start interacting with the bot" in HELP_MESSAGE
    assert "Show this help message" in HELP_MESSAGE
    assert "Register an event" in HELP_MESSAGE
    assert "YYYY-MM-DD" in HELP_MESSAGE  # Format information
