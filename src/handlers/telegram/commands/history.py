"""
Telegram /history command handler.
"""
import json
from typing import Dict, Any

from aws_lambda_powertools import Logger
from src.utils.dynamo import create_pk
from src.models.event import CycleEvent
from src.handlers.history import calculate_period_history
from src.utils.clients import get_dynamo, get_telegram, get_clients

logger = Logger()

def handle_history_command(user_id: str, chat_id: str) -> Dict[str, Any]:
    """
    Handle /history command.
    
    Args:
        user_id: User's unique identifier
        chat_id: Telegram chat ID
        
    Returns:
        API Gateway response object
        
    Example:
        >>> response = handle_history_command("user123", "chat456")
        >>> assert response["statusCode"] == 200
    """
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
            text="No cycle data found. Use /register to start tracking."
        )
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "ok": False,
                "error_code": 404,
                "description": "No events found"
            })
        }
    
    # Convert to CycleEvent objects
    cycle_events = [
        CycleEvent(**event)
        for event in events
        if event["SK"].startswith("EVENT#")
    ]
    
    # Calculate history
    history = calculate_period_history(cycle_events)
    
    # Format message
    message = [
        "📅 Your Period History (Last 6 Months)",
        "--------------------------------"
    ]
    
    if history["periods"]:
        for period in reversed(history["periods"]):  # Show most recent first
            start_date = period["start_date"].strftime("%Y-%m-%d")
            end_date = period["end_date"].strftime("%Y-%m-%d")
            message.append(f"• {start_date} to {end_date} ({period['duration']} days)")
            
        message.extend([
            "",
            f"Total periods: {history['total_count']}",
            f"Average duration: {history['average_duration']} days"
        ])
    else:
        message.append("No periods found in the last 6 months")
    
    logger.info(
        "History command executed",
        extra={
            "user_id": user_id,
            "periods_found": history["total_count"]
        }
    )
    
    telegram.send_message(
        chat_id=chat_id,
        text="\n".join(message)
    )
    
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "ok": True,
            "result": {"message": "History sent"}
        })
    }
