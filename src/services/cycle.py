"""
Service module for menstrual cycle calculations and predictions.

This module provides functionality for analyzing cycle data and making predictions
about future cycles based on historical data. It also includes utilities for
determining cycle phases and generating phase-specific information.

Typical usage:
    events = get_user_events(user_id)
    next_date, duration, warning = calculate_next_cycle(events)
    current_phase = analyze_cycle_phase(events)
"""
from typing import List, Tuple, Optional
from datetime import date, timedelta
from statistics import mean, stdev

from src.models.event import CycleEvent
from src.services.statistics import calculate_cycle_statistics, find_period_ranges
from src.models.phase import TraditionalPhaseType, FunctionalPhaseType, Phase
from src.services.phase import get_phase_details
from src.services.utils import (
    get_menstruation_events,
    calculate_cycle_day,
    determine_traditional_phase,
    determine_functional_phase
)

def calculate_next_cycle(events: List[CycleEvent]) -> Tuple[date, int, Optional[str]]:
    """
    Calculate the next expected cycle date based on historical data.
    
    Args:
        events: List of cycle events ordered by date
        
    Returns:
        Tuple containing:
        - Predicted next cycle start date
        - Average cycle duration in days
        - Warning message if cycle irregularity detected
        
    Raises:
        ValueError: If no events are provided
        
    Example:
        >>> events = get_user_events(user_id)
        >>> next_date, duration, warning = calculate_next_cycle(events)
        >>> print(f"Next cycle expected on {next_date}, avg duration: {duration} days")
        >>> if warning:
        ...     print(f"Warning: {warning}")
    """
    if not events:
        raise ValueError("No events provided for prediction")
        
    menstruation_events = get_menstruation_events(events)
    
    if len(menstruation_events) < 2:
        if menstruation_events:
            return (
                menstruation_events[0].date + timedelta(days=28),
                28,
                "Insufficient data for accurate prediction"
            )
        raise ValueError("No menstruation events found for prediction")
    
    # Get accurate statistics using the statistics service
    stats = calculate_cycle_statistics(events)
    period_ranges = find_period_ranges(events)
    
    if not period_ranges:
        raise ValueError("No valid period ranges found")
        
    # Get the last period's end date
    last_period_end = period_ranges[-1][1]
    avg_days_between = stats["average_days_between"]
    warning = None
    
    today = date.today()
    days_since_last_end = (today - last_period_end).days
    
    # If today is within a day of the expected next cycle, predict tomorrow
    if days_since_last_end >= avg_days_between - 1:
        next_date = today + timedelta(days=1)
    else:
        # Otherwise predict based on the last period end date plus average interval
        next_date = last_period_end + timedelta(days=round(avg_days_between))
    
    # Check for irregularity by comparing recent cycles
    if len(period_ranges) >= 3:
        recent_intervals = []
        for i in range(1, len(period_ranges)):
            interval = (period_ranges[i][0] - period_ranges[i-1][1]).days - 1
            recent_intervals.append(interval)
        if stdev(recent_intervals) > 7:  # Using a tighter threshold
            warning = "Irregular cycle detected"
            
    return next_date, round(stats["average_period_duration"]), warning

def analyze_cycle_phase(events: List[CycleEvent], target_date: Optional[date] = None) -> Phase:
    """
    Analyze and determine the cycle phase for a given date.
    
    Args:
        events: List of cycle events
        target_date: Date to analyze, defaults to current date
        
    Returns:
        Phase object containing phase information
        
    Raises:
        ValueError: If no events found or no menstruation events in history
        
    Example:
        >>> events = get_user_events(user_id)
        >>> phase = analyze_cycle_phase(events)
        >>> print(f"Current phase: {phase.traditional_phase}")
        >>> print(f"Functional phase: {phase.functional_phase}")
    """
    if target_date is None:
        target_date = date.today()

    cycle_day = calculate_cycle_day(events, target_date)
    phase_type, duration = determine_traditional_phase(cycle_day)
    functional_phase = determine_functional_phase(cycle_day)

    # Calculate phase dates
    menstruation_events = get_menstruation_events(events, reverse=True)
    if not menstruation_events:
        raise ValueError("No menstruation events found")
        
    last_menstruation = menstruation_events[0]
    days_since = (target_date - last_menstruation.date).days
    start_date = target_date - timedelta(days=days_since % duration)
    end_date = start_date + timedelta(days=duration)
    
    # Get phase details from phase service
    phase_details = get_phase_details(phase_type, cycle_day)

    return Phase(
        traditional_phase=phase_type,
        functional_phase=functional_phase,
        start_date=start_date,
        end_date=end_date,
        duration=duration,
        typical_symptoms=phase_details["traditional_symptoms"],
        dietary_style=phase_details["dietary_style"],
        fasting_protocol=phase_details["fasting_protocol"],
        food_recommendations=phase_details["food_recommendations"],
        activity_recommendations=phase_details["activity_recommendations"],
        supplement_recommendations=phase_details.get("supplement_recommendations"),
        user_notes=None
    )
