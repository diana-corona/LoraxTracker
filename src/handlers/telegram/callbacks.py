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
telegram = TelegramClient()
dynamo = DynamoDBClient(os.environ['TRACKER_TABLE_NAME'])

def handle_callback_query(callback_query: Dict[str, Any]) -> Dict[str, Any]:
    """Handle callback queries from inline keyboards."""
    try:
        chat_id = str(callback_query["message"]["chat"]["id"])
        user_id = str(callback_query["from"]["id"])
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
