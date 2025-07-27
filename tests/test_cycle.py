"""
Tests for cycle and phase functionality.
"""
import pytest
from datetime import date, timedelta

from src.models.event import CycleEvent
from src.models.phase import TraditionalPhaseType, FunctionalPhaseType
from src.services.phase import get_current_phase, predict_next_phase, determine_functional_phase
from src.services.cycle import calculate_next_cycle

def test_phase_detection():
    """Test phase detection and mapping to functional phases."""
    events = [
        CycleEvent(
            user_id="123",
            date=date(2024, 1, 1),
            state=TraditionalPhaseType.MENSTRUATION.value
        )
    ]
    
    # Test Power Phase (during menstruation)
    phase = get_current_phase(events, date(2024, 1, 3))
    assert phase.traditional_phase == TraditionalPhaseType.MENSTRUATION
    assert phase.functional_phase == FunctionalPhaseType.POWER
    assert phase.duration == 5
    
    # Test Power Phase (early follicular)
    phase = get_current_phase(events, date(2024, 1, 8))
    assert phase.traditional_phase == TraditionalPhaseType.FOLLICULAR
    assert phase.functional_phase == FunctionalPhaseType.POWER
    
    # Test Manifestation Phase
    phase = get_current_phase(events, date(2024, 1, 15))  # Changed to day 15 (ovulation phase)
    assert phase.traditional_phase == TraditionalPhaseType.OVULATION
    assert phase.functional_phase == FunctionalPhaseType.MANIFESTATION
    
    # Test Power Phase (early luteal)
    phase = get_current_phase(events, date(2024, 1, 18))
    assert phase.traditional_phase == TraditionalPhaseType.LUTEAL
    assert phase.functional_phase == FunctionalPhaseType.POWER
    
    # Test Nurture Phase (late luteal)
    phase = get_current_phase(events, date(2024, 1, 25))
    assert phase.traditional_phase == TraditionalPhaseType.LUTEAL
    assert phase.functional_phase == FunctionalPhaseType.NURTURE

def test_phase_recommendations():
    """Test recommendations based on functional phases."""
    events = [
        CycleEvent(
            user_id="123",
            date=date(2024, 1, 1),
            state=TraditionalPhaseType.MENSTRUATION.value
        )
    ]
    
    # Test Power Phase recommendations
    phase = get_current_phase(events, date(2024, 1, 3))
    assert phase.dietary_style == "Ketobiotic"
    assert "13 to 72 hours" in phase.fasting_protocol
    assert any("Healthy fats" in rec for rec in phase.food_recommendations)
    assert any("Clean proteins" in rec for rec in phase.food_recommendations)
    
    # Test Manifestation Phase recommendations
    phase = get_current_phase(events, date(2024, 1, 13))
    assert "Transition" in phase.dietary_style
    assert "No more than 15 hours" in phase.fasting_protocol
    assert any("Root vegetables" in rec for rec in phase.food_recommendations)
    
    # Test Nurture Phase recommendations
    phase = get_current_phase(events, date(2024, 1, 25))
    assert "hormone feasting" in phase.dietary_style.lower()
    assert "Avoid fasting" in phase.fasting_protocol
    assert any("Root vegetables" in rec for rec in phase.food_recommendations)
    assert phase.supplement_recommendations is not None
    assert any("Magnesium" in supp for supp in phase.supplement_recommendations)

def test_phase_mapping():
    """Test mapping between traditional and functional phases."""
    # Day 1-10: Power Phase
    assert determine_functional_phase(1) == FunctionalPhaseType.POWER
    assert determine_functional_phase(8) == FunctionalPhaseType.POWER
    
    # Day 11-15: Manifestation Phase
    assert determine_functional_phase(14) == FunctionalPhaseType.MANIFESTATION
    
    # Day 16-19: Power Phase (early luteal)
    assert determine_functional_phase(17) == FunctionalPhaseType.POWER
    
    # Day 20+: Nurture Phase
    assert determine_functional_phase(22) == FunctionalPhaseType.NURTURE

def test_phase_transition():
    """Test phase transition predictions."""
    events = [
        CycleEvent(
            user_id="123",
            date=date(2024, 1, 1),
            state=TraditionalPhaseType.MENSTRUATION.value
        )
    ]
    
    current = get_current_phase(events, date(2024, 1, 3))
    next_phase = predict_next_phase(current)
    
    assert next_phase.traditional_phase == TraditionalPhaseType.FOLLICULAR
    assert next_phase.start_date == current.end_date + timedelta(days=1)
    assert next_phase.food_recommendations
    assert next_phase.activity_recommendations

def test_invalid_phase_detection():
    """Test error handling for invalid phase detection."""
    events = []
    
    with pytest.raises(ValueError, match="No menstruation events found"):
        get_current_phase(events, date(2024, 1, 1))

def test_report_generation():
    """Test phase report generation."""
    events = [
        CycleEvent(
            user_id="123",
            date=date(2024, 1, 1),
            state=TraditionalPhaseType.MENSTRUATION.value,
            notes="Started period"
        )
    ]
    
    phase = get_current_phase(events, date(2024, 1, 3))
    from src.services.phase import generate_phase_report
    report = generate_phase_report(phase, events)
    
    assert "Traditional Phase: Menstruation" in report
    assert "Functional Phase: Power" in report
    assert "🍽️ Dietary Style" in report
    assert phase.dietary_style in report
    assert "⏱️ Fasting Protocol" in report
    assert phase.fasting_protocol in report
    assert "Started period" in report

def test_prediction_with_recent_longer_cycles():
    """Test prediction when recent cycles are longer than historical ones."""
    # Test case matching the reported scenario
    events = [
        CycleEvent(
            user_id="test_user",
            date=date(2025, 6, 16),
            state="menstruation",
            pain_level=3
        ),
        CycleEvent(
            user_id="test_user",
            date=date(2025, 7, 22),
            state="menstruation",
            pain_level=3
        )
    ]
    
    next_date, duration, warning = calculate_next_cycle(events)
    
    # Should predict 36 days after July 22 (around Aug 23)
    assert next_date == date(2025, 8, 27)
    assert duration == 36  # The interval between June 16 and July 22
    assert warning == "Limited data for prediction, using most recent cycle length"

def test_prediction_with_mixed_cycle_lengths():
    """Test prediction with historical shorter cycles but recent longer cycles."""
    events = [
        CycleEvent(
            user_id="test_user",
            date=date(2025, 4, 1),
            state="menstruation",
            pain_level=3
        ),
        CycleEvent(
            user_id="test_user",
            date=date(2025, 4, 28),
            state="menstruation",
            pain_level=3
        ),
        CycleEvent(
            user_id="test_user",
            date=date(2025, 6, 16),
            state="menstruation",
            pain_level=3
        ),
        CycleEvent(
            user_id="test_user",
            date=date(2025, 7, 22),
            state="menstruation",
            pain_level=3
        )
    ]
    
    next_date, duration, warning = calculate_next_cycle(events)
    
    # Should weight recent cycles more heavily
    # Earlier cycles: 27 days (Apr 1 -> Apr 28)
    # Middle cycle: 49 days (Apr 28 -> Jun 16)
    # Latest cycle: 36 days (Jun 16 -> Jul 22)
    # With exponential weights (4,2,1), should predict closer to recent cycles
    assert next_date > date(2025, 8, 15)  # Should be closer to Aug 23 than Aug 1
    assert warning == "Irregular cycle detected"  # Should detect irregularity due to varying lengths
