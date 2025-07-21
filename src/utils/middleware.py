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
            # Extract user ID from event
            body = event.get("body", {})
            if isinstance(body, str):
                import json
                body = json.loads(body)
                
            user_id = None
            if "message" in body:
                user_id = str(body["message"]["from"]["id"])
            elif "callback_query" in body:
                user_id = str(body["callback_query"]["from"]["id"])
                
            if not user_id:
                raise AuthorizationError("Could not determine user ID")
                
            # Parse command if it's a message
            command = None
            if "message" in body and body["message"].get("text"):
                text = body["message"]["text"]
                if text.startswith('/'):
                    command = text.split()[0]

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
                logger.warning(f"Unauthorized access attempt from user {user_id}")
                return {
                    "statusCode": 200,  # Return 200 to avoid Telegram retries
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({
                        "ok": True,  # Tell Telegram the message was handled
                        "result": True
                    })
                }
            
            # User is authorized, proceed with handler
            return f(event, *args, **kwargs)
            
        except Exception as e:
            logger.exception("Error in authorization")
            return {
                "statusCode": 200,  # Return 200 to avoid Telegram retries
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "ok": True,  # Tell Telegram the message was handled
                    "result": True
                })
            }
    
    return wrapped
