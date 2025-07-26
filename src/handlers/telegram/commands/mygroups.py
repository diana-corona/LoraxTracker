"""
Telegram /mygroups command handler.

Displays user's group chat and partner information in private chats.
"""
import json
from typing import Dict, Any

from aws_lambda_powertools import Logger
from src.utils.telegram import TelegramClient
from src.models.user import User
from src.utils.dynamo import get_item

logger = Logger()
telegram = TelegramClient()

def handle_mygroups_command(user_id: str, chat_id: str) -> Dict[str, Any]:
    """
    Handle /mygroups command.
    
    Displays user's associated group chat and partner information.
    Only works in private chats.
    
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
        
        # Log command usage
        logger.info(
            "Mygroups command received",
            extra={
                "user_id": user_id,
                "chat_id": chat_id,
                "command": "/mygroups",
                "chat_type": "group" if is_group else "private"
            }
        )

        # Command only works in private chats
        if is_group:
            message = "This command only works in private chats."
            telegram.send_message(chat_id=chat_id, text=message)
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": True, "result": True}),
                "isBase64Encoded": False
            }

        # Get user data
        user_data = get_item('users', {'user_id': user_id})
        if not user_data:
            message = "You are not registered in the system."
            telegram.send_message(chat_id=chat_id, text=message)
            return {
                "statusCode": 404,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": False, "error": "User not found"}),
                "isBase64Encoded": False
            }

        user = User(**user_data)
        
        # Build response message
        message_parts = ["Your Groups and Partners:\n"]
        
        # Add group information if available
        if user.chat_id_group:
            try:
                group_info = telegram.get_chat(user.chat_id_group)
                group_name = group_info.get('title', 'Unknown Group')
                message_parts.append(f"Group Chat: {group_name}")
            except Exception as e:
                logger.warning(
                    "Failed to get group info",
                    extra={
                        "user_id": user_id,
                        "group_id": user.chat_id_group,
                        "error": str(e)
                    }
                )
                message_parts.append("Group Chat: Unable to fetch group name")
        else:
            message_parts.append("Group Chat: None")

        # Add partner information if available
        if user.partner_id:
            try:
                partner_data = get_item('users', {'user_id': user.partner_id})
                if partner_data:
                    partner = User(**partner_data)
                    partner_name = partner.name or "Unknown Partner"
                    message_parts.append(f"Partner: {partner_name}")
                else:
                    message_parts.append("Partner: Unable to fetch partner info")
            except Exception as e:
                logger.warning(
                    "Failed to get partner info",
                    extra={
                        "user_id": user_id,
                        "partner_id": user.partner_id,
                        "error": str(e)
                    }
                )
                message_parts.append("Partner: Unable to fetch partner info")
        else:
            message_parts.append("Partner: None")

        # If no group or partner, add a note
        if not user.chat_id_group and not user.partner_id:
            message_parts.append("\nNote: You haven't been added to any groups or assigned any partners yet.")
        
        # Send the message
        telegram.send_message(chat_id=chat_id, text="\n".join(message_parts))
        
        logger.info(
            "Mygroups command completed successfully",
            extra={
                "user_id": user_id,
                "has_group": bool(user.chat_id_group),
                "has_partner": bool(user.partner_id)
            }
        )

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"ok": True, "result": True}),
            "isBase64Encoded": False
        }
        
    except Exception as e:
        logger.exception(
            "Error handling mygroups command",
            extra={
                "user_id": user_id,
                "chat_id": chat_id,
                "error": str(e),
                "error_type": e.__class__.__name__
            }
        )
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"ok": False, "error": "Internal server error"}),
            "isBase64Encoded": False
        }
