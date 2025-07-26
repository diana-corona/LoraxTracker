"""
Telegram /start command handler.
"""
import json
from typing import Dict, Any

from aws_lambda_powertools import Logger
from src.utils.telegram import TelegramClient

logger = Logger()
telegram = TelegramClient()

def handle_start_command(user_id: str, chat_id: str) -> Dict[str, Any]:
    """
    Handle /start command.
    
    For users in private chats, displays welcome message with available commands.
    For group chats, displays a simple welcome message.
    
    Args:
        user_id: Telegram user ID
        chat_id: Telegram chat ID
        
    Returns:
        Dict with API response
    """
    try:
        # Get chat info to determine if it's a group
        chat_info = telegram.get_chat(chat_id)
        is_group = chat_info.get('type') in ['group', 'supergroup'] or str(chat_id).startswith('-')
        
        # Log new interaction
        logger.info(
            "New interaction started",
            extra={
                "user_id": user_id,
                "chat_id": chat_id,
                "command": "/start",
                "chat_type": "group" if is_group else "private"
            }
        )
        
        if is_group:
            message = "Hi! I'm Lorax, your weekly planner assistant. 🌙"
        else:
            message = (
                "Hi! I'm Lorax, your menstrual cycle assistant. 🌙\n\n"
                "You can use these commands:\n"
                "/register YYYY-MM-DD - Register a cycle event\n"
                "/register YYYY-MM-DD to YYYY-MM-DD - Register events for a date range\n"
                "/phase - View your current phase\n"
                "/predict - View next cycle prediction\n"
                "/statistics - View your cycle statistics\n"
                "/mygroups - View your groups and partners"
            )
        
        telegram.send_message(chat_id=chat_id, text=message)
    
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({"ok": True, "result": True}),
            "isBase64Encoded": False
        }
        
    except Exception as e:
        logger.exception(
            "Error handling start command",
            extra={
                "user_id": user_id,
                "chat_id": chat_id,
                "error": str(e),
                "error_type": e.__class__.__name__
            }
        )
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({"ok": False, "error": "Internal server error"}),
            "isBase64Encoded": False
        }
