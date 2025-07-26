"""
Service for handling group phase distribution functionality.

This module provides functionality for formatting and distributing 
phase information to group chats.
"""
from typing import List
from datetime import date

from aws_lambda_powertools import Logger
from src.models.event import CycleEvent
from src.services.weekly_plan import generate_weekly_plan
from src.utils.dynamo import get_user_events

logger = Logger()

def format_group_phase_message(user_id: str) -> str:
    """
    Format phase recommendations message for group distribution.

    Args:
        user_id: The user ID to get phase information for

    Returns:
        str: Formatted message containing phase recommendations for next 7 days

    Raises:
        ValueError: If no events found for user
    """
    try:
        events = get_user_events(user_id)
        if not events:
            logger.warning("No events found for user", extra={"user_id": user_id})
            return f"No cycle data available for user {user_id}"
        
        weekly_plan = generate_weekly_plan(events)
        message_lines = [
            "🌙 Phase Recommendations for Next 7 Days:",
            "----------------------------------------"
        ]
        
        for group in weekly_plan.phase_groups:
            date_range = (
                f"{group.start_date.strftime('%b %d')}-{group.end_date.strftime('%b %d')}"
                if group.start_date != group.end_date
                else group.start_date.strftime("%b %d")
            )
            
            message_lines.extend([
                f"\n📅 {date_range} - {group.traditional_phase.value.title()} Phase",
                f"🌱 Fasting: {group.recommendations.fasting_protocol}",
                "\n🥗 Foods to Focus On:",
                *[f"• {food}" for food in group.recommendations.foods],
                "\n🏃‍♀️ Recommended Activities:",
                *[f"• {activity}" for activity in group.recommendations.activities]
            ])
            
            if group.recommendations.supplements:
                message_lines.extend([
                    "\n💊 Supplements:",
                    *[f"• {supp}" for supp in group.recommendations.supplements]
                ])
            message_lines.append("\n")
        
        logger.info("Phase message formatted successfully", extra={"user_id": user_id})
        return "\n".join(message_lines)
        
    except Exception as e:
        logger.exception(
            "Error formatting group phase message",
            extra={
                "error_type": e.__class__.__name__,
                "user_id": user_id
            }
        )
        raise
