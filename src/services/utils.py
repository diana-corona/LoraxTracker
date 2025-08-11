"""
Shared utility functions for cycle-related services.

These utilities are used across multiple service modules to handle common
operations like event filtering, cycle day calculation, and phase mapping.
"""
from typing import List, Optional, Tuple
from datetime import date, timedelta

from src.models.event import CycleEvent
from src.models.phase import TraditionalPhaseType, FunctionalPhaseType
from src.services.constants import (
    TRADITIONAL_PHASE_DURATIONS,
    FUNCTIONAL_PHASE_MAPPING
)

def get_menstruation_events(events: List[CycleEvent], reverse: bool = False) -> List[CycleEvent]:
    """
    Filter and sort menstruation events.
    
    Args:
        events: List of cycle events to filter
        reverse: Whether to sort in reverse order (newest first)
        
    Returns:
        List of menstruation events sorted by date
        
    Example:
        >>> events = [event1, event2, event3]
        >>> menstruation_events = get_menstruation_events(events)
        >>> recent_events = get_menstruation_events(events, reverse=True)
    """
    menstruation_events = [
        e for e in events
        if e.state == TraditionalPhaseType.MENSTRUATION.value
    ]
    return sorted(menstruation_events, key=lambda x: x.date, reverse=reverse)

def calculate_cycle_day(events: List[CycleEvent], target_date: date = None) -> int:
    """
    Calculate the current day in the cycle.
    
    Args:
        events: List of cycle events
        target_date: Optional specific date to calculate for, defaults to today
        
    Returns:
        Current day number in the cycle (1-based)
        
    Example:
        >>> events = get_user_events(user_id)
        >>> current_day = calculate_cycle_day(events)
        >>> specific_day = calculate_cycle_day(events, date(2025, 7, 1))
    """
    if target_date is None:
        target_date = date.today()
        
    menstruation_events = get_menstruation_events(events, reverse=True)
    
    if not menstruation_events:
        return 1
        
    last_menstruation = menstruation_events[0]
    return (target_date - last_menstruation.date).days + 1

def determine_traditional_phase(
    cycle_day: int,
    custom_durations: Optional[dict] = None
) -> Tuple[TraditionalPhaseType, int]:
    """
    Determine traditional phase and remaining days based on cycle day.
    
    Args:
        cycle_day: Current day in the cycle (1-based)
        custom_durations: Optional custom phase durations
        
    Returns:
        Tuple of (phase type, remaining days in current phase)
        
    Example:
        >>> phase, remaining = determine_traditional_phase(5)
        >>> assert phase == TraditionalPhaseType.MENSTRUATION
        >>> assert remaining == 1  # On day 5, 1 day remaining in menstruation
    """
    durations = custom_durations or TRADITIONAL_PHASE_DURATIONS
    
    # Define phase boundaries
    if cycle_day <= 5:  # Days 1-5
        remaining_days = 5 - cycle_day + 1
        return TraditionalPhaseType.MENSTRUATION, remaining_days
    elif cycle_day <= 14:  # Days 6-14
        remaining_days = 14 - cycle_day + 1
        return TraditionalPhaseType.FOLLICULAR, remaining_days
    elif cycle_day <= 17:  # Days 15-17
        remaining_days = 17 - cycle_day + 1
        return TraditionalPhaseType.OVULATION, remaining_days
    else:  # Days 18-28
        if cycle_day <= 28:
            remaining_days = 28 - cycle_day + 1
        else:
            remaining_days = 1  # If beyond day 28, show 1 day remaining
        return TraditionalPhaseType.LUTEAL, remaining_days

def determine_functional_phase(cycle_day: int) -> FunctionalPhaseType:
    """
    Map cycle day to functional phase.
    
    Args:
        cycle_day: Current day in the cycle (1-based)
        
    Returns:
        Functional phase type
        
    Example:
        >>> phase = determine_functional_phase(12)
        >>> assert phase == FunctionalPhaseType.MANIFESTATION
    """
    for start, end, phase in FUNCTIONAL_PHASE_MAPPING:
        if start <= cycle_day <= end:
            return phase
            
    return FunctionalPhaseType.NURTURE  # Default to nurture phase

def calculate_functional_phase_duration(cycle_day: int, phase: FunctionalPhaseType) -> tuple[int, date, date]:
    """
    Calculate the duration and dates for the current functional phase.
    
    Args:
        cycle_day: Current day in the cycle (1-based)
        phase: Current functional phase
        
    Returns:
        Tuple of (duration in days, start date, end date)
        
    Example:
        >>> duration, start, end = calculate_functional_phase_duration(17, FunctionalPhaseType.POWER)
        >>> assert duration == 4  # Second power phase is 4 days (16-19)
    """
    today = date.today()
    
    # Find the current phase range
    for start_day, end_day, mapped_phase in FUNCTIONAL_PHASE_MAPPING:
        if mapped_phase == phase and start_day <= cycle_day <= end_day:
            # Calculate remaining days in this phase
            days_remaining = end_day - cycle_day + 1
            
            # Calculate dates
            phase_start = today - timedelta(days=cycle_day - start_day)
            phase_end = phase_start + timedelta(days=end_day - start_day)
            
            return days_remaining, phase_start, phase_end
            
    # Default to end of cycle for nurture phase
    if phase == FunctionalPhaseType.NURTURE:
        days_remaining = 28 - cycle_day + 1
        phase_start = today - timedelta(days=cycle_day - 20)  # Nurture starts day 20
        phase_end = phase_start + timedelta(days=9)  # 9 days duration
        return days_remaining, phase_start, phase_end
        
    raise ValueError(f"Could not calculate duration for phase {phase} on cycle day {cycle_day}")

def calculate_average_metrics(
    events: List[CycleEvent]
) -> Tuple[Optional[float], Optional[float]]:
    """
    Calculate average pain and energy levels from events.
    
    Args:
        events: List of cycle events
        
    Returns:
        Tuple of (average pain level, average energy level)
        
    Example:
        >>> events = get_recent_events(user_id)
        >>> avg_pain, avg_energy = calculate_average_metrics(events)
    """
    pain_levels = [e.pain_level for e in events if e.pain_level is not None]
    energy_levels = [e.energy_level for e in events if e.energy_level is not None]
    
    avg_pain = sum(pain_levels) / len(pain_levels) if pain_levels else None
    avg_energy = sum(energy_levels) / len(energy_levels) if energy_levels else None
    
    return avg_pain, avg_energy
