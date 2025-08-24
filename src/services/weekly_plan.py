"""
Service module for generating weekly cycle plans.
"""
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
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
from src.services.constants import (
    TRADITIONAL_PHASE_RECOMMENDATIONS,
    MEAL_ICONS,
    FUNCTIONAL_PHASE_MAPPING,
    TRADITIONAL_PHASE_DURATIONS,
    PHASE_TRANSITIONS
)
from src.services.utils import calculate_cycle_day
from src.services.cycle import calculate_next_cycle, analyze_cycle_phase
from src.services.phase import get_phase_details, predict_next_phase
from src.services.recipe import RecipeService
from src.models.recipe import Recipe, MealRecommendation
from src.services.recipe_selection import RecipeSelectionService, MealSelection


def get_phase_emoji(phase: FunctionalPhaseType) -> str:
    """Get emoji for functional phase."""
    emoji_map = {
        FunctionalPhaseType.POWER: "⚡",
        FunctionalPhaseType.MANIFESTATION: "✨",
        FunctionalPhaseType.NURTURE: "🌱"
    }
    return emoji_map[phase]

def create_phase_recommendations(
    phase_details: Dict,
    phase_type: FunctionalPhaseType,
    phase_groups: Optional[List[Dict]] = None,
    user_id: Optional[str] = None
) -> PhaseRecommendations:
    """
    Create enhanced phase recommendations with recipes.
    
    Args:
        phase_details: Traditional phase details from phase service
        phase_type: Functional phase type for recipe recommendations
        phase_groups: List of phase groups from weekly plan
        user_id: Optional user ID for recipe history tracking
        
    Returns:
        Enhanced PhaseRecommendations with recipe suggestions
    """
    recipe_recs = []
    recipe_ids = []  # Keep track of recipe IDs we'll need ingredients for
    recipe_service = RecipeService()
    
    try:
        # Initialize recipe service and load recipes considering multiple phases
        # Convert phase_groups to expected format if provided
        formatted_groups = None
        if phase_groups:
            formatted_groups = [{
                'functional_phase': group.functional_phase,
                'start_date': group.start_date,
                'end_date': group.end_date
            } for group in phase_groups]
        
        # Load recipes with proper error handling
        try:
            all_phase_recipes = recipe_service.load_recipes_for_multi_phase_week(formatted_groups, user_id)
            phase = phase_type.value.lower()
            phase_recipes = all_phase_recipes.get(phase, {}) if all_phase_recipes else {}
        except Exception as e:
            logger.warning(f"Failed to load recipes for {phase_type.value} phase: {str(e)}")
            phase_recipes = {}
        
        # Get recipe recommendations for each meal type
        for meal_type in ['breakfast', 'lunch', 'dinner', 'snack']:
            recipes_data = phase_recipes.get(meal_type, [])
            if recipes_data:
                # Convert recipe data to Recipe objects
                recipes = []
                total_prep_time = 0
                for r in recipes_data:
                    recipe = Recipe(
                        title=r['title'],
                        phase=phase,
                        prep_time=r.get('prep_time', 0),
                        tags=[meal_type] if meal_type else [],
                        ingredients=[],  # Will be populated when needed
                        instructions=[],
                        notes=None,
                        url=r.get('url'),
                        file_path=r['file_path']
                    )
                    recipes.append(recipe)
                    total_prep_time += recipe.prep_time

                # Keep track of first recipe's ID for ingredients
                recipe_id = recipes[0].file_path.split("/")[-1].split(".")[0]
                if recipe_id not in recipe_ids:
                    recipe_ids.append(recipe_id)
                    
                recipe_recs.append(MealRecommendation(
                    meal_type=meal_type,
                    recipes=recipes,
                    prep_time_total=total_prep_time
                ))
        
        # Format recipe suggestions and generate shopping list
        recipe_suggestions = format_recipe_suggestions(recipe_recs) if recipe_recs else []
        meal_plan_preview = create_meal_plan_preview(recipe_recs) if recipe_recs else []
        
        # Get recipe recommendations and shopping preview
        phase_recommendations = recipe_service.get_recipe_recommendations(phase_type)
        shopping_preview = phase_recommendations.shopping_list_preview if phase_recommendations else []
        # Remove category headers and bullet points for clean ingredient list
        cleaned_preview = []
        for item in shopping_preview:
            if not any(item.startswith(x) for x in ['🥩', '🥬', '🥛']):
                cleaned = item.strip('• ').strip()
                if cleaned:  # Only add non-empty strings
                    cleaned_preview.append(cleaned)
        shopping_preview = cleaned_preview
        
        # Get ingredients for all unique recipes (for backward compatibility)
        try:
            ingredients = recipe_service.get_multiple_recipe_ingredients(recipe_ids)
        except Exception as e:
            logger.warning(f"Failed to get ingredients: {str(e)}")
            ingredients = []

        # Ensure we have at least empty lists for recipe fields
        recipe_suggestions = recipe_suggestions or []
        meal_plan_preview = meal_plan_preview or ["No specific meals available for this phase"]
        shopping_preview = shopping_preview or []

        recs = PhaseRecommendations(
            fasting_protocol=phase_details["fasting_protocol"],
            foods=phase_details["food_recommendations"][:3],  # Top 3 food recommendations
            activities=phase_details["activity_recommendations"][:3],  # Top 3 activities
            supplements=phase_details.get("supplement_recommendations"),
            # Enhanced recipe fields
            recipe_suggestions=recipe_suggestions,
            meal_plan_preview=meal_plan_preview,
            shopping_preview=shopping_preview[:10]  # Show up to 10 lines of shopping list
        )
        
        return recs
        
    except Exception as e:
        logger.warning(f"Failed to load recommendations for {phase_type.value} phase: {str(e)}")
        # Graceful fallback - return basic recommendations without recipe fields
        return PhaseRecommendations(
            fasting_protocol=phase_details["fasting_protocol"],
            foods=phase_details["food_recommendations"][:3],
            activities=phase_details["activity_recommendations"][:3],
            supplements=phase_details.get("supplement_recommendations"),
            recipe_suggestions=None,
            meal_plan_preview=None,
            shopping_preview=None
        )

