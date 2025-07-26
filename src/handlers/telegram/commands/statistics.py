"""
Telegram /statistics command handler.
"""
from typing import Dict, Any

from aws_lambda_powertools import Logger
from src.utils.telegram import TelegramClient
from src.utils.dynamo import DynamoDBClient, create_pk
from src.models.event import CycleEvent
from src.handlers.statistics import calculate_cycle_statistics, calculate_phase_statistics

import os

logger = Logger()
telegram = TelegramClient()
dynamo = DynamoDBClient(os.environ['TRACKER_TABLE_NAME'])

def handle_statistics_command(user_id: str, chat_id: str) -> Dict[str, Any]:
    """Handle /statistics command."""
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
    phase_stats = calculate_phase_statistics(cycle_events)
    
    # Format message
    message = [
        "📊 Your Cycle Statistics",
        "------------------------",
        f"Total cycles tracked: {cycle_stats['total_cycles']}",
        f"Average cycle length: {round(cycle_stats['average_cycle_length'], 1)} days",
        f"Shortest cycle: {cycle_stats['min_cycle_length']} days",
        f"Longest cycle: {cycle_stats['max_cycle_length']} days",
        "",
        "📈 Phase Statistics:",
    ]
    
    for phase, stats in phase_stats.items():
        phase_info = [
            f"\n{phase.title()}:",
            f"• Average duration: {round(stats['average_duration'], 1)} days",
            f"• Occurrences: {stats['occurrence_count']} times"
        ]
        
        if stats['average_pain_level'] is not None:
            phase_info.append(f"• Average pain level: {round(stats['average_pain_level'], 1)}/5")
        if stats['average_energy_level'] is not None:
            phase_info.append(f"• Average energy level: {round(stats['average_energy_level'], 1)}/5")
            
        message.extend(phase_info)
    
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
