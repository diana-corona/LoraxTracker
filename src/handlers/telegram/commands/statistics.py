"""
Telegram /statistics command handler.
"""
import json
from typing import Dict, Any

from aws_lambda_powertools import Logger
from src.utils.dynamo import create_pk
from src.models.event import CycleEvent
from src.handlers.statistics import calculate_cycle_statistics
from src.utils.clients import get_dynamo, get_telegram, get_clients

logger = Logger()

def handle_statistics_command(user_id: str, chat_id: str) -> Dict[str, Any]:
    """Handle /statistics command."""
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
    
    # Calculate statistics
    cycle_stats = calculate_cycle_statistics(cycle_events)
    
    # Format message
    message = [
        "📊 Your Cycle Statistics",
        "------------------------",
        f"Total cycles tracked: {cycle_stats['total_cycles']}",
        f"Average period duration: {round(cycle_stats['average_period_duration'], 1)} days",
        f"Average days between periods: {round(cycle_stats['average_days_between'], 1)} days",
    ]

    # Add last two periods if available
    if cycle_stats['last_two_periods']:
        message.extend([
            "",
            "Last Two Periods:",
            "---------------"
        ])
        for period in reversed(cycle_stats['last_two_periods']):  # Show most recent first
            start_date = period['start_date'].strftime('%Y-%m-%d')
            end_date = period['end_date'].strftime('%Y-%m-%d')
            message.append(f"• {start_date} to {end_date} ({period['duration']} days)")
    
    telegram.send_message(
        chat_id=chat_id,
        text="\n".join(message)
    )
    
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "ok": True,
            "result": {"message": "Statistics sent"}
        })
    }
