"""
Service module for historical cycle data analysis.

This module provides functionality for analyzing historical cycle data,
including retrieving period history for specified time ranges.

Typical usage:
    events = get_user_events(user_id)
    history = get_period_history(events, months=6)
    for period in history:
        print(f"{period['start_date']} to {period['end_date']}")
"""
from typing import List, Dict, Any
from datetime import date, timedelta

from src.models.event import CycleEvent
from src.services.utils import get_menstruation_events

def get_period_history(events: List[CycleEvent], months: int = 6) -> List[Dict[str, Any]]:
    """
    Get period history for specified number of months.
    
    Args:
        events: List of cycle events
        months: Number of months to look back
        
    Returns:
        List of period details containing:
        - start_date: Period start date
        - end_date: Period end date
        - duration: Period duration in days
        
    Example:
        >>> events = get_user_events(user_id)
        >>> history = get_period_history(events)
        >>> for period in history:
        ...     print(f"{period['start_date']} to {period['end_date']} ({period['duration']} days)")
    """
    if not events:
        return []

    # Calculate cutoff date (current date minus specified months)
    cutoff_date = date.today() - timedelta(days=30 * months)
    
    # Get menstruation events in reverse order (newest first)
    menstruation_events = get_menstruation_events(events, reverse=True)
    
    # Filter events within time range and group into periods
    periods = []
    current_period = None
    
    for event in menstruation_events:
        if event.date < cutoff_date:
            break
            
        # Since events are in reverse order (newest first), 
        # we need to handle the dates differently
        if not current_period:
            # Start new period
            current_period = {
                'start_date': event.date,
                'end_date': event.date,
                'duration': 1
            }
        elif abs((event.date - current_period['start_date']).days) == 1:
            # Extend current period (could be earlier or later day)
            current_period['start_date'] = min(current_period['start_date'], event.date)
            current_period['end_date'] = max(current_period['end_date'], event.date)
            current_period['duration'] += 1
        else:
            # Gap found, start new period
            periods.append(current_period)
            current_period = {
                'start_date': event.date,
                'end_date': event.date,
                'duration': 1
            }
    
    # Add final period if exists
    if current_period:
        periods.append(current_period)
    
    return periods
