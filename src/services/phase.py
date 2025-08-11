"""
Service module for handling menstrual cycle phases and transitions.

This module provides functionality for managing cycle phases, including phase
determination, transitions between phases, and generating phase-specific details
and recommendations.

Typical usage:
    >>> phase = get_current_phase(user_events)
    >>> details = get_phase_details(phase.traditional_phase, cycle_day)
    >>> recommendations = get_phase_specific_recommendations(phase.traditional_phase)
"""
from typing import List, Optional
from datetime import date, timedelta

from src.models.phase import Phase, TraditionalPhaseType, FunctionalPhaseType
from src.models.event import CycleEvent
from src.models.recommendation import Recommendation, RecommendationType
from src.services.constants import (
    TRADITIONAL_PHASE_SYMPTOMS,
    TRADITIONAL_PHASE_DURATIONS,
    FUNCTIONAL_PHASE_DETAILS,
    PHASE_TRANSITIONS,
    FUNCTIONAL_PHASE_MAPPING
)
from src.services.utils import (
    calculate_cycle_day,
    determine_traditional_phase,
    determine_functional_phase,
    get_menstruation_events,
    calculate_functional_phase_duration
)

def get_current_phase(events: List[CycleEvent], target_date: Optional[date] = None) -> Phase:
    """
    Get the current phase based on historical events.
    
    Args:
        events: List of cycle events
        target_date: Optional specific date to analyze
        
    Returns:
        Current Phase object with both traditional and functional phase information
        
    Raises:
        ValueError: If no menstruation events are found
        
    Example:
        >>> events = get_user_events(user_id)
        >>> phase = get_current_phase(events)
        >>> print(f"Current phase: {phase.traditional_phase.value}")
    """
    if not target_date:
        target_date = date.today()

    cycle_day = calculate_cycle_day(events, target_date)
    traditional_phase, duration = determine_traditional_phase(cycle_day)
    functional_phase = determine_functional_phase(cycle_day)
    
    # Calculate traditional phase dates
    menstruation_events = get_menstruation_events(events, reverse=True)
    if not menstruation_events:
        raise ValueError("No menstruation events found")
        
    last_menstruation = menstruation_events[0]
    days_since = (target_date - last_menstruation.date).days
    
    start_date = target_date - timedelta(days=days_since % duration)
    end_date = start_date + timedelta(days=duration)
    
    # Calculate functional phase duration and dates
    func_duration, func_start, func_end = calculate_functional_phase_duration(
        cycle_day,
        functional_phase
    )
    
    # Get phase details
    phase_details = get_phase_details(traditional_phase, cycle_day)
    
    return Phase(
        traditional_phase=traditional_phase,
        functional_phase=functional_phase,
        start_date=start_date,
        end_date=end_date,
        duration=duration,
        functional_phase_duration=func_duration,
        functional_phase_start=func_start,
        functional_phase_end=func_end,
        typical_symptoms=phase_details["traditional_symptoms"],
        dietary_style=phase_details["dietary_style"],
        fasting_protocol=phase_details["fasting_protocol"],
        food_recommendations=phase_details["food_recommendations"],
        activity_recommendations=phase_details["activity_recommendations"],
        supplement_recommendations=phase_details.get("supplement_recommendations"),
        user_notes=None
    )

def predict_next_phase(current_phase: Phase) -> Phase:
    """
    Predict the next phase based on the current phase.
    
    Args:
        current_phase: Current Phase object
        
    Returns:
        Predicted next Phase object
        
    Example:
        >>> current = get_current_phase(events)
        >>> next_phase = predict_next_phase(current)
        >>> print(f"Next phase will be: {next_phase.traditional_phase.value}")
    """
    next_traditional_phase = PHASE_TRANSITIONS[current_phase.traditional_phase]
    next_start_date = current_phase.end_date + timedelta(days=1)
    
    # Calculate cycle day for next phase
    if next_traditional_phase == TraditionalPhaseType.MENSTRUATION:
        cycle_day = 1
    elif next_traditional_phase == TraditionalPhaseType.FOLLICULAR:
        cycle_day = 6  # Day after menstruation
    elif next_traditional_phase == TraditionalPhaseType.OVULATION:
        cycle_day = 15  # Approximate ovulation
    else:  # LUTEAL
        cycle_day = 18  # Start of luteal phase
    
    # Get phase details for the next phase
    phase_details = get_phase_details(next_traditional_phase, cycle_day)
    
    # Map to functional phase
    next_functional_phase = determine_functional_phase(cycle_day)
    
    # Set durations and dates
    duration = TRADITIONAL_PHASE_DURATIONS[next_traditional_phase]
    next_end_date = next_start_date + timedelta(days=duration - 1)
    
    # Calculate functional phase duration and dates
    func_duration, func_start, func_end = calculate_functional_phase_duration(
        cycle_day,
        next_functional_phase
    )
    
    return Phase(
        traditional_phase=next_traditional_phase,
        functional_phase=next_functional_phase,
        start_date=next_start_date,
        end_date=next_end_date,
        duration=duration,
        functional_phase_duration=func_duration,
        functional_phase_start=func_start,
        functional_phase_end=func_end,
        typical_symptoms=phase_details["traditional_symptoms"],
        dietary_style=phase_details["dietary_style"],
        fasting_protocol=phase_details["fasting_protocol"],
        food_recommendations=phase_details["food_recommendations"],
        activity_recommendations=phase_details["activity_recommendations"],
        supplement_recommendations=phase_details.get("supplement_recommendations"),
        user_notes=None
    )

