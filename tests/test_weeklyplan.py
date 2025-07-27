"""Tests for weekly plan generation service."""
from datetime import date, timedelta
import pytest

from src.models.event import CycleEvent
from src.models.phase import TraditionalPhaseType, FunctionalPhaseType
from src.services.weekly_plan import generate_weekly_plan, format_weekly_plan, get_daily_phases

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

def test_format_weekly_plan():
    """Test weekly plan formatting."""
    today = date.today()
    events = [
        CycleEvent(
            user_id="test_user",
            date=today - timedelta(days=3),
            state=TraditionalPhaseType.MENSTRUATION.value
        )
    ]
    
    plan = generate_weekly_plan(events)
    formatted = format_weekly_plan(plan)
    
    assert isinstance(formatted, list)
    assert len(formatted) > 0
    assert formatted[0].startswith("📅")  # Header
    assert any("Phase Schedule" in line for line in formatted)

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
