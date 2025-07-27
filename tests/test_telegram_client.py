"""
Tests for the TelegramClient class.
"""
import os
import pytest
import requests
import responses
from src.utils.telegram.client import TelegramClient

@pytest.fixture
def telegram_client():
    """Create a TelegramClient instance for testing."""
    os.environ["TELEGRAM_BOT_TOKEN"] = "test_token"
    return TelegramClient()

@responses.activate
def test_get_chat(telegram_client):
    """Test get_chat method."""
    chat_id = "123456"
    expected_response = {
        "ok": True,
        "result": {
            "id": 123456,
            "type": "group",
            "title": "Test Group"
        }
    }
    
    responses.add(
        responses.GET,
        f"https://api.telegram.org/bottest_token/getChat",
        json=expected_response,
        status=200
    )
    
    result = telegram_client.get_chat(chat_id)
    assert result == expected_response["result"]
    assert result["type"] == "group"
    assert result["title"] == "Test Group"

@responses.activate
def test_get_chat_error(telegram_client):
    """Test get_chat method handles errors."""
    chat_id = "invalid_id"
    error_response = {
        "ok": False,
        "error_code": 400,
        "description": "Bad Request: chat not found"
    }
    
    responses.add(
        responses.GET,
        f"https://api.telegram.org/bottest_token/getChat",
        json=error_response,
        status=400
    )
    
    with pytest.raises(requests.exceptions.HTTPError):
        telegram_client.get_chat(chat_id)
