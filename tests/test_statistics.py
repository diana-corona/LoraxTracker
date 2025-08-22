"""Tests for statistics calculation service."""
from datetime import date, datetime
import pytest
from src.models.event import CycleEvent
from src.models.phase import TraditionalPhaseType
from src.services.statistics import calculate_cycle_statistics, find_period_ranges
from src.services.exceptions import InvalidPeriodDurationError

class MockDateTime:
    """Mock datetime for testing with fixed date."""
    def __init__(self, year, month, day):
        self._now = datetime(year, month, day)
    
    def now(self):
        """Return fixed datetime."""
        return self._now

def test_calculate_cycle_statistics_with_normal_periods():
    """Test statistics calculation with typical period data."""
    events = [
        # First period: Jan 1-5 (5 days)
        CycleEvent(user_id="test_user", date=date(2025, 1, 1), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 1, 2), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 1, 3), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 1, 4), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 1, 5), state=TraditionalPhaseType.MENSTRUATION.value),
        
        # Second period: Jan 31-Feb 4 (5 days, 25 days after first period)
        CycleEvent(user_id="test_user", date=date(2025, 1, 31), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 2, 1), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 2, 2), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 2, 3), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 2, 4), state=TraditionalPhaseType.MENSTRUATION.value),
    ]
    
    stats = calculate_cycle_statistics(events)
    
    assert stats["average_period_duration"] == 5.0
    assert stats["average_days_between"] == 25.0
    assert stats["total_cycles"] == 2
    assert len(stats["last_two_periods"]) == 2
    
    # Verify first period
    first_period = stats["last_two_periods"][1]
    assert first_period["start_date"] == date(2025, 1, 1)
    assert first_period["end_date"] == date(2025, 1, 5)
    assert first_period["duration"] == 5
    
    # Verify second period
    second_period = stats["last_two_periods"][0]
    assert second_period["start_date"] == date(2025, 1, 31)
    assert second_period["end_date"] == date(2025, 2, 4)
    assert second_period["duration"] == 5

def test_calculate_cycle_statistics_empty_events():
    """Test statistics calculation with no events."""
    stats = calculate_cycle_statistics([])
    
    assert stats["average_period_duration"] == 0
    assert stats["average_days_between"] == 0
    assert stats["total_cycles"] == 0
    assert stats["last_two_periods"] == []

def test_find_period_ranges_with_single_period():
    """Test period range detection with a single period."""
    events = [
        CycleEvent(user_id="test_user", date=date(2025, 1, 1), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 1, 2), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 1, 3), state=TraditionalPhaseType.MENSTRUATION.value),
    ]
    
    ranges = find_period_ranges(events)
    
    assert len(ranges) == 1
    assert ranges[0] == (date(2025, 1, 1), date(2025, 1, 3))

def test_find_period_ranges_with_small_gap():
    """Test period range detection with a small gap (should be considered same period)."""
    events = [
        CycleEvent(user_id="test_user", date=date(2025, 1, 1), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 1, 2), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 1, 4), state=TraditionalPhaseType.MENSTRUATION.value),  # Gap on Jan 3
    ]
    
    ranges = find_period_ranges(events)
    
    # Should detect as single period since gap is only 1 day
    assert len(ranges) == 1
    assert ranges[0] == (date(2025, 1, 1), date(2025, 1, 4))

def test_find_period_ranges_with_large_gap():
    """Test period range detection with a large gap (should be considered separate periods)."""
    events = [
        CycleEvent(user_id="test_user", date=date(2025, 1, 1), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 1, 2), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 1, 5), state=TraditionalPhaseType.MENSTRUATION.value),  # Gap of 2 days
    ]
    
    ranges = find_period_ranges(events)
    
    # Should detect as two periods since gap is more than 1 day
    assert len(ranges) == 2
    assert ranges[0] == (date(2025, 1, 1), date(2025, 1, 2))
    assert ranges[1] == (date(2025, 1, 5), date(2025, 1, 5))

def test_calculate_cycle_statistics_with_current_period(monkeypatch):
    """Test statistics calculation with a current/incomplete period."""
    # Mock current date to 2025-08-22 to match error log scenario
    monkeypatch.setattr("src.services.statistics.datetime", MockDateTime(2025, 8, 22))
    
    events = [
        # First complete period: 5 days
        CycleEvent(user_id="test_user", date=date(2025, 7, 1), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 7, 2), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 7, 3), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 7, 4), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 7, 5), state=TraditionalPhaseType.MENSTRUATION.value),
        
        # Current incomplete period (1 day so far)
        CycleEvent(user_id="test_user", date=date(2025, 8, 21), state=TraditionalPhaseType.MENSTRUATION.value),
    ]
    
    stats = calculate_cycle_statistics(events)
    
    # Should only count the complete period in averages
    assert stats["total_cycles"] == 1
    assert stats["average_period_duration"] == 5.0
    
    # Current period should be detected
    assert stats["current_period"] is not None
    assert stats["current_period"]["start_date"] == date(2025, 8, 21)
    assert stats["current_period"]["last_logged_date"] == date(2025, 8, 21)
    assert stats["current_period"]["days_logged"] == 1

def test_calculate_cycle_statistics_with_invalid_complete_period():
    """Test that invalid period durations raise appropriate error for complete periods."""
    events = [        
        # 12-day period (too long)
        CycleEvent(user_id="test_user", date=date(2025, 2, 1), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 2, 12), state=TraditionalPhaseType.MENSTRUATION.value),
    ]
    
    with pytest.raises(InvalidPeriodDurationError) as exc:
        calculate_cycle_statistics(events)
    assert "outside normal range" in str(exc.value)

def test_calculate_cycle_statistics_with_valid_ranges():
    """Test statistics calculation with periods at min and max valid durations."""
    events = [
        # 2-day period (minimum valid duration)
        CycleEvent(user_id="test_user", date=date(2025, 1, 1), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 1, 2), state=TraditionalPhaseType.MENSTRUATION.value),
        
        # Non-menstruation gap...
        
        # 10-day period (maximum valid duration)
        CycleEvent(user_id="test_user", date=date(2025, 2, 1), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 2, 2), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 2, 3), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 2, 4), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 2, 5), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 2, 6), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 2, 7), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 2, 8), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 2, 9), state=TraditionalPhaseType.MENSTRUATION.value),
        CycleEvent(user_id="test_user", date=date(2025, 2, 10), state=TraditionalPhaseType.MENSTRUATION.value),
    ]
    
    stats = calculate_cycle_statistics(events)
    assert stats["total_cycles"] == 2
    assert stats["average_period_duration"] == 6.0  # Average of 2 and 10
