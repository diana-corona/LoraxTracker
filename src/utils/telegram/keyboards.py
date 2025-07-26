"""
Keyboard creation functions for Telegram bot.
"""
from typing import Dict, List
import json

def create_inline_keyboard(
    buttons: List[List[Dict[str, str]]]
) -> Dict[str, List[List[Dict[str, str]]]]:
    """
    Create an inline keyboard markup.
    
    Args:
        buttons: List of button rows with text and callback data
        
    Returns:
        Keyboard markup dictionary
    """
    return {
        "inline_keyboard": buttons
    }

def create_rating_keyboard() -> Dict[str, List[List[Dict[str, str]]]]:
    """Create rating keyboard with 1-5 stars."""
    buttons = [[{
        "text": "⭐" * i,
        "callback_data": json.dumps({
            "action": "rate",
            "value": i
        })
    } for i in range(1, 6)]]
    
    return {
        "inline_keyboard": buttons
    }
