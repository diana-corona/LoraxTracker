"""
Tests for Telegram utilities and handlers.
"""
import pytest
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, ANY
from typing import List, Dict, Any

import pytest
from src.models.recommendation import RecommendationType

# Set up test environment variables
os.environ['TRACKER_TABLE_NAME'] = 'test-table'
os.environ['TELEGRAM_BOT_TOKEN'] = 'test-token'

from src.utils.telegram import (
    validate_date,
    validate_date_range,
    generate_dates_in_range,
    TelegramClient
)
from src.handlers.telegram import handle_register_event
from src.models.event import CycleEvent

def test_validate_date_range_valid():
    """Test valid date range validation."""
    start_date = datetime(2025, 2, 15)
    end_date = datetime(2025, 2, 20)
    
    is_valid, error_msg = validate_date_range(start_date, end_date)
    
    assert is_valid is True
    assert error_msg is None

def test_validate_date_range_invalid_order():
    """Test date range validation with end date before start date."""
    start_date = datetime(2025, 2, 20)
    end_date = datetime(2025, 2, 15)
    
    is_valid, error_msg = validate_date_range(start_date, end_date)
    
    assert is_valid is False
    assert error_msg == "Start date must be before end date"

def test_validate_date_range_too_long():
    """Test date range validation with range > 31 days."""
    start_date = datetime(2025, 2, 1)
    end_date = datetime(2025, 3, 5)  # 32 days
    
    is_valid, error_msg = validate_date_range(start_date, end_date)
    
    assert is_valid is False
    assert error_msg == "Date range cannot exceed 31 days"

def test_generate_dates_in_range():
    """Test date range generation."""
    start_date = datetime(2025, 2, 15)
    end_date = datetime(2025, 2, 17)
    
    dates = generate_dates_in_range(start_date, end_date)
    
    assert len(dates) == 3
    assert dates[0] == start_date
    assert dates[1] == datetime(2025, 2, 16)
    assert dates[2] == end_date

@patch('src.handlers.telegram.telegram')
@patch('src.handlers.telegram.dynamo')
def test_handle_register_event_single_date(mock_dynamo, mock_telegram, sample_user):
    """Test registering a single date event."""
    chat_id = "test_chat"
    date_str = "2025-02-15"
    args = [date_str]
    
    handle_register_event(sample_user.user_id, chat_id, date_str, args)
    
    # Verify DynamoDB put_item was called once with correct data
    mock_dynamo.put_item.assert_called_once()
    put_item_args = mock_dynamo.put_item.call_args[0][0]
    assert put_item_args['SK'].endswith(date_str)
    
    # Verify success message was sent
    mock_telegram.send_message.assert_called_once_with(
        chat_id=chat_id,
        text=f"✅ Event registered for {date_str}"
    )

@patch('src.handlers.telegram.telegram')
@patch('src.handlers.telegram.dynamo')
def test_handle_register_event_date_range(mock_dynamo, mock_telegram, sample_user):
    """Test registering events for a date range."""
    chat_id = "test_chat"
    start_date = "2025-02-15"
    end_date = "2025-02-17"
    args = [start_date, "to", end_date]
    
    handle_register_event(sample_user.user_id, chat_id, start_date, args)
    
    # Verify DynamoDB put_item was called three times (one for each date)
    assert mock_dynamo.put_item.call_count == 3
    
    # Verify the SK values for each put_item call
    calls = mock_dynamo.put_item.call_args_list
    assert calls[0][0][0]['SK'].endswith('2025-02-15')
    assert calls[1][0][0]['SK'].endswith('2025-02-16')
    assert calls[2][0][0]['SK'].endswith('2025-02-17')
    
    # Verify success message was sent
    mock_telegram.send_message.assert_called_once_with(
        chat_id=chat_id,
        text=f"✅ Events registered for range {start_date} to {end_date}"
    )

@patch('src.handlers.telegram.telegram')
@patch('src.handlers.telegram.dynamo')
def test_handle_register_event_invalid_range(mock_dynamo, mock_telegram, sample_user):
    """Test registering events with invalid date range."""
    chat_id = "test_chat"
    start_date = "2025-02-20"
    end_date = "2025-02-15"  # Before start date
    args = [start_date, "to", end_date]
    
    handle_register_event(sample_user.user_id, chat_id, start_date, args)
    
    # Verify DynamoDB put_item was not called
    mock_dynamo.put_item.assert_not_called()
    
    # Verify error message was sent
    mock_telegram.send_message.assert_called_once_with(
        chat_id=chat_id,
        text="Invalid date range: Start date must be before end date"
    )

@patch('src.handlers.telegram.telegram')
@patch('src.handlers.telegram.dynamo')
def test_handle_register_event_invalid_format(mock_dynamo, mock_telegram, sample_user):
    """Test registering events with invalid date format."""
    chat_id = "test_chat"
    start_date = "2025-13-45"  # Invalid date
    end_date = "2025-02-17"
    args = [start_date, "to", end_date]
    
    handle_register_event(sample_user.user_id, chat_id, start_date, args)
    
    # Verify DynamoDB put_item was not called
    mock_dynamo.put_item.assert_not_called()
    
    # Verify error message was sent
    mock_telegram.send_message.assert_called_once_with(
        chat_id=chat_id,
        text="Invalid date format. Use: /register YYYY-MM-DD to YYYY-MM-DD"
    )

def test_validate_date_valid():
    """Test valid date validation."""
    date_str = "2025-02-15"
    result = validate_date(date_str)
    
    assert result is not None
    assert result.year == 2025
    assert result.month == 2
    assert result.day == 15

def test_validate_date_invalid():
    """Test invalid date validation."""
    invalid_dates = [
        "2025-13-45",  # Invalid month/day
        "2025/02/15",  # Wrong format
        "15-02-2025",  # Wrong order
        "abc",         # Not a date
    ]
    
    for date_str in invalid_dates:
        result = validate_date(date_str)
        assert result is None

def test_send_recommendation(monkeypatch):
    """Test sending formatted recommendations."""
    # Mock the Telegram API request
    mock_response = Mock()
    mock_response.json.return_value = {"ok": True}
    monkeypatch.setattr("requests.post", lambda *args, **kwargs: mock_response)
    
    # Create test recommendations
    recommendations = [
        RecommendationType(
            category="exercise",
            priority=3,
            description="Do gentle stretching"
        ),
        RecommendationType(
            category="nutrition",
            priority=2,
            description="Increase iron-rich foods"
        )
    ]
    
    client = TelegramClient()
    result = client.send_recommendation("test_chat", recommendations)
    
    # Verify the message was formatted correctly
    expected_text = (
        "🌙 Recomendaciones personalizadas:\n\n"
        "⭐⭐⭐\n"
        "<b>Exercise</b>\n"
        "Do gentle stretching\n\n"
        "⭐⭐\n"
        "<b>Nutrition</b>\n"
        "Increase iron-rich foods\n"
    )
    
    # Verify API call with correctly formatted message
    mock_response.json.assert_called_once()
    assert result["statusCode"] == 200
    assert "ok" in json.loads(result["body"])
    
    # Verify the message format sent to Telegram API
    requests_call_args = next(iter(mock_response.mock_calls)).args[0]
    assert requests_call_args["text"] == expected_text
    assert requests_call_args["chat_id"] == "test_chat"
    assert requests_call_args["parse_mode"] == "HTML"
