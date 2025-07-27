"""
Parsing functions for Telegram bot messages and data.
"""
from typing import Dict, Any, List, Tuple
import json

def parse_command(text: str) -> tuple[str, List[str]]:
    """
    Parse command and arguments from message text.
    
    Handles both direct commands (/start) and group commands with bot username
    (/start@BotUsername). The @BotUsername suffix is stripped from the command
    for consistent handling.
    
    Args:
        text: Raw message text from Telegram update
            Examples:
                "/start"
                "/start@MyBot argument1 argument2"
                "/help@BotUsername"
    
    Returns:
        Tuple of (command, arguments) where:
            - command is the normalized command string (e.g., "/start")
            - arguments is a list of argument strings
    
    Example:
        >>> parse_command("/start@MyBot arg1")
        ("/start", ["arg1"])
        >>> parse_command("/help")
        ("/help", [])
    """
    parts = text.split()
    # Extract and normalize command by removing any @BotUsername suffix
    command = parts[0].lower().split('@')[0]
    args = parts[1:] if len(parts) > 1 else []
    
    return command, args

def parse_callback_data(callback_data: str) -> Dict[str, Any]:
    """
    Parse callback data from button presses.
    
    Args:
        callback_data: JSON string from callback query
        
    Returns:
        Parsed callback data
    """
    try:
        return json.loads(callback_data)
    except json.JSONDecodeError:
        return {"action": callback_data}
