"""
Telegram /start command handler.
"""
import json
from typing import Dict, Any

from aws_lambda_powertools import Logger
from src.utils.clients import get_clients

logger = Logger()

# Add help command to the list
START_MESSAGE_PRIVATE = (
    "Hi! I'm Lorax, your menstrual cycle assistant. 🌙\n\n"
    "You can use these commands:\n"
    "/help - Show all available commands\n"
    "/register YYYY-MM-DD - Register a cycle event\n"
    "/register YYYY-MM-DD to YYYY-MM-DD - Register events for a date range\n"
    "/phase - View your current phase\n"
    "/predict - View next cycle prediction\n"
    "/statistics - View your cycle statistics\n"
    "/mygroups - View your groups and partners"
)

START_MESSAGE_GROUP = "Hi! I'm Lorax, your weekly planner assistant. 🌙"

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
        # Check if it's a group chat based on chat_id format (groups start with -)
        is_group = str(chat_id).startswith('-')
        
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
        
        message = START_MESSAGE_GROUP if is_group else START_MESSAGE_PRIVATE
        
        # Get clients lazily
        dynamo, telegram = get_clients()
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
