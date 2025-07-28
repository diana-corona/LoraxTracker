"""
Main telegram webhook handler.
"""
import json
import requests
from typing import Dict, Any, List
from datetime import datetime

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from src.utils.telegram import (
    TelegramClient,
    parse_command,
    format_error_message
)
from src.utils.dynamo import DynamoDBClient
from src.utils.auth import Authorization
from src.models.event import CycleEvent
from .admin import is_admin, handle_allow_command, handle_revoke_command
from .commands import (
    handle_start_command,
    handle_register_event,
    handle_phase_command,
    handle_prediction_command,
    handle_statistics_command,
    handle_weeklyplan_command,
    handle_help_command,
    handle_history_command
)
from .callbacks import handle_callback_query

logger = Logger()
tracer = Tracer()

import os

dynamo = DynamoDBClient(os.environ['TRACKER_TABLE_NAME'])
telegram = TelegramClient()
auth = Authorization()

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Handle incoming Telegram webhook requests.
    
    Args:
        event: API Gateway Lambda proxy event
        context: Lambda context
        
    Returns:
        API Gateway Lambda proxy response
    """
    try:
        body = json.loads(event["body"])
        
        # Extract message details and enhance logging
        user_id = None
        command = None
        
        if "message" in body:
            chat = body["message"]["chat"]
            user = body["message"]["from"]
            text = body["message"].get("text", "")
            
            user_id = str(user["id"])
            if text.startswith('/'):
                command = text.split()[0]
                
            # Enhanced logging for all messages
            logger.info("Received message", extra={
                "user_id": user_id,
                "username": user.get("username"),
                "chat_id": str(chat["id"]),
                "chat_type": chat.get("type", "private"),
                "message_type": "command" if text.startswith('/') else "text",
                "command": command,
                "group_title": chat.get("title") if chat.get("type") in ["group", "supergroup"] else None
            })
            
        # Check for admin commands before authorization
        if command in ["/allow", "/revoke"] and user_id in os.environ.get("ADMIN_USER_IDS", "").split(","):
            logger.info(f"Admin command access: {command} by user {user_id}")
            return handle_message(body["message"])
        
        # For non-admin commands, apply authorization check
        if not auth.check_user_authorized(user_id):
            logger.warning("Unauthorized access attempt", extra={
                "user_id": user_id,
                "username": user.get("username") if "message" in body else None,
                "chat_id": str(chat["id"]) if "message" in body else None,
                "chat_type": chat.get("type", "private") if "message" in body else None,
                "command": command,
                "group_title": chat.get("title") if "message" in body and chat.get("type") in ["group", "supergroup"] else None
            })
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": True, "result": True})
            }
        
        # Handle callback queries (button presses)
        if "callback_query" in body:
            callback = body["callback_query"]
            user = callback["from"]
            chat = callback["message"]["chat"]
            
            # Enhanced logging for callback queries
            logger.info("Received callback query", extra={
                "user_id": str(user["id"]),
                "username": user.get("username"),
                "chat_id": str(chat["id"]),
                "chat_type": chat.get("type", "private"),
                "callback_data": callback["data"],
                "group_title": chat.get("title") if chat.get("type") in ["group", "supergroup"] else None
            })
            
            return handle_callback_query(callback)
            
        # Handle text messages
        if "message" in body:
            return handle_message(body["message"])
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({"ok": True, "result": True}),
            "isBase64Encoded": False
        }
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            # Propagate 429 status to trigger Telegram's retry mechanism
            return {
                "statusCode": 429,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": False, "error_code": 429, "description": "Rate limit exceeded"})
            }
        raise
    except Exception as e:
        logger.exception("Error processing webhook")
        return {
            "statusCode": 200,  # Keep 200 for other errors to avoid infinite retries
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"ok": False, "error_code": 500, "description": str(e)})
        }

def handle_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """Handle incoming text messages."""
    chat_id = str(message["chat"]["id"])
    user_id = str(message["from"]["id"])
    text = message.get("text", "")
    
    if not text:
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "ok": False,
                    "error_code": 400,
                    "description": "No text in message"
                })
            }
    
    command, args = parse_command(text)
    
    try:
        # Admin commands
        if command == "/allow" and is_admin(user_id):
            return handle_allow_command(user_id, chat_id, args)
        elif command == "/revoke" and is_admin(user_id):
            return handle_revoke_command(user_id, chat_id, args)
            
        # Regular commands
        if command == "/start":
            return handle_start_command(user_id, chat_id)
            
        elif command == "/register":
            if not args:
                return telegram.send_message(
                    chat_id=chat_id,
                    text="Please provide a date in YYYY-MM-DD format"
                )
            return handle_register_event(user_id, chat_id, args[0], args)
            
        elif command == "/phase":
            return handle_phase_command(user_id, chat_id)
            
        elif command == "/predict":
            return handle_prediction_command(user_id, chat_id)
            
        elif command == "/statistics":
            return handle_statistics_command(user_id, chat_id)
            
        elif command == "/weeklyplan":
            return handle_weeklyplan_command(user_id, chat_id)
            
        elif command == "/help":
            return handle_help_command(user_id, chat_id)
            
        elif command == "/history":
            return handle_history_command(user_id, chat_id)
            
        else:
            return telegram.send_message(
                chat_id=chat_id,
                text="Unrecognized command. Use /help to see available commands."
            )
            
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            # Propagate 429 status to trigger Telegram's retry mechanism
            return {
                "statusCode": 429,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": False, "error_code": 429, "description": "Rate limit exceeded"})
            }
        raise
    except Exception as e:
        logger.exception(f"Error handling command {command}")
        telegram.send_message(
            chat_id=chat_id,
            text=format_error_message(e)
        )
        return {
            "statusCode": 200,  # Keep 200 for other errors to avoid infinite retries
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "ok": False,
                "error_code": 500,
                "description": str(e)
            }),
            "isBase64Encoded": False
        }
