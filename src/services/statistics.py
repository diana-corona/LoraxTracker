"""
Statistics calculation service for cycle tracking data.

This module provides functionality for calculating menstrual cycle statistics,
including period durations and inter-period lengths.
"""
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from statistics import mean
from aws_lambda_powertools import Logger
from src.models.event import CycleEvent
from src.models.phase import TraditionalPhaseType

logger = Logger()

def calculate_phase_statistics(events: List[CycleEvent]) -> Dict:
    """
    Calculate statistics for each phase.
    
    Args:
        events: List of cycle events to analyze
        
    Returns:
        Dictionary containing statistics for each phase
    """
    phase_data = {phase.value: {"durations": [], "pain_levels": [], "energy_levels": []} 
                 for phase in TraditionalPhaseType}
    
    for event in events:
        phase = event.state
        phase_data[phase]["durations"].append(1)  # Each event represents one day
        if event.pain_level is not None:
            phase_data[phase]["pain_levels"].append(event.pain_level)
        if event.energy_level is not None:
            phase_data[phase]["energy_levels"].append(event.energy_level)
    
    statistics = {}
    for phase, data in phase_data.items():
        statistics[phase] = {
            "average_duration": mean(data["durations"]) if data["durations"] else 0,
            "occurrence_count": len(data["durations"]),
            "average_pain_level": mean(data["pain_levels"]) if data["pain_levels"] else None,
            "average_energy_level": mean(data["energy_levels"]) if data["energy_levels"] else None
        }
    
    return statistics

def filter_recent_events(events: List[CycleEvent], max_periods: int = 12) -> List[CycleEvent]:
    """
    Filter events to include only recent data (last year or last 12 periods).
    
    Args:
        events: List of cycle events to filter
        max_periods: Maximum number of periods to include
        
    Returns:
        Filtered list of events
    """
    if not events:
        return []
        
    # Sort events by date
    sorted_events = sorted(events, key=lambda x: x.date, reverse=True)
    
    # Get cutoff date (1 year ago)
    cutoff_date = datetime.now().date() - timedelta(days=365)
    
    # Filter events by date and count periods
    filtered_events = []
    period_count = 0
    
    for event in sorted_events:
        # Stop if we've found max periods and this event is before cutoff
        if period_count >= max_periods and event.date < cutoff_date:
            break
            
        # Count new period starts
        if event.state == TraditionalPhaseType.MENSTRUATION.value:
            if not filtered_events or filtered_events[-1].state != TraditionalPhaseType.MENSTRUATION.value:
                period_count += 1
                
        filtered_events.append(event)
    
    # Sort back to chronological order
    return sorted(filtered_events, key=lambda x: x.date)

def find_period_ranges(events: List[CycleEvent]) -> List[Tuple[datetime.date, datetime.date]]:
    """
    Find start and end dates for each period.
    
    Args:
        events: List of cycle events to analyze
        
    Returns:
        List of tuples containing (period_start_date, period_end_date)
    """
    period_ranges = []
    period_start = None
    last_date = None
    
    for event in events:
        if event.state == TraditionalPhaseType.MENSTRUATION.value:
            if period_start is None:
                period_start = event.date
            last_date = event.date
        elif period_start is not None:
            period_ranges.append((period_start, last_date))
            period_start = None
            
    # Add final period if we ended during one
    if period_start is not None:
        period_ranges.append((period_start, last_date))
    
    return period_ranges

def calculate_cycle_statistics(events: List[CycleEvent]) -> Dict:
    """
    Calculate overall cycle statistics including period durations and inter-period lengths.
    
    Args:
        events: List of cycle events to analyze
        
    Returns:
        Dictionary containing:
        - average_period_duration: Average length of periods
        - average_days_between: Average days between periods
        - total_cycles: Number of cycles analyzed
        - last_two_periods: List of last two period dates and durations
    """
    if not events:
        return {
            "average_period_duration": 0,
            "average_days_between": 0,
            "total_cycles": 0,
            "last_two_periods": []
        }
    
    # Filter to recent events
    recent_events = filter_recent_events(events)
    logger.info(f"Analyzing {len(recent_events)} events from the past year")
    
    # Find period ranges
    period_ranges = find_period_ranges(recent_events)
    
    if not period_ranges:
        return {
            "average_period_duration": 0,
            "average_days_between": 0,
            "total_cycles": 0,
            "last_two_periods": []
        }
    
    # Calculate period durations
    period_durations = [(end - start).days + 1 for start, end in period_ranges]
    
    # Calculate days between periods
    days_between = []
    for i in range(1, len(period_ranges)):
        current_start = period_ranges[i][0]
        prev_end = period_ranges[i-1][1]
        days_between.append((current_start - prev_end).days - 1)
    
    # Get last two periods with durations
    last_two = []
    if len(period_ranges) >= 1:
        last_two.append({
            "start_date": period_ranges[-1][0],
            "end_date": period_ranges[-1][1],
            "duration": period_durations[-1]
        })
    if len(period_ranges) >= 2:
        last_two.append({
            "start_date": period_ranges[-2][0],
            "end_date": period_ranges[-2][1],
            "duration": period_durations[-2]
        })
        
    logger.info(f"Found {len(period_ranges)} periods in analyzed timeframe")
    
    return {
        "average_period_duration": mean(period_durations) if period_durations else 0,
        "average_days_between": mean(days_between) if days_between else 0,
        "total_cycles": len(period_ranges),
        "last_two_periods": last_two
    }
