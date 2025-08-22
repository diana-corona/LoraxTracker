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
from src.services.exceptions import InvalidPeriodDurationError

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

def find_period_ranges(events: List[CycleEvent], max_gap: int = 1) -> List[Tuple[datetime.date, datetime.date]]:
    """
    Find start and end dates for each period.
    
    Args:
        events: List of cycle events to analyze
        max_gap: Maximum number of days gap allowed within same period (default: 1)
        
    Returns:
        List of tuples containing (period_start_date, period_end_date)
        
    Note:
        Periods are considered continuous if gap between menstruation days
        is not more than max_gap days. This handles missing data while still
        maintaining physiologically reasonable period lengths.
    """
    period_ranges = []
    period_start = None
    last_date = None
    
    for i, event in enumerate(events):
        if event.state == TraditionalPhaseType.MENSTRUATION.value:
            if period_start is None:
                period_start = event.date
                last_date = event.date
            else:
                # Check if this is continuous with previous menstruation
                days_gap = (event.date - last_date).days - 1
                if days_gap <= max_gap:
                    last_date = event.date
                else:
                    # Gap too large, end previous period and start new one
                    period_ranges.append((period_start, last_date))
                    period_start = event.date
                    last_date = event.date
        elif period_start is not None:
            # Non-menstruation event after period
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
        - total_cycles: Number of complete cycles analyzed
        - last_two_periods: List of last two period dates and durations
        - current_period: Information about ongoing period (if any)
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
            "last_two_periods": [],
            "current_period": None
        }
    
    # Check if most recent period is potentially ongoing
    today = datetime.now().date()
    most_recent_period = period_ranges[-1]
    most_recent_end = most_recent_period[1]
    is_current = (today - most_recent_end).days <= 10
    
    # Exclude current period from statistics if it's incomplete
    periods_for_stats = period_ranges[:-1] if is_current else period_ranges
    
    # Calculate period durations for complete periods only
    period_durations = []
    today = datetime.now().date()
    for start, end in periods_for_stats:
        duration = (end - start).days + 1
        
        # Only validate and add duration if it's not from current period
        if not (is_current and end == most_recent_end):
            if duration < 2 or duration > 10:
                logger.warning(
                    "Invalid period duration detected",
                    extra={
                        "start_date": str(start),
                        "end_date": str(end),
                        "duration": duration
                    }
                )
                raise InvalidPeriodDurationError(
                    f"Period duration of {duration} days is outside normal range (2-10 days)"
                )
            period_durations.append(duration)
        else:
            logger.info("Skipping validation for current period", extra={
                "start_date": str(start),
                "end_date": str(end),
                "duration": duration
            })
    
    # Calculate days between periods (exclusive of end dates)
    days_between = []
    for i in range(1, len(periods_for_stats)):
        current_start = periods_for_stats[i][0]
        prev_end = periods_for_stats[i-1][1]
        # Calculate days between periods, not counting the end date of previous period
        days_between.append((current_start - prev_end).days - 1)
        logger.info(
            "Calculated days between periods",
            extra={
                "previous_end": str(prev_end),
                "current_start": str(current_start),
                "days_between": days_between[-1]
            }
        )
    
    # Prepare current period info if detected
    current_period = None
    if is_current:
        current_period = {
            "start_date": most_recent_period[0],
            "last_logged_date": most_recent_period[1],
            "days_logged": (most_recent_period[1] - most_recent_period[0]).days + 1
        }
    
    # Get last two complete periods with durations
    # Get last two complete periods with durations (excluding current period)
    last_two = []
    complete_periods = periods_for_stats  # Use periods excluding current if it's incomplete
    if len(complete_periods) >= 1:
        last_two.append({
            "start_date": complete_periods[-1][0],
            "end_date": complete_periods[-1][1],
            "duration": (complete_periods[-1][1] - complete_periods[-1][0]).days + 1
        })
    if len(complete_periods) >= 2:
        last_two.append({
            "start_date": complete_periods[-2][0],
            "end_date": complete_periods[-2][1],
            "duration": (complete_periods[-2][1] - complete_periods[-2][0]).days + 1
        })
        
    logger.info(f"Found {len(complete_periods)} complete periods in analyzed timeframe")
    if current_period:
        logger.info("Current period detected", extra=current_period)
    
    return {
        "average_period_duration": mean(period_durations) if period_durations else 0,
        "average_days_between": mean(days_between) if days_between else 0,
        "total_cycles": len(complete_periods),
        "last_two_periods": last_two,
        "current_period": current_period
    }
