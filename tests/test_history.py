"""Test module for history service."""
from datetime import date, timedelta

import pytest
from src.models.event import CycleEvent
from src.services.history import get_period_history
from src.handlers.history import calculate_period_history

@pytest.fixture
def sample_events():
    """Create sample events for testing."""
    today = date.today()
    return [
        CycleEvent(
            user_id="test_user",
            date=today - timedelta(days=5),
            state="menstruation"
        ),
        CycleEvent(
            user_id="test_user",
            date=today - timedelta(days=4),
            state="menstruation"
        ),
        CycleEvent(
            user_id="test_user",
            date=today - timedelta(days=3),
            state="menstruation"
        ),
        # Previous period
        CycleEvent(
            user_id="test_user",
            date=today - timedelta(days=33),
            state="menstruation"
        ),
        CycleEvent(
            user_id="test_user",
            date=today - timedelta(days=32),
            state="menstruation"
        ),
        # Old period (beyond 6 months)
        CycleEvent(
            user_id="test_user",
            date=today - timedelta(days=200),
            state="menstruation"
        ),
        # Non-menstruation events should be ignored
        CycleEvent(
            user_id="test_user",
            date=today - timedelta(days=1),
            state="follicular"
        ),
    ]

def test_get_period_history_empty():
    """Test getting history with no events."""
    assert get_period_history([]) == []

def test_get_period_history(sample_events):
    """Test getting period history with sample events."""
    history = get_period_history(sample_events)
    
    assert len(history) == 2  # Should find 2 periods within 6 months
    
    # Most recent period - 3 days: today-5, today-4, today-3
    assert history[0]["duration"] == 3  # Three separate dates
    assert (history[0]["end_date"] - history[0]["start_date"]).days == 2  # Span of 2 days
    
    # Previous period - 2 days: today-33, today-32
    assert history[1]["duration"] == 2  # Two separate dates
    assert (history[1]["end_date"] - history[1]["start_date"]).days == 1  # Span of 1 day

def test_get_period_history_custom_months(sample_events):
    """Test getting history with custom month range."""
    # Look back only 1 month
    history = get_period_history(sample_events, months=1)
    assert len(history) == 1  # Should only find most recent period
    
    # Look back 12 months
    history = get_period_history(sample_events, months=12)
    assert len(history) == 3  # Should find all periods

def test_calculate_period_history_empty():
    """Test calculating history with no events."""
    history = calculate_period_history([])
    assert history == {
        "periods": [],
        "total_count": 0,
        "average_duration": None
    }

def test_calculate_period_history(sample_events):
    """Test calculating period history with events."""
    history = calculate_period_history(sample_events)
    
    assert len(history["periods"]) == 2
    assert history["total_count"] == 2
    assert history["average_duration"] == 2.5  # (3 + 2) / 2

def test_calculate_period_history_single_period(sample_events):
    """Test calculating history with only one period."""
    # Only look at last month so we get one period
    history = calculate_period_history(sample_events, months=1)
    
    assert len(history["periods"]) == 1
    assert history["total_count"] == 1
    assert history["average_duration"] == 3.0
