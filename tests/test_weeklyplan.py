"""Tests for weekly plan generation service."""
from datetime import date, timedelta
import pytest

from src.models.event import CycleEvent
from src.models.phase import TraditionalPhaseType, FunctionalPhaseType
from src.models.recipe import Recipe, MealRecommendation, RecipeRecommendations
from src.services.weekly_plan import (
    generate_weekly_plan, 
    format_weekly_plan, 
    get_daily_phases,
    create_meal_plan_preview
)

def create_test_recipe(title: str, prep_time: int = 30, url: str = None) -> Recipe:
    """Helper function to create a test recipe."""
    return Recipe(
        title=title,
        phase="power",
        prep_time=prep_time,
        tags=["breakfast"],
        ingredients=["ingredient1", "ingredient2"],
        instructions=["step1", "step2"],
        notes=None,
        url=url,
        file_path="test/path.md"
    )

def test_get_daily_phases_with_recent_events():
    """Test daily phase calculation with recent cycle events."""
    today = date.today()
    events = [
        CycleEvent(
            user_id="test_user",
            date=today - timedelta(days=2),
            state=TraditionalPhaseType.MENSTRUATION.value
        ),
        CycleEvent(
            user_id="test_user",
            date=today - timedelta(days=1),
            state=TraditionalPhaseType.MENSTRUATION.value
        )
    ]
    
    phases = get_daily_phases(events, today)
    assert len(phases) == 7  # Week of phases
    assert phases[today].traditional_phase == TraditionalPhaseType.MENSTRUATION

def test_generate_weekly_plan_normal_cycle():
    """Test weekly plan generation with normal cycle data."""
    today = date.today()
    events = [
        CycleEvent(
            user_id="test_user",
            date=today - timedelta(days=25),
            state=TraditionalPhaseType.MENSTRUATION.value
        ),
        CycleEvent(
            user_id="test_user",
            date=today - timedelta(days=24),
            state=TraditionalPhaseType.MENSTRUATION.value
        ),
        CycleEvent(
            user_id="test_user",
            date=today - timedelta(days=23),
            state=TraditionalPhaseType.MENSTRUATION.value
        )
    ]
    
    plan = generate_weekly_plan(events)
    
    assert plan.start_date == today + timedelta(days=1)  # Starts tomorrow
    assert plan.end_date == today + timedelta(days=7)
    assert len(plan.phase_groups) > 0
    
    # Verify first phase group has recommendations
    first_group = plan.phase_groups[0]
    assert first_group.recommendations.foods
    assert first_group.recommendations.activities
    assert first_group.recommendations.fasting_protocol

def test_generate_weekly_plan_no_events():
    """Test weekly plan generation with no events."""
    with pytest.raises(ValueError, match="No events provided"):
        generate_weekly_plan([])

def test_meal_plan_preview_with_urls():
    """Test creation of meal plan preview with recipe URLs."""
    # Test single recipe
    recipe_with_url = create_test_recipe("Test Recipe", url="https://example.com/recipe")
    meal = MealRecommendation(
        meal_type="breakfast",
        recipes=[recipe_with_url],
        prep_time_total=30
    )
    preview = create_meal_plan_preview([meal])
    
    assert len(preview) == 1
    assert "Test Recipe (30 min) - https://example.com/recipe" in preview[0]
    
    # Test multiple recipes
    recipe1 = create_test_recipe("Recipe 1", url="https://example.com/recipe1")
    recipe2 = create_test_recipe("Recipe 2", url="https://example.com/recipe2")
    meal_multiple = MealRecommendation(
        meal_type="breakfast",
        recipes=[recipe1, recipe2],
        prep_time_total=60
    )
    preview = create_meal_plan_preview([meal_multiple])
    
    assert len(preview) == 1
    assert "Recipe 1 (30 min) - https://example.com/recipe1" in preview[0]
    assert "Recipe 2 (30 min) - https://example.com/recipe2" in preview[0]
    
    # Test recipe without URL
    recipe_no_url = create_test_recipe("No URL Recipe", url=None)
    meal_no_url = MealRecommendation(
        meal_type="breakfast",
        recipes=[recipe_no_url],
        prep_time_total=30
    )
    preview = create_meal_plan_preview([meal_no_url])
    
    assert len(preview) == 1
    assert "No URL Recipe (30 min)" in preview[0]
    assert "http" not in preview[0]

