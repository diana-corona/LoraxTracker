"""
Main telegram webhook handler.
"""
import json
import requests
from typing import Dict, Any, List
from datetime import datetime

import os
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.logging import correlation_paths

from src.utils.telegram import (
    TelegramClient,
    parse_command,
    format_error_message
)
from src.utils.auth import DynamoDBAccessError
from src.utils.dynamo import get_dynamo
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

from src.utils.logging import logger, log_exception

tracer = Tracer(service="telegram_bot")

telegram = TelegramClient()
auth = Authorization(dynamo_client=get_dynamo())

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
    # Add lambda context keys
    logger.set_correlation_id(context.aws_request_id)
    logger.structure_logs(append=True, lambda_context={
        "function_version": context.function_version,
        "invoked_function_arn": context.invoked_function_arn,
        "aws_request_id": context.aws_request_id
    })
    
    # Log invocation
    logger.info("Lambda function invoked")
    
    try:
        # Log raw incoming event for debugging
        logger.debug("Received webhook event", extra={
            "webhook_event": event,
            "event_type": type(event).__name__,
            "has_body": "body" in event,
            "body_type": type(event.get("body")).__name__ if "body" in event else None
        })

        body = json.loads(event["body"])
        
        # Log parsed body
        logger.debug("Parsed webhook body", extra={
            "webhook_body": body,
            "body_keys": list(body.keys()) if isinstance(body, dict) else None,
            "message_type": "callback_query" if "callback_query" in body else "message" if "message" in body else "unknown"
        })
        
        # Extract message details and enhance logging
        user_id = None
        command = None
        
        # Extract user_id and details for both messages and callback queries
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
                "group_title": chat.get("title") if chat.get("type") in ["group", "supergroup"] else None,
                "telegram_message": body["message"],  # Log raw message for debugging
                "message_id": body["message"].get("message_id"),
                "date": body["message"].get("date")
            })
        elif "callback_query" in body:
            callback = body["callback_query"]
            user = callback["from"]
            chat = callback["message"]["chat"]
            user_id = str(user["id"])
            
        # Check for admin commands before authorization
        if command in ["/allow", "/revoke"] and user_id in os.environ.get("ADMIN_USER_IDS", "").split(","):
            logger.info(f"Admin command access: {command} by user {user_id}")
            return handle_message(body["message"])
        
        # For non-admin commands, apply authorization check silently
        try:
            if not auth.check_user_authorized(user_id):
                # Enhanced logging for unauthorized attempts, but no user response
                logger.warning("Unauthorized access attempt", extra={
                    "user_id": user_id,
                    "username": user.get("username", None),
                    "chat_id": str(chat["id"]),
                    "chat_type": chat.get("type", "private"),
                    "command": command,
                    "interaction_type": "callback_query" if "callback_query" in body else "message",
                    "group_title": chat.get("title") if chat.get("type") in ["group", "supergroup"] else None
                })
                # Return silent success to not reveal bot existence
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"ok": True})
                }
        except DynamoDBAccessError as e:
            # Log the error but maintain silence to unauthorized users
            logger.error("DynamoDB access error during authorization", extra={
                "user_id": user_id,
                "error": str(e),
                "command": command
            })
            # Return silent success despite the error
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": True})
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
                "group_title": chat.get("title") if chat.get("type") in ["group", "supergroup"] else None,
                "telegram_callback": callback,  # Log callback for debugging
                "message_id": callback["message"].get("message_id"),
                "callback_query_id": callback.get("id")
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
        log_exception(logger, "Error processing webhook", extra={
            "error_type": type(e).__name__,
            "error_details": str(e)
        })
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
        log_exception(logger, f"Error handling command {command}", extra={
            "command": command,
            "chat_id": chat_id,
            "error_type": type(e).__name__,
            "error_details": str(e)
        })
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
