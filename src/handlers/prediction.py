"""
Lambda handler for cycle predictions.
"""
from typing import Dict
import json

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from src.utils.dynamo import DynamoDBClient, create_pk
from src.utils.telegram import TelegramClient, format_error_message
from src.utils.middleware import require_auth
from src.utils.auth import Authorization
from src.models.event import CycleEvent
from src.services.cycle import calculate_next_cycle

logger = Logger()
tracer = Tracer()

import os

dynamo = DynamoDBClient(f"TrackerTable-{os.environ.get('STAGE', 'dev')}")
telegram = TelegramClient()
auth = Authorization()

@logger.inject_lambda_context
@tracer.capture_lambda_handler
@require_auth
async def handler(event: Dict, context: LambdaContext) -> Dict:
    """
    Handle prediction request.
    
    Args:
        event: API Gateway Lambda proxy event
        context: Lambda context
        
    Returns:
        API Gateway Lambda proxy response
    """
    try:
        body = json.loads(event["body"])
        user_id = body.get("user_id")
        chat_id = body.get("chat_id")
        
        if not user_id or not chat_id:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "Missing user_id or chat_id"
                })
            }
        
        # Get user's events
        events = dynamo.query_items(
            partition_key="PK",
            partition_value=create_pk(user_id)
        )
        
        if not events:
            await telegram.send_message(
                chat_id=chat_id,
                text="No events found. Use /register to add cycle events."
            )
            return {
                "statusCode": 404,
                "body": json.dumps({
                    "error": "No events found"
                })
            }
            
        # Convert to CycleEvent objects
        cycle_events = [
            CycleEvent(**event)
            for event in events
            if event["SK"].startswith("EVENT#")
        ]
        
        # Calculate prediction
        next_date, duration, warning = calculate_next_cycle(cycle_events)
        
        # Format message
        message = [
            f"🔮 Next cycle expected: {next_date}",
            f"📊 Average duration: {duration} days"
        ]
        
        if warning:
            message.append(f"⚠️ {warning}")
        
        # Send prediction
        await telegram.send_message(
            chat_id=chat_id,
            text="\n".join(message)
        )
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Prediction sent",
                "user_id": user_id,
                "next_date": next_date,
                "duration": duration
            })
        }
        
    except Exception as e:
        logger.exception("Error calculating prediction")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e)
            })
        }
