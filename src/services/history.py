"""
Service module for historical cycle data analysis.

This module provides functionality for analyzing historical cycle data,
including retrieving period history for specified time ranges or counts.

Typical usage:
    events = get_user_events(user_id)
    history = get_period_history(events, months=6)  # Time-based
    history = get_period_history(events, periods=3)  # Count-based
    for period in history:
        print(f"{period['start_date']} to {period['end_date']}")
"""
from typing import List, Dict, Any, Optional
from datetime import date, timedelta

from src.models.event import CycleEvent
from src.services.utils import get_menstruation_events

def get_period_history(
    events: List[CycleEvent], 
    months: Optional[int] = 6,  # Default to 6 months
    periods: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Get period history for specified number of months or periods.
    
    Args:
        events: List of cycle events
        months: Optional number of months to look back
        periods: Optional number of most recent periods to return
        
    Returns:
        List of period details containing:
        - start_date: Period start date
        - end_date: Period end date
        - duration: Period duration in days
        
    Example:
        >>> events = get_user_events(user_id)
        >>> history = get_period_history(events, periods=3)  # Last 3 periods
        >>> for period in history:
        ...     print(f"{period['start_date']} to {period['end_date']} ({period['duration']} days)")
    """
    if not events:
        return []

    # Get menstruation events in reverse order (newest first)
    menstruation_events = get_menstruation_events(events, reverse=True)
    
    # Initialize result list for periods
    result_periods = []
    current_period = None
    
    # Calculate cutoff date
    cutoff_date = date.today() - timedelta(days=30 * months) if months else None
    
    # Keep track of processed dates to avoid duplicates
    processed_dates = set()
    
    for event in menstruation_events:
        # Skip if this date was already processed
        if event.date in processed_dates:
            continue
            
        # Since events are in reverse order (newest first), 
        # we need to handle the dates differently
        if cutoff_date and event.date < cutoff_date:
            break
            
        if not current_period:
            # Start new period
            current_period = {
                'start_date': event.date,
                'end_date': event.date,
                'duration': 1
            }
            processed_dates.add(event.date)
        elif abs((event.date - current_period['start_date']).days) == 1:
            # Extend current period (could be earlier or later day)
            if event.date not in processed_dates:
                current_period['start_date'] = min(current_period['start_date'], event.date)
                current_period['end_date'] = max(current_period['end_date'], event.date)
                current_period['duration'] += 1
                processed_dates.add(event.date)
        else:
            # Gap found, start new period
            result_periods.append(current_period)
            
            # Check count and time limits before starting a new period
            if (periods is not None and len(result_periods) >= periods) or \
               (cutoff_date and event.date < cutoff_date):
                break
                
            current_period = {
                'start_date': event.date,
                'end_date': event.date,
                'duration': 1
            }
    
    # Add final period if exists and we haven't hit our count limit
    if current_period and (periods is None or len(result_periods) < periods):
        result_periods.append(current_period)
    
    return result_periods
