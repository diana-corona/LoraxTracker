"""
Parsing functions for Telegram bot messages and data.
"""
from typing import Dict, Any, List, Tuple
import json

def parse_command(text: str) -> tuple[str, List[str]]:
    """
    Parse command and arguments from message text.
    
    Args:
        text: Raw message text
        
    Returns:
        Tuple of (command, arguments)
    """
    parts = text.split()
    command = parts[0].lower()
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
