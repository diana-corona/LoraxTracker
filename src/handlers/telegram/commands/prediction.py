"""
Telegram /predict command handler.
"""
import json
from typing import Dict, Any

from aws_lambda_powertools import Logger
from src.utils.dynamo import create_pk
from src.models.event import CycleEvent
from src.services.cycle import calculate_next_cycle
from src.utils.clients import get_dynamo, get_telegram, get_clients

logger = Logger()

def handle_prediction_command(user_id: str, chat_id: str) -> Dict[str, Any]:
    """Handle /prediction command."""
    # Get clients lazily
    dynamo, telegram = get_clients()
    
    # Get user's events
    events = dynamo.query_items(
        partition_key="PK",
        partition_value=create_pk(user_id)
    )
    
    if not events:
        telegram.send_message(
            chat_id=chat_id,
            text="Not enough data to make a prediction."
        )
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "ok": False,
                "error_code": 404,
                "description": "No events found"
            }),
            "isBase64Encoded": False
        }
    
    # Convert to CycleEvent objects
    cycle_events = [
        CycleEvent(**event)
        for event in events
        if event["SK"].startswith("EVENT#")
    ]
    
    # Calculate prediction
    next_date, duration, warning = calculate_next_cycle(cycle_events)
    
    message = [
        f"🔮 Next expected cycle: {next_date}",
        f"📊 Average duration: {duration} days",
    ]
    
    if warning:
        message.append(f"⚠️ {warning}")
    
    telegram.send_message(
        chat_id=chat_id,
        text="\n".join(message)
    )
    
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "ok": True,
            "result": {"message": "Prediction sent"}
        }),
        "isBase64Encoded": False
    }
