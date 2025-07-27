"""
Service module for generating weekly cycle plans.
"""
from enum import Enum
from typing import Dict, List, Optional
from datetime import date, timedelta

from src.models.event import CycleEvent
from src.models.phase import Phase, TraditionalPhaseType, FunctionalPhaseType
from src.models.weekly_plan import WeeklyPlan, PhaseGroup, PhaseRecommendations
from src.services.cycle import calculate_next_cycle, analyze_cycle_phase

from src.services.phase import get_phase_details, predict_next_phase


def get_phase_emoji(phase: FunctionalPhaseType) -> str:
    """Get emoji for functional phase."""
    emoji_map = {
        FunctionalPhaseType.POWER: "⚡",
        FunctionalPhaseType.MANIFESTATION: "✨",
        FunctionalPhaseType.NURTURE: "🌱"
    }
    return emoji_map[phase]

def create_phase_recommendations(phase_details: Dict) -> PhaseRecommendations:
    """Create phase recommendations from phase details."""
    return PhaseRecommendations(
        fasting_protocol=phase_details["fasting_protocol"],
        foods=phase_details["food_recommendations"][:3],  # Top 3 food recommendations
        activities=phase_details["activity_recommendations"][:3],  # Top 3 activities
        supplements=phase_details.get("supplement_recommendations")
    )

def group_consecutive_phases(daily_phases: Dict[date, Phase]) -> List[PhaseGroup]:
    """Group consecutive days with the same phase."""
    phase_groups = []
    current_group = {"phase": None, "start": None, "end": None}
    
    for day, phase in daily_phases.items():
        if current_group["phase"] != phase.traditional_phase:
            if current_group["phase"]:
                phase_groups.append(PhaseGroup(
                    start_date=current_group["start"],
                    end_date=current_group["end"],
                    traditional_phase=current_group["phase"],
                    functional_phase=current_group["functional_phase"],
                    recommendations=current_group["recommendations"]
                ))
            details = get_phase_details(phase.traditional_phase, 1)  # Day 1 for base recommendations
            current_group = {
                "phase": phase.traditional_phase,
                "start": day,
                "end": day,
                "functional_phase": phase.functional_phase,
                "recommendations": create_phase_recommendations(details)
            }
        else:
            current_group["end"] = day
    
    # Add last group
    if current_group["phase"]:
        phase_groups.append(PhaseGroup(
            start_date=current_group["start"],
            end_date=current_group["end"],
            traditional_phase=current_group["phase"],
            functional_phase=current_group["functional_phase"],
            recommendations=current_group["recommendations"]
        ))
    
    return phase_groups

def get_daily_phases(
    events: List[CycleEvent],
    start_date: date,
    days: int = 7
) -> Dict[date, Phase]:
    """Get phases for each day in the given range."""
    current_phase = analyze_cycle_phase(events)
    phase = current_phase
    
    daily_phases = {}
    for i in range(days):
        target_date = start_date + timedelta(days=i)
        if target_date >= phase.end_date:
            phase = predict_next_phase(phase)
        daily_phases[target_date] = phase
    
    return daily_phases

def generate_weekly_plan(events: List[CycleEvent], start_date: Optional[date] = None) -> WeeklyPlan:
    """
    Generate a weekly plan based on cycle events.
    
    Args:
        events: List of cycle events
        start_date: Optional start date, defaults to tomorrow
        
    Returns:
        WeeklyPlan object containing phase predictions and recommendations
    """
    if not events:
        raise ValueError("No events provided for plan generation")
    
    if start_date is None:
        start_date = date.today() + timedelta(days=1)  # Start from tomorrow
        
    end_date = start_date + timedelta(days=6)
    
    # Get next cycle prediction
    next_cycle_date, avg_duration, warning = calculate_next_cycle(events)
    
    # Only include cycle prediction if it falls within the week
    if next_cycle_date and (next_cycle_date < start_date or next_cycle_date > end_date):
        next_cycle_date = None
        avg_duration = None
        warning = None
    
    # Get phases for each day
    daily_phases = get_daily_phases(events, start_date)
    
    # Group consecutive phases
    phase_groups = group_consecutive_phases(daily_phases)
    
    return WeeklyPlan(
        start_date=start_date,
        end_date=end_date,
        next_cycle_date=next_cycle_date,
        avg_cycle_duration=avg_duration,
        warning=warning,
        phase_groups=phase_groups
    )

def format_weekly_plan(plan: WeeklyPlan) -> List[str]:
    """
    Format a weekly plan into a list of strings for display.
    
    Args:
        plan: WeeklyPlan object
        
    Returns:
        List of formatted strings
    """
    formatted = [
        f"📅 Next Week's Plan ({plan.start_date.strftime('%b %d')} - {plan.end_date.strftime('%b %d')})",
        "------------------------"
    ]
    
    # Add cycle prediction only if it falls within this week's plan
    if plan.next_cycle_date:
        formatted.extend([
            "🔮 Cycle Prediction:",
            f"• Next cycle expected to start: {plan.next_cycle_date.strftime('%A, %b %d')}",
            f"• Average cycle length: {plan.avg_cycle_duration} days",
            ""
        ])
        if plan.warning:
            formatted.extend([f"⚠️ Note: {plan.warning}", ""])
        formatted.append("")  # Extra space before phase schedule
    
    # Add phase breakdown
    formatted.extend(["🌙 Phase Schedule:"])
    for group in plan.phase_groups:
        date_range = (
            f"{group.start_date.strftime('%a %d')}-{group.end_date.strftime('%a %d')}"
            if group.start_date != group.end_date
            else f"{group.start_date.strftime('%A %d')}"
        )
        
        formatted.extend([
            "",
            f"{date_range}: {group.functional_phase.value.title()} Phase {get_phase_emoji(group.functional_phase)}",
            f"({group.traditional_phase.value.title()})",
            f"⏱️ Fasting: {group.recommendations.fasting_protocol}",
            "🥗 Key Foods:",
            *[f"  - {food}" for food in group.recommendations.foods],
            "💪 Activities:",
            *[f"  - {activity}" for activity in group.recommendations.activities]
        ])
        
        if group.recommendations.supplements:
            formatted.extend([
                "💊 Supplements:",
                *[f"  - {supp}" for supp in group.recommendations.supplements]
            ])
    
    return formatted
