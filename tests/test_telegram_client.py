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


@responses.activate
def test_edit_message_reply_markup_success(telegram_client):
    """Test successful edit of message reply markup (keyboard only)."""
    chat_id = "123"
    message_id = 42
    keyboard = {"inline_keyboard": [[{"text": "Btn", "callback_data": "cb"}]]}

    expected_response = {
        "ok": True,
        "result": {
            "message_id": message_id,
            "chat": {"id": int(chat_id), "type": "private"},
            "reply_markup": keyboard
        }
    }

    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest_token/editMessageReplyMarkup",
        json=expected_response,
        status=200
    )

    resp = telegram_client.edit_message_reply_markup(
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=keyboard
    )
    assert resp["statusCode"] == 200
    # Verify request payload
    sent = responses.calls[0].request.body
    assert b'"chat_id": "123"' in sent
    assert b'"message_id": 42' in sent
    assert b'callback_data' in sent


@responses.activate
def test_edit_message_reply_markup_error(telegram_client):
    """Test error handling for edit_message_reply_markup."""
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest_token/editMessageReplyMarkup",
        json={"ok": False, "error_code": 400, "description": "Bad Request"},
        status=400
    )
    with pytest.raises(requests.exceptions.HTTPError):
        telegram_client.edit_message_reply_markup(
            chat_id="123",
            message_id=1,
            reply_markup={"inline_keyboard": []}
        )


@responses.activate
def test_edit_message_text_success(telegram_client):
    """Test successful edit of message text (and optional keyboard)."""
    chat_id = "123"
    message_id = 55
    new_text = "Updated text"
    keyboard = {"inline_keyboard": [[{"text": "X", "callback_data": "x"}]]}

    expected_response = {
        "ok": True,
        "result": {
            "message_id": message_id,
            "chat": {"id": int(chat_id), "type": "private"},
            "text": new_text
        }
    }

    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest_token/editMessageText",
        json=expected_response,
        status=200
    )

    resp = telegram_client.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=new_text,
        reply_markup=keyboard
    )
    assert resp["statusCode"] == 200
    sent = responses.calls[0].request.body
    assert b'"text": "Updated text"' in sent
    assert b'"parse_mode": "Markdown"' in sent  # default parse_mode used
    assert b'callback_data' in sent


@responses.activate
def test_edit_message_text_error(telegram_client):
    """Test error handling for edit_message_text."""
    responses.add(
        responses.POST,
        "https://api.telegram.org/bottest_token/editMessageText",
        json={"ok": False, "error_code": 400, "description": "Bad Request"},
        status=400
    )
    with pytest.raises(requests.exceptions.HTTPError):
        telegram_client.edit_message_text(
            chat_id="123",
            message_id=99,
            text="Bad",
            reply_markup=None
        )
