"""
Service module for generating weekly cycle plans.
"""
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import date, timedelta

try:
    from aws_lambda_powertools import Logger
    logger = Logger()
except ImportError:
    # Fallback for local testing without aws_lambda_powertools
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

from src.models.event import CycleEvent
from src.models.phase import Phase, TraditionalPhaseType, FunctionalPhaseType
from src.models.weekly_plan import WeeklyPlan, PhaseGroup, PhaseRecommendations
from src.services.constants import TRADITIONAL_PHASE_RECOMMENDATIONS, MEAL_ICONS
from src.services.cycle import calculate_next_cycle, analyze_cycle_phase
from src.services.phase import get_phase_details, predict_next_phase
from src.services.recipe import RecipeService
from src.models.recipe import MealRecommendation
from src.services.recipe_selection import RecipeSelectionService, MealSelection


def get_phase_emoji(phase: FunctionalPhaseType) -> str:
    """Get emoji for functional phase."""
    emoji_map = {
        FunctionalPhaseType.POWER: "⚡",
        FunctionalPhaseType.MANIFESTATION: "✨",
        FunctionalPhaseType.NURTURE: "🌱"
    }
    return emoji_map[phase]

def create_phase_recommendations(phase_details: Dict, phase_type: FunctionalPhaseType) -> PhaseRecommendations:
    """
    Create enhanced phase recommendations with recipes.
    
    Args:
        phase_details: Traditional phase details from phase service
        phase_type: Functional phase type for recipe recommendations
        
    Returns:
        Enhanced PhaseRecommendations with recipe suggestions
    """
    try:
        # Initialize recipe service
        recipe_service = RecipeService()
        
        # Get recipe recommendations for this phase
        recipe_recs = recipe_service.get_recipe_recommendations(phase_type)
        
        # Format recipe suggestions and generate shopping list
        recipe_suggestions = format_recipe_suggestions(recipe_recs.meals)
        meal_plan_preview = create_meal_plan_preview(recipe_recs.meals)
        
        # Generate shopping list using RecipeSelectionService
        meal_selections = [
            MealSelection(
                meal_type=meal.meal_type,
                recipe=meal.recipes[0]  # Use first recipe as default selection
            )
            for meal in recipe_recs.meals
        ]
        shopping_list = RecipeSelectionService.generate_shopping_list(meal_selections)
        formatted_shopping_list = RecipeSelectionService.format_shopping_list(shopping_list)
        
        return PhaseRecommendations(
            fasting_protocol=phase_details["fasting_protocol"],
            foods=phase_details["food_recommendations"][:3],  # Top 3 food recommendations
            activities=phase_details["activity_recommendations"][:3],  # Top 3 activities
            supplements=phase_details.get("supplement_recommendations"),
            # Enhanced recipe fields
            recipe_suggestions=recipe_suggestions,
            meal_plan_preview=meal_plan_preview,
            shopping_preview=formatted_shopping_list.splitlines()[:5]  # Top 5 lines of shopping list
        )
        
    except Exception as e:
        logger.warning(f"Failed to load recipes for {phase_type.value} phase: {str(e)}")
        # Graceful fallback - return basic recommendations without recipes
        return PhaseRecommendations(
            fasting_protocol=phase_details["fasting_protocol"],
            foods=phase_details["food_recommendations"][:3],
            activities=phase_details["activity_recommendations"][:3],
            supplements=phase_details.get("supplement_recommendations")
        )

def format_recipe_suggestions(meals: List[MealRecommendation]) -> List[Dict[str, Any]]:
    """
    Convert MealRecommendation objects to dict format for display.
    
    Args:
        meals: List of meal recommendations
        
    Returns:
        List of formatted recipe suggestions using markdown links
    """
    # Use RecipeSelectionService to format recipe options with embedded URLs
    formatted_text = RecipeSelectionService.format_recipe_options(meals)
    
    # Convert to dict format for consistency with existing code
    suggestions = []
    for meal in meals:
        meal_data = {
            "meal_type": meal.meal_type,
            "recipes": [{
                "title": recipe.title,
                "prep_time": recipe.prep_time,
                "tags": recipe.tags,
                "url": recipe.url,
                "formatted_text": f"[{recipe.title}]({recipe.url})" if recipe.url else recipe.title
            } for recipe in meal.recipes],
            "total_prep_time": meal.prep_time_total
        }
        suggestions.append(meal_data)
    
    return suggestions

def create_meal_plan_preview(meals: List[MealRecommendation]) -> List[str]:
    """
    Generate human-readable meal plan preview strings with embedded URLs.
    
    Args:
        meals: List of meal recommendations
        
    Returns:
        List of formatted meal plan strings with clickable recipe links
    """
    preview = []
    for meal in meals:
        emoji = MEAL_ICONS.get(meal.meal_type.lower(), "🍴")
        
        if len(meal.recipes) == 1:
            recipe = meal.recipes[0]
            url_part = f"]({recipe.url})" if recipe.url else "]"
            preview.append(
                f"{emoji} {meal.meal_type.title()}: [{recipe.title}{url_part} "
                f"({recipe.prep_time} min)"
            )
        else:
            # Multiple recipes for this meal type
            recipe_texts = []
            for r in meal.recipes:
                url_part = f"]({r.url})" if r.url else "]"
                recipe_texts.append(f"[{r.title}{url_part} ({r.prep_time} min)")
            preview.append(f"{emoji} {meal.meal_type.title()}: {' or '.join(recipe_texts)}")
    
    return preview

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
                "recommendations": create_phase_recommendations(details, phase.functional_phase)
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
    
    # Group phase groups by functional phase
    functional_groups = {}
    for group in plan.phase_groups:
        if group.functional_phase not in functional_groups:
            functional_groups[group.functional_phase] = {
                'groups': [],
                'recommendations': group.recommendations  # Use first group's recommendations for shared info
            }
        functional_groups[group.functional_phase]['groups'].append(group)
    
    # Format each functional phase
    for functional_phase, data in functional_groups.items():
        formatted.extend([
            "",
            f"{functional_phase.value.title()} Phase {get_phase_emoji(functional_phase)}",
            f"⏱️ Fasting: {data['recommendations'].fasting_protocol}",
            "🥗 Key Foods:",
            *[f"  - {food}" for food in data['recommendations'].foods]
        ])
        
        # Add recipe suggestions if available
        if data['recommendations'].meal_plan_preview:
            formatted.extend([
                "🍽️ Suggested Meals:",
                *[f"  {meal}" for meal in data['recommendations'].meal_plan_preview]
            ])
        
        # Add individual phase groups with their traditional phase and specific activities
        formatted.append("")  # Add space before individual phases
        for group in data['groups']:
            date_range = (
                f"{group.start_date.strftime('%a %d')}-{group.end_date.strftime('%a %d')}"
                if group.start_date != group.end_date
                else f"{group.start_date.strftime('%A %d')}"
            )
            
            formatted.extend([
                f"{date_range}: ({group.traditional_phase.value.title()})",
                f"💪 Activities: {', '.join(TRADITIONAL_PHASE_RECOMMENDATIONS[group.traditional_phase])}"
            ])
        
        # Add supplements if available (shared at functional phase level)
        if data['recommendations'].supplements:
            formatted.extend([
                "",
                "💊 Supplements:",
                *[f"  - {supp}" for supp in data['recommendations'].supplements]
            ])
    
    return formatted
