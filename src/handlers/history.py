"""
Handler module for historical cycle data requests.

This module handles requests for historical cycle data analysis,
coordinating between services and data sources.
"""
from typing import Dict, Any, List
from datetime import date

from aws_lambda_powertools import Logger
from src.models.event import CycleEvent
from src.services.history import get_period_history

logger = Logger()

def calculate_period_history(
    events: List[CycleEvent],
    months: int = 6
) -> Dict[str, Any]:
    """
    Calculate period history statistics.
    
    Args:
        events: List of user's cycle events
        months: Number of months to look back
        
    Returns:
        Dictionary containing:
        - periods: List of period details
        - total_count: Total number of periods found
        - average_duration: Average duration of periods
        
    Example:
        >>> events = get_user_events(user_id)
        >>> history = calculate_period_history(events)
        >>> print(f"Found {history['total_count']} periods")
    """
    try:
        periods = get_period_history(events, months)
        
        if not periods:
            return {
                "periods": [],
                "total_count": 0,
                "average_duration": None
            }
            
        total_duration = sum(period["duration"] for period in periods)
        average_duration = round(total_duration / len(periods), 1)
        
        logger.info(
            "Period history calculated",
            extra={
                "months_analyzed": months,
                "periods_found": len(periods),
                "average_duration": average_duration
            }
        )
        
        return {
            "periods": periods,
            "total_count": len(periods),
            "average_duration": average_duration
        }
        
    except Exception as e:
        logger.exception(
            "Error calculating period history",
            extra={
                "error": str(e),
                "error_type": e.__class__.__name__,
                "months": months
            }
        )
        raise
