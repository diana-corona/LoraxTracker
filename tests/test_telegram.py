"""
Tests for Telegram command parsing.

These tests verify that the parse_command function correctly handles
both direct commands and group commands with bot username suffix.
"""
from src.utils.telegram.parsers import parse_command

def test_parse_command_basic():
    """Test parsing basic commands without arguments."""
    command, args = parse_command("/start")
    assert command == "/start"
    assert args == []

def test_parse_command_with_args():
    """Test parsing commands with arguments."""
    command, args = parse_command("/register 2025-02-15")
    assert command == "/register"
    assert args == ["2025-02-15"]

def test_parse_command_with_bot_username():
    """Test parsing group commands with bot username suffix."""
    command, args = parse_command("/start@LoraxTrackerBot")
    assert command == "/start"
    assert args == []

def test_parse_command_with_bot_username_and_args():
    """Test parsing group commands with bot username and arguments."""
    command, args = parse_command("/register@LoraxTrackerBot 2025-02-15 to 2025-02-17")
    assert command == "/register"
    assert args == ["2025-02-15", "to", "2025-02-17"]