def get_phase_details(traditional_phase: TraditionalPhaseType, cycle_day: int) -> dict:
    """
    Get detailed phase information including symptoms and recommendations.
    
    Args:
        traditional_phase: Traditional menstrual phase type
        cycle_day: Day in the cycle (1-based)
        
    Returns:
        Dictionary containing phase-specific details:
        {
            "traditional_symptoms": List[str],
            "dietary_style": str,
            "fasting_protocol": str,
            "food_recommendations": List[str],
            "activity_recommendations": List[str],
            "supplement_recommendations": Optional[List[str]]
        }
        
    Example:
        >>> details = get_phase_details(TraditionalPhaseType.FOLLICULAR, 8)
        >>> print(details["dietary_style"])
        >>> print(len(details["food_recommendations"]))
    """
    # Map traditional phase to functional phase
    functional_phase = determine_functional_phase(cycle_day)
    
    return {
        "traditional_symptoms": TRADITIONAL_PHASE_SYMPTOMS[traditional_phase],
        **FUNCTIONAL_PHASE_DETAILS[functional_phase]
    }

def get_phase_specific_recommendations(
    traditional_phase: TraditionalPhaseType,
    functional_phase: FunctionalPhaseType,
    cycle_day: int
) -> List[RecommendationType]:
    """
    Get detailed recommendations based on both traditional and functional phases.
    
    Args:
        traditional_phase: Traditional menstrual phase type
        functional_phase: Functional phase type (Power/Manifestation/Nurture)
        cycle_day: Day in the cycle (1-based)
        
    Returns:
        List of RecommendationType objects
    """
    phase_details = get_phase_details(traditional_phase, cycle_day)
    recommendations = []
    
    # Dietary recommendations
    recommendations.extend([
        RecommendationType(
            category="nutrition",
            priority=5,
            description=f"Dietary style: {phase_details['dietary_style']}"
        ),
        RecommendationType(
            category="nutrition",
            priority=4,
            description=f"Fasting protocol: {phase_details['fasting_protocol']}"
        )
    ])
    
    # Food recommendations
    for food_rec in phase_details['food_recommendations']:
        recommendations.append(
            RecommendationType(
                category="nutrition",
                priority=4,
                description=food_rec
            )
        )
    
    # Activity recommendations
    for activity_rec in phase_details['activity_recommendations']:
        recommendations.append(
            RecommendationType(
                category="activity",
                priority=3,
                description=activity_rec
            )
        )
    
    # Supplement recommendations if available
    if phase_details.get('supplement_recommendations'):
        for supp_rec in phase_details['supplement_recommendations']:
            recommendations.append(
            RecommendationType(
                category="nutrition",
                priority=3,
                description=f"Consider supplementing with {supp_rec}"
            )
            )
    
    return recommendations

def generate_phase_report(phase: Phase, events: List[CycleEvent]) -> str:
    """
    Generate a detailed report for the current phase.
    
    Args:
        phase: Current Phase object
        events: List of relevant cycle events
        
    Returns:
        Formatted report string
    """
    report = [
        "🌙 Phase Report",
        f"Traditional Phase: {phase.traditional_phase.value.title()} ({phase.duration} days total)",
        f"Functional Phase: {phase.functional_phase.value.title()} ({phase.functional_phase_duration} days remaining)",
        (f"Period: {phase.start_date} to {phase.end_date} (traditional) | "
         f"{phase.functional_phase_start} to {phase.functional_phase_end} (functional)"),
        "",
        "🩺 Common Symptoms:",
        *[f"• {symptom}" for symptom in phase.typical_symptoms],
        "",
        "🍽️ Dietary Style:",
        f"• {phase.dietary_style}",
        "",
        "⏱️ Fasting Protocol:",
        f"• {phase.fasting_protocol}",
        "",
        "🥗 Recommended Foods:",
        *[f"• {food}" for food in phase.food_recommendations],
        "",
        "💪 Recommended Activities:",
        *[f"• {activity}" for activity in phase.activity_recommendations],
    ]
    
    if phase.supplement_recommendations:
        report.extend([
            "",
            "💊 Supplements to Consider:",
            *[f"• {supplement}" for supplement in phase.supplement_recommendations]
        ])
    
    if events:
        recent_events = [e for e in events if e.notes and e.date >= phase.start_date]
        if recent_events:
            report.extend([
                "",
                "📝 Recent Notes:",
                *[f"• {event.date}: {event.notes}" for event in recent_events]
            ])
    
    return "\n".join(report)
