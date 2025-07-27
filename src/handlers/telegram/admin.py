"""
Admin-related command handlers for Telegram bot.
"""
import os
from typing import Dict, Any, List

from aws_lambda_powertools import Logger
from src.utils.telegram import TelegramClient
from src.utils.auth import Authorization
from src.utils.dynamo import DynamoDBClient

logger = Logger()

# Initialize shared clients (lazy loading)
_dynamo = None
_telegram = None
_auth = None

def get_dynamo():
    """Get or create DynamoDB client."""
    global _dynamo
    if _dynamo is None:
        _dynamo = DynamoDBClient(os.environ['TRACKER_TABLE_NAME'])
    return _dynamo

def get_telegram():
    """Get or create Telegram client."""
    global _telegram
    if _telegram is None:
        _telegram = TelegramClient()
    return _telegram

def get_auth():
    """Get or create Authorization instance."""
    global _auth
    if _auth is None:
        _auth = Authorization()
    return _auth

# Helper function to get all clients
def get_clients():
    """Get all required clients."""
    return get_dynamo(), get_telegram(), get_auth()

def is_admin(user_id: str) -> bool:
    """
    Check if user is an admin.
    
    Args:
        user_id: Telegram user ID to check
        
    Returns:
        bool: True if user is an admin
    """
    admin_ids = os.environ.get("ADMIN_USER_IDS", "").split(",")
    return user_id in admin_ids

def handle_allow_command(user_id: str, chat_id: str, args: List[str]) -> Dict[str, Any]:
    """Handle /allow command for admins."""
    dynamo, telegram, auth = get_clients()
    if not args or len(args) != 2 or args[1] not in ["user", "partner", "group"]:
        return telegram.send_message(
            chat_id=chat_id,
            text=(
                "Usage: /allow <user_id> <type>\n"
                "Types: user, partner, group\n\n"
                "Examples:\n"
                "/allow 123456 user\n"
                "/allow 789012 partner\n"
                "/allow -100123456789 group"
            )
        )
    
    target_id, user_type = args
    auth.add_allowed_user(target_id, user_type, user_id)
    
    # Enhanced logging for group allowlist changes
    if user_type == "group":
        logger.info("Added group to allowlist", extra={
            "admin_id": user_id,
            "group_id": target_id,
            "action": "allow",
            "command": "/allow"
        })
    else:
        logger.info("Added user to allowlist", extra={
            "admin_id": user_id,
            "target_id": target_id,
            "user_type": user_type,
            "action": "allow",
            "command": "/allow"
        })
    
    return telegram.send_message(
        chat_id=chat_id,
        text=f"✅ Added {target_id} as {user_type}"
    )

def handle_revoke_command(user_id: str, chat_id: str, args: List[str]) -> Dict[str, Any]:
    """Handle /revoke command for admins."""
    dynamo, telegram, auth = get_clients()
    if not args:
        return telegram.send_message(
            chat_id=chat_id,
            text=(
                "Usage: /revoke <user_id>\n\n"
                "Example:\n"
                "/revoke 123456"
            )
        )
        
    target_id = args[0]
    auth.remove_allowed_user(target_id)
    
    # Log removal from allowlist
    logger.info("Removed from allowlist", extra={
        "admin_id": user_id,
        "target_id": target_id,
        "action": "revoke",
        "command": "/revoke"
    })
    
    return telegram.send_message(
        chat_id=chat_id,
        text=f"✅ Removed {target_id} from allow list"
    )