def format_recipe_suggestions(meals: List[MealRecommendation]) -> List[Dict[str, Any]]:
    """
    Convert MealRecommendation objects to display format.
    
    Args:
        meals: List of MealRecommendation objects
        
    Returns:
        List of formatted recipe suggestions using markdown links
    """
    suggestions = []
    for meal in meals:
        meal_data = {
            "meal_type": meal.meal_type,
            "recipes": [{
                "title": recipe.title,
                "prep_time": recipe.prep_time,
                "tags": recipe.tags,
                "url": recipe.url,
                "id": recipe.file_path.split("/")[-1].split(".")[0],  # Extract ID from file path
            } for recipe in meal.recipes],
            "total_prep_time": meal.prep_time_total
        }
        suggestions.append(meal_data)
    
    return suggestions

def create_meal_plan_preview(meals: List[MealRecommendation]) -> List[str]:
    """
    Generate human-readable meal plan preview strings.
    
    Args:
        meals: List of MealRecommendation objects
        
    Returns:
        List of formatted meal plan strings with clickable recipe links
    """
    preview = []
    for meal in meals:
        emoji = MEAL_ICONS.get(meal.meal_type.lower(), "🍴")
        
        if len(meal.recipes) == 1:
            recipe = meal.recipes[0]
            recipe_text = f"{recipe.title} ({recipe.prep_time} min)"
            preview.append(f"{emoji} {meal.meal_type.title()}: {recipe_text}")
            if recipe.url:
                preview[-1] += f" - {recipe.url}"
        else:
            # Multiple recipes for this meal type
            recipe_texts = []
            for r in meal.recipes:
                recipe_text = f"{r.title} ({r.prep_time} min)"
                recipe_texts.append(recipe_text)
                if r.url:
                    recipe_texts[-1] += f" - {r.url}"
            preview.append(f"{emoji} {meal.meal_type.title()}: {' or '.join(recipe_texts)}")
    
    return preview

