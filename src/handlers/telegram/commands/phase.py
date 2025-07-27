"""
Telegram /phase command handler.
"""
import json
from typing import Dict, Any

from aws_lambda_powertools import Logger
from src.utils.dynamo import create_pk
from src.models.event import CycleEvent
from src.services.phase import get_current_phase, generate_phase_report
from src.utils.clients import get_dynamo, get_telegram, get_clients

logger = Logger()

def handle_phase_command(user_id: str, chat_id: str) -> Dict[str, Any]:
    """Handle /phase command."""
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
            text="No events registered. Use /register to start."
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
    
    # Get current phase
    current_phase = get_current_phase(cycle_events)
    
    # Generate and send report
    report = generate_phase_report(current_phase, cycle_events)
    telegram.send_phase_report(chat_id, report)
    
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "ok": True,
            "result": {"message": "Phase report sent"}
        }),
        "isBase64Encoded": False
    }
