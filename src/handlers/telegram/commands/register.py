"""
Telegram /register command handler.
"""
import os
from typing import Dict, Any, List
from datetime import datetime

from aws_lambda_powertools import Logger
from src.utils.telegram import (
    TelegramClient,
    validate_date,
    validate_date_range,
    generate_dates_in_range
)
from src.utils.dynamo import DynamoDBClient, create_pk, create_event_sk
from src.models.event import CycleEvent

logger = Logger()
telegram = TelegramClient()
dynamo = DynamoDBClient(os.environ['TRACKER_TABLE_NAME'])

def handle_register_event(
    user_id: str,
    chat_id: str,
    date_str: str,
    args: List[str] = []
) -> Dict[str, Any]:
    """Handle /register command with optional date range."""
    if len(args) >= 3 and args[1].lower() == "to":
        # Handle date range
        end_date_str = args[2]
        
        start_date = validate_date(date_str)
        end_date = validate_date(end_date_str)
        
        if not start_date or not end_date:
            telegram.send_message(
                chat_id=chat_id,
                text="Invalid date format. Use: /register YYYY-MM-DD to YYYY-MM-DD"
            )
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "ok": False,
                    "error_code": 400,
                    "description": "Invalid date format"
                }),
                "isBase64Encoded": False
            }
            
        is_valid, error_msg = validate_date_range(start_date, end_date)
        if not is_valid:
            telegram.send_message(
                chat_id=chat_id,
                text=f"Invalid date range: {error_msg}"
            )
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "ok": False,
                    "error_code": 400,
                    "description": error_msg
                }),
                "isBase64Encoded": False
            }
            
        # Generate and store events for each date in range
        dates = generate_dates_in_range(start_date, end_date)
        for date_obj in dates:
            event = CycleEvent(
                user_id=user_id,
                date=date_obj.date(),
                state="menstruation"  # Default to menstruation event
            )
            
            # Convert date to ISO string format for DynamoDB storage
            event_data = event.model_dump()
            event_data['date'] = event_data['date'].isoformat()
            
            # Store in DynamoDB
            dynamo.put_item({
                "PK": create_pk(user_id),
                "SK": create_event_sk(date_obj.strftime("%Y-%m-%d")),
                **event_data
            })
        
        telegram.send_message(
            chat_id=chat_id,
            text=f"✅ Events registered for range {date_str} to {end_date_str}"
        )
        
    else:
        # Handle single date
        date_obj = validate_date(date_str)
        if not date_obj:
            telegram.send_message(
                chat_id=chat_id,
                text="Invalid date. Use YYYY-MM-DD format"
            )
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "ok": False,
                    "error_code": 400,
                    "description": "Invalid date format"
                }),
                "isBase64Encoded": False
            }
        
        event = CycleEvent(
            user_id=user_id,
            date=date_obj.date(),
            state="menstruation"  # Default to menstruation event
        )
        
        # Convert date to ISO string format for DynamoDB storage
        event_data = event.model_dump()
        event_data['date'] = event_data['date'].isoformat()
        
        # Store in DynamoDB
        dynamo.put_item({
            "PK": create_pk(user_id),
            "SK": create_event_sk(date_str),
            **event_data
        })
        
        telegram.send_message(
            chat_id=chat_id,
            text=f"✅ Event registered for {date_str}"
        )
    
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "ok": True,
            "result": {"message": "Event registered"}
        }),
        "isBase64Encoded": False
    }
