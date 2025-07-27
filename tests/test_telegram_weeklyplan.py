"""Tests for weeklyplan command handler."""
from datetime import date, timedelta
import pytest
from unittest.mock import patch, Mock
import logging

from src.handlers.telegram.commands.weeklyplan import handle_weeklyplan_command
from src.models.phase import TraditionalPhaseType

@pytest.fixture(autouse=True)
def setup_logging():
    """Set up logging for tests."""
    logging.basicConfig(level=logging.INFO)

def test_weeklyplan_command_no_events():
    """Test weeklyplan command when user has no events."""
    # Mock update data
    update = {
        "message": {
            "chat": {"id": "123"},
            "from": {"id": "456"}
        }
    }
    
    # Mock dependencies
    mock_telegram = Mock()
    mock_telegram.send_message = Mock()
    mock_dynamo = Mock()
    mock_dynamo.query_items.return_value = []
    
    # Patch clients
    with patch('src.utils.clients._dynamo', mock_dynamo), \
         patch('src.utils.clients._telegram', mock_telegram), \
         patch('src.utils.clients.get_clients', return_value=(mock_dynamo, mock_telegram)):
        mock_dynamo.query_items.return_value = []
        
        # Execute command
        handle_weeklyplan_command(update)
        
        # Verify error message sent
        mock_telegram.send_message.assert_called_once_with(
            chat_id="123",
            text="⚠️ No cycle events found. Please register some events first."
        )

def test_weeklyplan_command_success():
    """Test successful weeklyplan command execution."""
    # Mock update data
    update = {
        "message": {
            "chat": {"id": "123"},
            "from": {"id": "456"}
        }
    }
    
    # Mock event data
    today = date.today()
    mock_events = [
        {
            "PK": "USER#456",
            "SK": "EVENT#2025-07-20",
            "user_id": "456",
            "date": (today - timedelta(days=5)).isoformat(),
            "state": TraditionalPhaseType.MENSTRUATION.value
        }
    ]
    
    # Mock dependencies
    mock_telegram = Mock()
    mock_telegram.send_message = Mock()
    mock_dynamo = Mock()
    mock_dynamo.query_items.return_value = mock_events
    
    # Patch clients
    with patch('src.utils.clients._dynamo', mock_dynamo), \
         patch('src.utils.clients._telegram', mock_telegram), \
         patch('src.utils.clients.get_clients', return_value=(mock_dynamo, mock_telegram)):
        mock_dynamo.query_items.return_value = mock_events
        
        # Execute command
        handle_weeklyplan_command(update)
        
        # Verify success
        mock_telegram.send_message.assert_called_once()
        
        # Verify message format
        call_args = mock_telegram.send_message.call_args[1]
        assert call_args["chat_id"] == "123"
        assert "📅 Next Week's Plan" in call_args["text"]
        assert "Phase Schedule" in call_args["text"]

def test_weeklyplan_command_unexpected_error():
    """Test weeklyplan command handling of unexpected errors."""
    # Mock update data
    update = {
        "message": {
            "chat": {"id": "123"},
            "from": {"id": "456"}
        }
    }
    
    # Mock dependencies
    mock_telegram = Mock()
    mock_telegram.send_message = Mock()
    mock_dynamo = Mock()
    mock_dynamo.query_items.side_effect = Exception("Unexpected error")
    
    # Patch clients
    with patch('src.utils.clients._dynamo', mock_dynamo), \
         patch('src.utils.clients._telegram', mock_telegram), \
         patch('src.utils.clients.get_clients', return_value=(mock_dynamo, mock_telegram)):
        mock_dynamo.query_items.side_effect = Exception("Unexpected error")
        
        # Execute command
        handle_weeklyplan_command(update)
        
        # Verify error message sent
        mock_telegram.send_message.assert_called_once_with(
            chat_id="123",
            text="Sorry, there was an error generating your weekly plan. Please try again later."
        )
