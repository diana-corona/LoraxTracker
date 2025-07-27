"""
Weekly plan command module.

This module provides functionality for generating on-demand weekly plans
through a Telegram command interface.

Typical usage:
    User sends: /weeklyplan
    Bot responds with a personalized weekly plan
"""
from typing import Optional, Dict, Any

from aws_lambda_powertools import Logger

from src.utils.dynamo import create_pk
from src.models.event import CycleEvent
from src.services.weekly_plan import generate_weekly_plan, format_weekly_plan
from src.utils.clients import get_telegram, get_dynamo, get_clients

logger = Logger()

def handle_weeklyplan_command(
    update: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Handle /weeklyplan command to generate an on-demand weekly plan.

    This handler retrieves cycle events and generates a personalized
    weekly plan on demand.

    Args:
        update: Telegram update object containing message and user info
        context: Optional context for the command handler

    Raises:
        ValueError: If no cycle events are found
        Exception: For unexpected errors during plan generation
    """
    chat_id = update["message"]["chat"]["id"]
    user_id = str(update["message"]["from"]["id"])
    
    logger.info("Processing weeklyplan command", extra={
        "user_id": user_id,
        "chat_id": chat_id
    })

    # Get clients lazily
    dynamo, telegram = get_clients()

    try:
        # Get user's events
        events = dynamo.query_items(
            partition_key="PK",
            partition_value=create_pk(user_id)
        )
        
        # Convert to CycleEvent objects
        cycle_events = [
            CycleEvent(**event)
            for event in events
            if event["SK"].startswith("EVENT#")
        ]
        
        if not cycle_events:
            logger.warning("No cycle events found", extra={
                "user_id": user_id
            })
            raise ValueError("No cycle events found. Please register some events first.")
            
        # Generate and format weekly plan
        weekly_plan = generate_weekly_plan(cycle_events)
        formatted_plan = format_weekly_plan(weekly_plan)
        
        # Send plan
        telegram.send_message(
            chat_id=chat_id,
            text="\n".join(formatted_plan)
        )
        
        logger.info("Weekly plan generated successfully", extra={
            "user_id": user_id,
            "chat_id": chat_id,
            "plan_start": weekly_plan.start_date.isoformat(),
            "plan_end": weekly_plan.end_date.isoformat()
        })
        
    except ValueError as e:
        telegram.send_message(
            chat_id=chat_id,
            text=f"⚠️ {str(e)}"
        )
    except Exception as e:
        logger.exception(
            "Error generating weekly plan",
            extra={
                "user_id": user_id,
                "error_type": e.__class__.__name__
            }
        )
        telegram.send_message(
            chat_id=chat_id,
            text="Sorry, there was an error generating your weekly plan. Please try again later."
        )
