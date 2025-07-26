"""
Service module for menstrual cycle calculations and predictions.
"""
from typing import List, Tuple, Optional
from datetime import date, timedelta
from statistics import mean, stdev

from src.models.event import CycleEvent
from src.models.phase import TraditionalPhaseType, FunctionalPhaseType, Phase
from src.services.phase import get_phase_details, map_to_functional_phase

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
    """
    if not events:
        raise ValueError("No events provided for prediction")
        
    # Filter menstruation events and sort by date
    menstruation_events = sorted(
        [e for e in events if e.state == "menstruation"],
        key=lambda x: x.date
    )
    
    if len(menstruation_events) < 2:
        return (
            menstruation_events[0].date + timedelta(days=28),
            28,
            "Insufficient data for accurate prediction"
        )
    
    # Calculate intervals between cycles
    intervals = []
    for i in range(1, len(menstruation_events)):
        interval = (menstruation_events[i].date - menstruation_events[i-1].date).days
        intervals.append(interval)
    
    avg_duration = round(mean(intervals))
    
    # Check for cycle irregularity
    warning = None
    if len(intervals) >= 3:
        cycle_stddev = stdev(intervals)
        if cycle_stddev > 10:  # More than 10 days variation
            warning = "Irregular cycle detected"
    
    last_date = menstruation_events[-1].date
    next_date = last_date + timedelta(days=avg_duration)
    
    return next_date, avg_duration, warning

def analyze_cycle_phase(events: List[CycleEvent], target_date: Optional[date] = None) -> Phase:
    """
    Analyze and determine the cycle phase for a given date.
    
    Args:
        events: List of cycle events
        target_date: Date to analyze, defaults to current date
        
    Returns:
        Phase object containing phase information
    """
    if target_date is None:
        target_date = date.today()
        
    # Get the most recent menstruation event before target date
    recent_events = [
        e for e in sorted(events, key=lambda x: x.date, reverse=True)
        if e.date <= target_date
    ]
    
    if not recent_events:
        raise ValueError("No events found before target date")
    
    last_menstruation = next(
        (e for e in recent_events if e.state == "menstruation"),
        None
    )
    
    if not last_menstruation:
        raise ValueError("No menstruation event found in history")
    
    days_since = (target_date - last_menstruation.date).days
    
    # Determine phase based on typical cycle lengths
    if days_since < 5:
        phase_type = TraditionalPhaseType.MENSTRUATION
        duration = 5
    elif days_since < 14:
        phase_type = TraditionalPhaseType.FOLLICULAR
        duration = 9
    elif days_since < 17:
        phase_type = TraditionalPhaseType.OVULATION
        duration = 3
    else:
        phase_type = TraditionalPhaseType.LUTEAL
        duration = 11
    
    start_date = target_date - timedelta(days=days_since % duration)
    end_date = start_date + timedelta(days=duration)
    
    # Get phase details from phase service
    phase_details = get_phase_details(phase_type, days_since + 1)
    functional_phase = map_to_functional_phase(phase_type, days_since + 1)

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

def get_typical_symptoms(phase_type: TraditionalPhaseType) -> List[str]:
    """Get typical symptoms for a given phase."""
    symptoms = {
        TraditionalPhaseType.MENSTRUATION: [
            "Cramping",
            "Fatigue",
            "Lower back pain",
            "Headaches"
        ],
        TraditionalPhaseType.FOLLICULAR: [
            "Increased energy",
            "Better mood",
            "Higher cognitive function",
            "Increased motivation"
        ],
        TraditionalPhaseType.OVULATION: [
            "Mild pelvic pain",
            "Increased libido",
            "Breast tenderness",
            "Increased energy levels"
        ],
        TraditionalPhaseType.LUTEAL: [
            "Mood changes",
            "Breast tenderness",
            "Fatigue",
            "Food cravings"
        ]
    }
    return symptoms[phase_type]

def get_phase_recommendations(phase_type: TraditionalPhaseType) -> List[str]:
    """Get general recommendations for a given phase."""
    recommendations = {
        TraditionalPhaseType.MENSTRUATION: [
            "Rest and self-care",
            "Light exercise like walking or yoga",
            "Iron-rich foods",
            "Warm compress for cramps"
        ],
        TraditionalPhaseType.FOLLICULAR: [
            "High-intensity workouts",
            "Start new projects",
            "Social activities",
            "Learning new skills"
        ],
        TraditionalPhaseType.OVULATION: [
            "Challenging workouts",
            "Important presentations/meetings",
            "Social events",
            "Creative activities"
        ],
        TraditionalPhaseType.LUTEAL: [
            "Moderate exercise",
            "Organizational tasks",
            "Meal planning",
            "Relaxation techniques"
        ]
    }
    return recommendations[phase_type]