def group_consecutive_phases(
    daily_phases: Dict[date, Phase],
    user_id: Optional[str] = None
) -> List[PhaseGroup]:
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
            current_recs = create_phase_recommendations(details, phase.functional_phase, phase_groups, user_id)
            next_recs = None
            if next_phase:
                # Always create next phase recommendations when available
                next_details = get_phase_details(next_phase.traditional_phase, 1)
                next_recs = create_phase_recommendations(next_details, next_phase.functional_phase, phase_groups, user_id)
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
                    next_phase.functional_phase,
                    phase_groups,
                    user_id
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
        # For the last group, ensure we have proper phase transition information
        next_phase_type = PHASE_TRANSITIONS[current_group["phase"]]
        next_details = get_phase_details(next_phase_type, 1)  # Use day 1 for base recommendations
        next_recs = create_phase_recommendations(next_details, current_group["next_func_phase"] or current_group["functional_phase"])
        
        # Log phase group creation
        logger.info(f"Creating final phase group", extra={
            "traditional_phase": current_group["phase"].value,
            "functional_phase": current_group["functional_phase"].value,
            "start_date": current_group["start"].isoformat(),
            "end_date": current_group["end"].isoformat(),
            "next_phase_type": next_phase_type.value
        })
        
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
            next_phase_recommendations=next_recs
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
    if not events:
        return daily_phases
    for i in range(days):
        target_date = start_date + timedelta(days=i)
        # Calculate cycle day for this target date
        cycle_day = calculate_cycle_day(events, target_date)
        
        # Get the most recent event before target date, prioritizing recent events
        recent_events = sorted(events, key=lambda x: x.date, reverse=True)
        current_event = next((e for e in recent_events if e.date <= target_date), None)
        
        # Get most recent follicular event
        follicular_event = next((e for e in recent_events 
                               if e.date <= target_date and
                               e.state == TraditionalPhaseType.FOLLICULAR.value), None)
        
        # Get the next future event
        future_event = next((e for e in sorted(events, key=lambda x: x.date) 
                           if e.date > target_date), None)
        
        # Initialize variables
        phase_type = None
        remaining_days = cycle_day
        total_duration = sum(TRADITIONAL_PHASE_DURATIONS.values())
        
        # Normalize cycle day to be within total duration
        if remaining_days > total_duration:
            remaining_days = (remaining_days - 1) % total_duration + 1
        
        # First check follicular events to ensure proper phase transition
        if follicular_event:
            days_since_follicular = (target_date - follicular_event.date).days
            # Keep follicular phase for its full duration (usually 7-10 days)
            if days_since_follicular <= TRADITIONAL_PHASE_DURATIONS[TraditionalPhaseType.FOLLICULAR]:
                phase_type = TraditionalPhaseType.FOLLICULAR
                logger.info(f"Using follicular event for {target_date}", extra={
                    "event_date": follicular_event.date.isoformat(),
                    "days_diff": days_since_follicular,
                    "duration": TRADITIONAL_PHASE_DURATIONS[TraditionalPhaseType.FOLLICULAR]
                })
            # If we're past follicular duration, transition to ovulation
            elif days_since_follicular <= (TRADITIONAL_PHASE_DURATIONS[TraditionalPhaseType.FOLLICULAR] + 
                                        TRADITIONAL_PHASE_DURATIONS[TraditionalPhaseType.OVULATION]):
                phase_type = TraditionalPhaseType.OVULATION
        # Then check recent events within 3 days
        elif current_event and (target_date - current_event.date).days <= 3:
            phase_type = TraditionalPhaseType(current_event.state)
            logger.info(f"Using current event phase for {target_date}", extra={
                "phase": current_event.state,
                "event_date": current_event.date.isoformat(),
                "days_diff": (target_date - current_event.date).days
            })
        # Check future events next
        elif future_event and (future_event.date - target_date).days <= 3:
            phase_type = TraditionalPhaseType(future_event.state)
            logger.info(f"Using future event phase for {target_date}", extra={
                "phase": future_event.state,
                "event_date": future_event.date.isoformat(),
                "days_diff": (future_event.date - target_date).days
            })
        # If no phase type determined yet and no recent events within 3 days, use cycle day calculation
        if not phase_type:
            # Use cycle day directly to determine phase
            menstruation_end = TRADITIONAL_PHASE_DURATIONS[TraditionalPhaseType.MENSTRUATION]
            follicular_end = menstruation_end + TRADITIONAL_PHASE_DURATIONS[TraditionalPhaseType.FOLLICULAR]
            ovulation_end = follicular_end + TRADITIONAL_PHASE_DURATIONS[TraditionalPhaseType.OVULATION]
            
            # Normalize cycle day to be within cycle if it's too large
            total_duration = sum(TRADITIONAL_PHASE_DURATIONS.values())
            if cycle_day > total_duration:
                cycle_day = ((cycle_day - 1) % total_duration) + 1
            
            # Log cycle day and boundaries
            logger.info(f"Calculating phase for cycle day {cycle_day}", extra={
                "cycle_day": cycle_day,
                "normalized_cycle_day": cycle_day,
                "menstruation_end": menstruation_end,
                "follicular_end": follicular_end,
                "ovulation_end": ovulation_end,
                "total_duration": total_duration
            })
            
            # Determine phase based on normalized cycle day
            if cycle_day <= menstruation_end:
                phase_type = TraditionalPhaseType.MENSTRUATION
            elif cycle_day <= follicular_end:
                phase_type = TraditionalPhaseType.FOLLICULAR
            elif cycle_day <= ovulation_end:
                phase_type = TraditionalPhaseType.OVULATION
            else:
                phase_type = TraditionalPhaseType.LUTEAL
                
            # Log determined phase
            logger.info(f"Determined phase for cycle day {cycle_day}", extra={
                "cycle_day": cycle_day,
                "phase": phase_type.value,
                "remaining_days": remaining_days
            })

            # Calculate boundaries for logging
            phase_boundaries = {
                "menstruation_end": TRADITIONAL_PHASE_DURATIONS[TraditionalPhaseType.MENSTRUATION],
                "follicular_end": (TRADITIONAL_PHASE_DURATIONS[TraditionalPhaseType.MENSTRUATION] +
                                 TRADITIONAL_PHASE_DURATIONS[TraditionalPhaseType.FOLLICULAR]),
                "ovulation_end": (TRADITIONAL_PHASE_DURATIONS[TraditionalPhaseType.MENSTRUATION] +
                                TRADITIONAL_PHASE_DURATIONS[TraditionalPhaseType.FOLLICULAR] +
                                TRADITIONAL_PHASE_DURATIONS[TraditionalPhaseType.OVULATION]),
                "luteal_end": total_duration
            }

            # Log phase calculation details using cumulative durations
            logger.info(f"Phase calculation for {target_date}", extra={
                "cycle_day": cycle_day,
                "phase": phase_type.value,
                "boundaries": {
                    "menstruation_end": TRADITIONAL_PHASE_DURATIONS[TraditionalPhaseType.MENSTRUATION],
                    "follicular_end": (TRADITIONAL_PHASE_DURATIONS[TraditionalPhaseType.MENSTRUATION] + 
                                     TRADITIONAL_PHASE_DURATIONS[TraditionalPhaseType.FOLLICULAR]),
                    "ovulation_end": (TRADITIONAL_PHASE_DURATIONS[TraditionalPhaseType.MENSTRUATION] + 
                                    TRADITIONAL_PHASE_DURATIONS[TraditionalPhaseType.FOLLICULAR] +
                                    TRADITIONAL_PHASE_DURATIONS[TraditionalPhaseType.OVULATION]),
                    "luteal_end": total_duration
                }
            })

            # Final fallback
            if not phase_type:
                phase_type = TraditionalPhaseType.MENSTRUATION
                
            logger.info(f"Using calculated phase for {target_date}", extra={
                "phase": phase_type.value,
                "cycle_day": cycle_day,
                "remaining_days": remaining_days
            })

        # Get phase details and create Phase object
        phase_details = get_phase_details(phase_type, cycle_day)
        phase = Phase(
            start_date=target_date,
            end_date=target_date + timedelta(days=7),
            traditional_phase=phase_type,
            functional_phase=current_phase.functional_phase,
            functional_phase_start=current_phase.functional_phase_start,
            functional_phase_end=current_phase.functional_phase_end,
            functional_phase_duration=current_phase.functional_phase_duration,
            duration=TRADITIONAL_PHASE_DURATIONS[phase_type],
            typical_symptoms=phase_details["traditional_symptoms"],
            dietary_style=phase_details["dietary_style"],
            fasting_protocol=phase_details["fasting_protocol"],
            food_recommendations=phase_details["food_recommendations"],
            activity_recommendations=phase_details["activity_recommendations"]
        )
        
        # Determine next phase type
        next_phase_type = PHASE_TRANSITIONS[phase_type]
        
        # Check if any upcoming events should override the next phase
        if future_event and (future_event.date - target_date).days <= 3:
            next_phase_type = TraditionalPhaseType(future_event.state)
        
        # Check for second Power phase occurrence
        is_second_power = (
            phase.functional_phase == FunctionalPhaseType.POWER and
            any(start <= cycle_day <= end 
                for start, end, p in FUNCTIONAL_PHASE_MAPPING 
                if start >= 16 and p == FunctionalPhaseType.POWER)
        )
        
        # Determine next functional phase
        next_functional_phase = current_phase.functional_phase
        if is_second_power:
            next_functional_phase = FunctionalPhaseType.NURTURE
            logger.info("Second Power phase transitioning to Nurture", extra={
                "cycle_day": cycle_day,
                "target_date": target_date.isoformat()
            })
            
        # Create next phase
        next_phase_details = get_phase_details(next_phase_type, cycle_day + 1)
        next_phase = Phase(
            start_date=target_date + timedelta(days=1),
            end_date=target_date + timedelta(days=7),
            traditional_phase=next_phase_type,
            functional_phase=next_functional_phase,
            functional_phase_start=phase.functional_phase_start,
            functional_phase_end=phase.functional_phase_end,
            functional_phase_duration=7 if is_second_power else phase.functional_phase_duration,
            duration=TRADITIONAL_PHASE_DURATIONS[next_phase_type],
            typical_symptoms=next_phase_details["traditional_symptoms"],
            dietary_style=next_phase_details["dietary_style"],
            fasting_protocol=next_phase_details["fasting_protocol"],
            food_recommendations=next_phase_details["food_recommendations"],
            activity_recommendations=next_phase_details["activity_recommendations"]
        )
        
        logger.info(f"Phase transition for {target_date}", extra={
            "current_phase": phase.traditional_phase.value,
            "next_phase": next_phase.traditional_phase.value,
            "is_power_phase": phase.functional_phase == FunctionalPhaseType.POWER,
            "is_second_power": is_second_power
        })
        
        # Store the phase in daily_phases
        daily_phases[target_date] = phase
        
        phase = next_phase
    
    return daily_phases

