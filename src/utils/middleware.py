"""
Middleware functions for request processing.
"""
import os
from functools import wraps
from typing import Any, Callable, Dict

from aws_lambda_powertools import Logger
from src.utils.auth import Authorization, AuthorizationError
from src.utils.telegram import TelegramClient

logger = Logger()
auth = Authorization()
telegram = TelegramClient()

def require_auth(f: Callable) -> Callable:
    """
    Decorator to require authorization for handlers.
    
    Args:
        f: Handler function to wrap
        
    Returns:
        Wrapped handler function
    """
    @wraps(f)
    def wrapped(event: Dict[str, Any], *args: Any, **kwargs: Any) -> Dict[str, Any]:
        try:
            # Extract user ID from event or callback query
            user_id = None
            
            logger.debug("Processing auth middleware", extra={
                "event_type": type(event).__name__,
                "is_dict": isinstance(event, dict),
                "has_from": isinstance(event, dict) and "from" in event,
                "has_body": isinstance(event, dict) and "body" in event
            })
            
            if isinstance(event, dict):
                # If it's a callback query directly
                if "from" in event:
                    user_id = str(event["from"]["id"])
                    logger.debug("Extracted user ID from callback query", extra={
                        "user_id": user_id
                    })
                # If it's a Lambda event
                else:
                    body = event.get("body", {})
                    if isinstance(body, str):
                        import json
                        body = json.loads(body)
                    
                    if "message" in body:
                        user_id = str(body["message"]["from"]["id"])
                        logger.debug("Extracted user ID from message body", extra={
                            "user_id": user_id
                        })
                    elif "callback_query" in body:
                        user_id = str(body["callback_query"]["from"]["id"])
                        logger.debug("Extracted user ID from callback query body", extra={
                            "user_id": user_id
                        })
                
            if not user_id:
                logger.error("Failed to extract user ID", extra={
                    "event_type": type(event).__name__,
                    "event_keys": list(event.keys()) if isinstance(event, dict) else None
                })
                raise AuthorizationError("Could not determine user ID")
                
            # Parse command if it's a message (from Lambda event)
            command = None
            if isinstance(event, dict):
                if "message" in event:
                    # Direct message object
                    text = event["message"].get("text", "")
                    if text.startswith('/'):
                        command = text.split()[0]
                elif "body" in event and isinstance(event["body"], dict):
                    # Lambda event body
                    if "message" in event["body"]:
                        text = event["body"]["message"].get("text", "")
                        if text.startswith('/'):
                            command = text.split()[0]
                elif "body" in event and isinstance(event["body"], str):
                    # Lambda event with string body
                    try:
                        body = json.loads(event["body"])
                        if "message" in body:
                            text = body["message"].get("text", "")
                            if text.startswith('/'):
                                command = text.split()[0]
                    except json.JSONDecodeError:
                        pass

            # Allow admin commands for admin users, bypass auth check
            admin_ids = [id.strip() for id in os.environ.get("ADMIN_USER_IDS", "").split(",")]
            logger.info(f"Admin IDs from env: {admin_ids}")
            logger.info(f"Current user ID: {user_id}")
            logger.info(f"Current command: {command}")
            logger.info(f"Raw env value: {os.environ.get('ADMIN_USER_IDS')}")
            logger.info(f"Is admin check: {user_id in admin_ids}")
            logger.info(f"Is admin command: {command in ['/allow', '/revoke']}")
            
            if command in ["/allow", "/revoke"] and str(user_id) in admin_ids:
                logger.info("Admin command check passed")
                logger.info(f"Command: {command}")
                logger.info(f"User ID: {user_id}")
                logger.info("User is admin, bypassing auth check")
                return f(event, *args, **kwargs)
                
            # Check authorization for non-admin commands
            if not auth.check_user_authorized(user_id):
                logger.warning("Unauthorized access attempt", extra={
                    "user_id": user_id,
                    "command": command,
                    "event_type": "callback" if "from" in event else "message"
                })
                # Return silent success response
                return {
                    "statusCode": 200,  # Return 200 to avoid Telegram retries
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({
                        "ok": True  # Standard Telegram API success response
                    }),
                    "isBase64Encoded": False
                }
            
            # User is authorized, proceed with handler
            return f(event, *args, **kwargs)
            
        except Exception as e:
            logger.exception("Error in authorization middleware", extra={
                "error": str(e),
                "error_type": e.__class__.__name__,
                "event_type": type(event).__name__
            })
            return {
                "statusCode": 200,  # Return 200 to avoid Telegram retries
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "ok": True  # Silent success response
                }),
                "isBase64Encoded": False
            }
    
    return wrapped
