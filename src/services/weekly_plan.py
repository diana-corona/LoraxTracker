"""
Service module for generating weekly cycle plans.
"""
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import date, datetime, timedelta

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
        # Initialize recipe service and load recipes for this phase
        recipe_service = RecipeService()
        recipe_service.load_recipes_for_meal_planning(phase_type.value.lower())
        
        # Get recipe recommendations for each meal type
        meal_types = ['breakfast', 'lunch', 'dinner', 'snack']
        recipe_recs = []
        recipe_ids = []  # Keep track of recipe IDs we'll need ingredients for
        
        for meal_type in meal_types:
            recipes = recipe_service.get_recipes_by_meal_type(
                meal_type=meal_type,
                phase=phase_type.value.lower(),
                limit=2  # Get up to 2 recipes per meal type
            )
            if recipes:
                # Keep track of first recipe's ID for ingredients
                if recipes[0]['id'] not in recipe_ids:
                    recipe_ids.append(recipes[0]['id'])
                    
                recipe_recs.append({
                    'meal_type': meal_type,
                    'recipes': [recipe for recipe in recipes]
                })
        
        # Format recipe suggestions and generate shopping list
        recipe_suggestions = format_recipe_suggestions(recipe_recs)
        meal_plan_preview = create_meal_plan_preview(recipe_recs)
        
        # Get ingredients for all unique recipes
        ingredients = recipe_service.get_multiple_recipe_ingredients(recipe_ids)
        
        # Format ingredients into shopping preview
        shopping_preview = []
        if ingredients.proteins:
            shopping_preview.extend(["🥩 Proteins:"] + [f"  • {item}" for item in ingredients.proteins][:3])
        if ingredients.produce:
            shopping_preview.extend(["🥬 Produce:"] + [f"  • {item}" for item in ingredients.produce][:3])
        if ingredients.dairy:
            shopping_preview.extend(["🥛 Dairy:"] + [f"  • {item}" for item in ingredients.dairy][:3])
        
        return PhaseRecommendations(
            fasting_protocol=phase_details["fasting_protocol"],
            foods=phase_details["food_recommendations"][:3],  # Top 3 food recommendations
            activities=phase_details["activity_recommendations"][:3],  # Top 3 activities
            supplements=phase_details.get("supplement_recommendations"),
            # Enhanced recipe fields
            recipe_suggestions=recipe_suggestions,
            meal_plan_preview=meal_plan_preview,
            shopping_preview=shopping_preview[:10]  # Show up to 10 lines of shopping list
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

def format_recipe_suggestions(meals: List[Dict]) -> List[Dict[str, Any]]:
    """
    Convert dictionary of meal recommendations to display format.
    
    Args:
        meals: List of meal recommendation dictionaries
        
    Returns:
        List of formatted recipe suggestions using markdown links
    """
    suggestions = []
    for meal in meals:
        meal_data = {
            "meal_type": meal['meal_type'],
            "recipes": [{
                "title": recipe['title'],
                "prep_time": recipe.get('prep_time', 0),
                "id": recipe['id'],
                "formatted_text": f"[{recipe['title']}](/recipes/{meal['meal_type']}/{recipe['id']})"
            } for recipe in meal['recipes']],
            "total_prep_time": sum(r.get('prep_time', 0) for r in meal['recipes'])
        }
        suggestions.append(meal_data)
    
    return suggestions

def create_meal_plan_preview(meals: List[Dict]) -> List[str]:
    """
    Generate human-readable meal plan preview strings.
    
    Args:
        meals: List of meal recommendation dictionaries
        
    Returns:
        List of formatted meal plan strings with clickable recipe links
    """
    preview = []
    for meal in meals:
        emoji = MEAL_ICONS.get(meal['meal_type'].lower(), "🍴")
        
        if len(meal['recipes']) == 1:
            recipe = meal['recipes'][0]
            preview.append(
                f"{emoji} {meal['meal_type'].title()}: [{recipe['title']}](/recipes/{meal['meal_type']}/{recipe['id']}) "
                f"({recipe.get('prep_time', 0)} min)"
            )
        else:
            # Multiple recipes for this meal type
            recipe_texts = []
            for r in meal['recipes']:
                recipe_texts.append(f"[{r['title']}](/recipes/{meal['meal_type']}/{r['id']}) ({r.get('prep_time', 0)} min)")
            preview.append(f"{emoji} {meal['meal_type'].title()}: {' or '.join(recipe_texts)}")
    
    return preview

def group_consecutive_phases(daily_phases: Dict[date, Phase]) -> List[PhaseGroup]:
    """Group consecutive days with the same phase."""
    phase_groups = []
    current_group = {"phase": None, "start": None, "end": None}
    sorted_dates = sorted(daily_phases.keys())
    
    for i, day in enumerate(sorted_dates):
        phase = daily_phases[day]
        next_day = sorted_dates[i + 1] if i < len(sorted_dates) - 1 else None
        next_phase = daily_phases[next_day] if next_day else None
        
        # Check if this is a second Power phase occurrence
        is_second_power = (
            phase.functional_phase == FunctionalPhaseType.POWER
            and phase.start_date >= date(phase.start_date.year, phase.start_date.month, 16)
        )
        
        if current_group["phase"] != phase.traditional_phase:
            if current_group["phase"]:
                phase_groups.append(PhaseGroup(
                    start_date=current_group["start"],
                    end_date=current_group["end"],
                    traditional_phase=current_group["phase"],
                    functional_phase=current_group["functional_phase"],
                    functional_phase_duration=current_group["func_duration"],
                    functional_phase_start=current_group["func_start"],
                    functional_phase_end=current_group["func_end"],
                    is_power_phase_second_occurrence=current_group["is_second_power"],
                    next_functional_phase=current_group["next_func_phase"],
                    recommendations=current_group["recommendations"],
                    next_phase_recommendations=current_group["next_phase_recommendations"]
                ))
            
            details = get_phase_details(phase.traditional_phase, 1)  # Day 1 for base recommendations
            
            # Get recommendations for both current and next phase (if transitioning)
            current_recs = create_phase_recommendations(details, phase.functional_phase)
            next_recs = None
            if next_phase:
                # Always create next phase recommendations when available
                next_details = get_phase_details(next_phase.traditional_phase, 1)
                next_recs = create_phase_recommendations(next_details, next_phase.functional_phase)
                logger.info("Created next phase recommendations", extra={
                    "current_phase": phase.functional_phase.value,
                    "next_phase": next_phase.functional_phase.value,
                    "days_to_end": (phase.functional_phase_end - datetime.now().date()).days
                })
            
            current_group = {
                "phase": phase.traditional_phase,
                "start": day,
                "end": day,
                "functional_phase": phase.functional_phase,
                "func_duration": phase.functional_phase_duration,
                "func_start": phase.functional_phase_start,
                "func_end": phase.functional_phase_end,
                "is_second_power": is_second_power,
                "next_func_phase": next_phase.functional_phase if next_phase else None,
                "recommendations": current_recs,
                "next_phase_recommendations": next_recs
            }
        else:
            current_group["end"] = day
            current_group["func_duration"] = phase.functional_phase_duration
            current_group["func_end"] = phase.functional_phase_end
            current_group["next_func_phase"] = next_phase.functional_phase if next_phase else None
            
            # Always update next phase recommendations when available
            if next_phase:
                next_details = get_phase_details(next_phase.traditional_phase, 1)
                current_group["next_phase_recommendations"] = create_phase_recommendations(
                    next_details,
                    next_phase.functional_phase
                )
                logger.info("Updated next phase recommendations", extra={
                    "current_phase": phase.functional_phase.value,
                    "next_phase": next_phase.functional_phase.value,
                    "days_to_end": (phase.functional_phase_end - datetime.now().date()).days,
                    "start_date": phase.functional_phase_start.isoformat(),
                    "end_date": phase.functional_phase_end.isoformat(),
                    "has_next_recs": bool(next_recs)
                })
    
    # Add last group
    if current_group["phase"]:
        phase_groups.append(PhaseGroup(
            start_date=current_group["start"],
            end_date=current_group["end"],
            traditional_phase=current_group["phase"],
            functional_phase=current_group["functional_phase"],
            functional_phase_duration=current_group["func_duration"],
            functional_phase_start=current_group["func_start"],
            functional_phase_end=current_group["func_end"],
            is_power_phase_second_occurrence=current_group["is_second_power"],
            next_functional_phase=current_group["next_func_phase"],
            recommendations=current_group["recommendations"],
            next_phase_recommendations=current_group["next_phase_recommendations"]
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
            next_phase = predict_next_phase(phase)
            logger.info("Phase transition detected", extra={
                "date": target_date.isoformat(),
                "current_phase": phase.functional_phase.value,
                "next_phase": next_phase.functional_phase.value,
                "current_end": phase.functional_phase_end.isoformat(),
                "next_start": next_phase.functional_phase_start.isoformat(),
                "is_power_phase": phase.functional_phase == FunctionalPhaseType.POWER,
                "is_second_power": phase.start_date >= date(phase.start_date.year, phase.start_date.month, 16),
                "next_phase_sequence": {
                    "power_first": FunctionalPhaseType.MANIFESTATION.value,
                    "manifestation": FunctionalPhaseType.POWER.value,
                    "power_second": FunctionalPhaseType.NURTURE.value,
                    "nurture": FunctionalPhaseType.POWER.value
                }
            })
            phase = next_phase
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
        start_date = datetime.now().date() + timedelta(days=1)  # Start from tomorrow
        
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
    
    enhanced_plan = WeeklyPlan(
        start_date=start_date,
        end_date=end_date,
        next_cycle_date=next_cycle_date,
        avg_cycle_duration=avg_duration,
        warning=warning,
        phase_groups=phase_groups
    )
    
    logger.info("Generated enhanced weekly plan", extra={
        "start_date": start_date,
        "end_date": end_date,
        "phase_groups": len(phase_groups),
        "has_transitions": any(pg.has_phase_transition for pg in phase_groups)
    })
    
    return enhanced_plan

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
        formatted.extend([""])
        
        # Get first group for this functional phase to show phase-wide info
        first_group = data['groups'][0]
        days_remaining = max(0, (first_group.functional_phase_end - datetime.now().date()).days)
        
        # Log phase transitions for troubleshooting
        logger.info("Phase transition details", extra={
            "functional_phase": functional_phase.value,
            "days_remaining": days_remaining,
            "end_date": first_group.end_date.isoformat(),
            "func_phase_end": first_group.functional_phase_end.isoformat(),
            "has_next_phase": bool(first_group.next_functional_phase),
            "next_phase_recs": bool(first_group.next_phase_recommendations)
        })
        
        # Format phase label
        phase_label = f"{functional_phase.value.title()} Phase {get_phase_emoji(functional_phase)}"
        if first_group.is_power_phase_second_occurrence:
            phase_label += " (Second Occurrence)"
        phase_label += f" ({days_remaining} days remaining)"
        formatted.append(phase_label)
        
        formatted.extend([
            f"⏱️ Fasting: {data['recommendations'].fasting_protocol}",
            "🥗 Key Foods:",
            *[f"  - {food}" for food in data['recommendations'].foods]
        ])
        
        # Find the group with the soonest transition
        min_days_until_transition = float('inf')
        transitioning_group = None
        
        for group in data['groups']:
            days_until = (group.functional_phase_end - datetime.now().date()).days
            if days_until < min_days_until_transition:
                min_days_until_transition = days_until
                transitioning_group = group
        
        if not transitioning_group:
            transitioning_group = data['groups'][-1]  # Fallback to last group
        
        days_until_transition = min_days_until_transition
        
        # Log next phase display conditions
        logger.info("Next phase display check", extra={
            "current_phase": functional_phase.value,
            "has_next_phase": bool(transitioning_group.next_functional_phase),
            "has_next_phase_recs": bool(transitioning_group.next_phase_recommendations),
            "days_until_transition": days_until_transition,
            "next_phase": transitioning_group.next_functional_phase.value if transitioning_group.next_functional_phase else None,
            "transition_group_end": transitioning_group.functional_phase_end.isoformat(),
            "should_show": bool(transitioning_group.next_functional_phase 
                              and transitioning_group.next_phase_recommendations 
                              and (days_until_transition <= 3 or days_until_transition < 0))
        })
        
        # Show next phase if we're within 3 days of transition or have passed the end
        if (transitioning_group.next_functional_phase 
            and transitioning_group.next_phase_recommendations 
            and (days_until_transition <= 3 or days_until_transition < 0)):
            logger.info("Next phase will be shown", extra={
                "current_phase": functional_phase.value,
                "next_phase": transitioning_group.next_functional_phase.value,
                "days_until_transition": days_until_transition,
                "today": datetime.now().date().isoformat(),
                "phase_end": transitioning_group.functional_phase_end.isoformat()
            })
            next_phase_start = (transitioning_group.functional_phase_end + timedelta(days=1)).strftime('%A, %b %d')
            formatted.extend([
                "",
                f"Next Phase: {transitioning_group.next_functional_phase.value.title()} {get_phase_emoji(transitioning_group.next_functional_phase)} (starting {next_phase_start})",
                f"⏱️ Fasting: {transitioning_group.next_phase_recommendations.fasting_protocol}",
                "🥗 Key Foods:",
                *[f"  - {food}" for food in transitioning_group.next_phase_recommendations.foods]
            ])
            
            logger.info("Next phase details", extra={
                "current_phase": functional_phase.value,
                "next_phase": transitioning_group.next_functional_phase.value,
                "days_until_transition": days_until_transition,
                "transition_date": next_phase_start
            })
        
        # Add supplements if available (shared at functional phase level)
        if data['recommendations'].supplements:
            formatted.extend([
                "",
                "💊 Supplements:",
                *[f"  - {supp}" for supp in data['recommendations'].supplements]
            ])
    
    return formatted