def generate_weekly_plan(
    events: List[CycleEvent], 
    start_date: Optional[date] = None,
    user_id: Optional[str] = None
) -> WeeklyPlan:
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
        
    end_date = start_date + timedelta(days=6)  # Seven days total (tomorrow through next week)
    
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
    phase_groups = group_consecutive_phases(daily_phases, user_id)
    
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

def format_weekly_plan(
    plan: WeeklyPlan, 
    events: Optional[List[CycleEvent]] = None,
    user_id: Optional[str] = None,
    include_meals: bool = True,
    _testing: bool = False
) -> List[str]:
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
        # Get phase details from the Phase object to match /phase command
        days_remaining = first_group.functional_phase_duration
        if events:
            current_phase = analyze_cycle_phase(events)
            days_remaining = current_phase.functional_phase_duration
        
        # Log phase transitions for troubleshooting
        logger.info("Phase transition details", extra={
            "functional_phase": functional_phase.value,
            "days_remaining": days_remaining,
            "end_date": first_group.end_date.isoformat(),
            "func_phase_end": first_group.functional_phase_end.isoformat(),
            "has_next_phase": bool(first_group.next_functional_phase),
            "next_phase_recs": bool(first_group.next_phase_recommendations)
        })
        
        # Add functional phase header with remaining days
        phase_label = f"{functional_phase.value.title()} Phase {get_phase_emoji(functional_phase)}"
        if first_group.is_power_phase_second_occurrence:
            phase_label += " (Second Occurrence)"
        phase_label += f" ({days_remaining} days remaining)"
        formatted.append(phase_label)
        formatted.append("")  # Extra spacing
        
        # Add common information for the functional phase
        formatted.extend([
            f"⏱️ Fasting: {data['recommendations'].fasting_protocol if data['recommendations'] and data['recommendations'].fasting_protocol else 'No specific protocol for this phase'}",
            "",
            "🥗 Key Foods:",
            *[f"  - {food}" for food in (data['recommendations'].foods if data['recommendations'] else [])],
            "",
            "🍽️ Suggested Meals:"
        ])

        if data['recommendations'] and data['recommendations'].meal_plan_preview:
            formatted.extend([f"  {meal}" for meal in data['recommendations'].meal_plan_preview])
        else:
            formatted.append("  No specific meals suggested for this phase")
        formatted.append("")  # Extra spacing

        # Add each traditional phase on its own line, with dates and activities
        for group in data['groups']:
            formatted.append(f"({group.traditional_phase.value.title()}): {group.start_date.strftime('%b %d')} - {group.end_date.strftime('%b %d')}")
            # Get traditional phase activities from TRADITIONAL_PHASE_RECOMMENDATIONS
            traditional_activities = TRADITIONAL_PHASE_RECOMMENDATIONS[group.traditional_phase][:3]  # Get top 3 activities
            formatted.append(f"🏃‍♀️ Activities: {', '.join(traditional_activities)}")
            formatted.append("")  # Add spacing between groups
            
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
        
        # Use cycle day to determine if this is the second Power phase
        is_second_power = first_group.is_power_phase_second_occurrence
        if events:
            cycle_day = calculate_cycle_day(events)
            is_second_power = (
                functional_phase == FunctionalPhaseType.POWER and
                any(start <= cycle_day <= end 
                    for start, end, p in FUNCTIONAL_PHASE_MAPPING 
                    if start >= 16 and p == FunctionalPhaseType.POWER)
            )

        if is_second_power:
            # Override next phase to Nurture
            transitioning_group.next_functional_phase = FunctionalPhaseType.NURTURE
            next_details = get_phase_details(transitioning_group.traditional_phase, 1)
            transitioning_group.next_phase_recommendations = create_phase_recommendations(
                next_details,
                FunctionalPhaseType.NURTURE,
                plan.phase_groups,
                user_id
            )

        # Show next phase if we're within 3 days of transition or have passed the end
        if (transitioning_group.next_functional_phase and transitioning_group.next_phase_recommendations and 
            (days_until_transition <= 3 or days_until_transition < 0)):
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
                f"Next Phase: {transitioning_group.next_functional_phase.value.title()} {get_phase_emoji(transitioning_group.next_functional_phase)} (starting {next_phase_start})"
            ])
            
            # Add next phase recommendations if available
            if transitioning_group.next_phase_recommendations:
                if transitioning_group.next_phase_recommendations.fasting_protocol:
                    formatted.append(f"⏱️ Fasting: {transitioning_group.next_phase_recommendations.fasting_protocol}")
                formatted.extend([
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
