"""
Telegram /start command handler.
"""
import json
from typing import Dict, Any

from aws_lambda_powertools import Logger
from src.utils.clients import get_clients
from src.utils.telegram.command_definitions import get_start_message

logger = Logger()

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
        
        message = get_start_message(is_private_chat=not is_group)
        
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
