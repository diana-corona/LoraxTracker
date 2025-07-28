"""
Telegram callback query handlers.
"""
import json
from typing import Dict, Any

from aws_lambda_powertools import Logger
from src.utils.telegram import TelegramClient, format_error_message
from src.utils.dynamo import DynamoDBClient, create_pk

import os

logger = Logger()

# Initialize shared clients (lazy loading)
_dynamo = None
_telegram = None

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

def get_clients():
    """Get all required clients."""
    return get_dynamo(), get_telegram()

def handle_callback_query(callback_query: Dict[str, Any]) -> Dict[str, Any]:
    """Handle callback queries from inline keyboards."""
    try:
        # Get clients lazily
        dynamo, telegram = get_clients()
        chat_id = str(callback_query["message"]["chat"]["id"])
        user_id = str(callback_query["from"]["id"])
        # Handle recipe selection callbacks from weekly plan
        if "data" in callback_query and callback_query["data"].startswith("recipe_"):
            from .commands.weeklyplan import handle_recipe_callback
            # Convert any stringified JSON in body to dict
            if isinstance(callback_query.get("data"), str):
                try:
                    callback_query = callback_query.copy()
                    if callback_query["data"].startswith("recipe_"):
                        # Don't parse recipe callbacks as JSON
                        pass
                    else:
                        callback_query["data"] = json.loads(callback_query["data"])
                except json.JSONDecodeError:
                    pass
            
            # Wrap callback in a Lambda event structure for middleware
            wrapped_event = {
                "body": json.dumps({
                    "callback_query": callback_query
                })
            }
            return handle_recipe_callback(wrapped_event)
            
        data = json.loads(callback_query["data"])
        
        if data["action"] == "rate":
            return handle_rating(
                user_id,
                chat_id,
                data["recommendation_id"],
                data["value"]
            )
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "ok": False,
                "error_code": 400,
                "description": "Invalid callback action"
            }),
            "isBase64Encoded": False
        }
        
    except Exception as e:
        logger.exception("Error handling callback query")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

def handle_rating(
    user_id: str,
    chat_id: str,
    recommendation_id: str,
    rating: int
) -> Dict[str, Any]:
    """Handle recommendation rating callback."""
    try:
        # Get clients lazily
        dynamo, telegram = get_clients()
        # Update recommendation in DynamoDB
        dynamo.update_item(
            key={
                "PK": create_pk(user_id),
                "SK": f"REC#{recommendation_id}"
            },
            update_expression="SET effectiveness_rating = :r",
            expression_values={":r": rating}
        )
        
        telegram.send_message(
            chat_id=chat_id,
            text=f"Thanks for your rating! ({rating}⭐)"
        )
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "ok": True,
                "result": {"message": "Rating recorded"}
            }),
            "isBase64Encoded": False
        }
        
    except Exception as e:
        logger.exception("Error recording rating")
        telegram.send_message(
            chat_id=chat_id,
            text=format_error_message(e)
        )
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "ok": False,
                "error_code": 500,
                "description": str(e)
            }),
            "isBase64Encoded": False
        }