def test_format_weekly_plan():
    """Test weekly plan formatting with phase grouping."""
    today = date.today()
    events = [
        CycleEvent(
            user_id="test_user",
            date=today - timedelta(days=3),
            state=TraditionalPhaseType.MENSTRUATION.value
        ),
        CycleEvent(
            user_id="test_user",
            date=today - timedelta(days=2),
            state=TraditionalPhaseType.MENSTRUATION.value
        ),
        CycleEvent(
            user_id="test_user",
            date=today + timedelta(days=2),  # Future event to ensure phase transition
            state=TraditionalPhaseType.FOLLICULAR.value
        )
    ]
    
    plan = generate_weekly_plan(events)
    formatted = format_weekly_plan(plan)
    
    # Basic format checks
    assert isinstance(formatted, list)
    assert len(formatted) > 0
    assert formatted[0].startswith("📅")  # Header
    assert any("Phase Schedule" in line for line in formatted)
    
    # Find Power Phase section (both Menstruation and Follicular map to Power)
    power_phase_index = next(i for i, line in enumerate(formatted) if "Power Phase ⚡" in line)
    
    # Common information should appear once per functional phase
    common_info = formatted[power_phase_index:power_phase_index+10]  # Approximate range for common info
    assert sum("⏱️ Fasting:" in line for line in common_info) == 1  # Fasting info appears once
    assert sum("🥗 Key Foods:" in line for line in common_info) == 1  # Foods appear once
    assert sum("🍽️ Suggested Meals:" in line for line in common_info) == 1  # Meals appear once
    
    # Find the lines for each phase's activities
    # First find the phase headers
    menstruation_line = next(line for line in formatted if "(Menstruation)" in line)
    follicular_line = next(line for line in formatted if "(Follicular)" in line)
    
    # Get the activities lines that follow
    menstruation_idx = formatted.index(menstruation_line)
    follicular_idx = formatted.index(follicular_line)
    menstruation_activities = formatted[menstruation_idx + 1]  # Activities line follows phase line
    follicular_activities = formatted[follicular_idx + 1]
    
    # Verify different activities for each phase
    assert "Activities:" in menstruation_activities
    assert "Rest and self-care" in menstruation_activities
    assert "Light exercise" in menstruation_activities
    
    assert "Activities:" in follicular_activities
    assert "High-intensity workouts" in follicular_activities
    assert "Start new projects" in follicular_activities

def test_generate_weekly_plan_phase_transitions():
    """Test weekly plan handles phase transitions correctly."""
    today = date.today()
    events = [
        CycleEvent(
            user_id="test_user",
            date=today - timedelta(days=14),  # Two weeks ago, well into follicular phase
            state=TraditionalPhaseType.MENSTRUATION.value
        ),
        CycleEvent(
            user_id="test_user",
            date=today - timedelta(days=13),
            state=TraditionalPhaseType.MENSTRUATION.value
        ),
        CycleEvent(
            user_id="test_user",
            date=today - timedelta(days=7),  # A week ago, should be in ovulation phase
            state=TraditionalPhaseType.FOLLICULAR.value
        )
    ]
    
    plan = generate_weekly_plan(events)
    
    # Verify phase transitions in groups
    phases = set(group.traditional_phase for group in plan.phase_groups)
    assert len(phases) >= 2  # Should have at least 2 different phases
    assert TraditionalPhaseType.FOLLICULAR in phases  # Should include follicular phase
