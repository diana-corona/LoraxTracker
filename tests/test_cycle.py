"""
Tests for cycle and phase functionality.
"""
import pytest
from datetime import date, timedelta

from src.models.event import CycleEvent
from src.models.phase import TraditionalPhaseType, FunctionalPhaseType
from src.services.phase import get_current_phase, predict_next_phase, map_to_functional_phase

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
    phase = get_current_phase(events, date(2024, 1, 13))
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
    assert phase.dietary_style == "Ketobiótico"
    assert "13 a 72 horas" in phase.fasting_protocol
    assert any("Grasas saludables" in rec for rec in phase.food_recommendations)
    assert any("Proteínas limpias" in rec for rec in phase.food_recommendations)
    
    # Test Manifestation Phase recommendations
    phase = get_current_phase(events, date(2024, 1, 13))
    assert "Transición" in phase.dietary_style
    assert "No más de 15 horas" in phase.fasting_protocol
    assert any("Vegetales de raíz" in rec for rec in phase.food_recommendations)
    
    # Test Nurture Phase recommendations
    phase = get_current_phase(events, date(2024, 1, 25))
    assert "Hormone Feasting" in phase.dietary_style
    assert "Evitar el ayuno" in phase.fasting_protocol
    assert any("Tubérculos" in rec for rec in phase.food_recommendations)
    assert phase.supplement_recommendations is not None
    assert any("Magnesio" in supp for supp in phase.supplement_recommendations)

def test_phase_mapping():
    """Test mapping between traditional and functional phases."""
    # Day 1-10: Power Phase
    assert map_to_functional_phase(TraditionalPhaseType.MENSTRUATION, 1) == FunctionalPhaseType.POWER
    assert map_to_functional_phase(TraditionalPhaseType.FOLLICULAR, 8) == FunctionalPhaseType.POWER
    
    # Day 11-15: Manifestation Phase
    assert map_to_functional_phase(TraditionalPhaseType.OVULATION, 14) == FunctionalPhaseType.MANIFESTATION
    
    # Day 16-19: Power Phase (early luteal)
    assert map_to_functional_phase(TraditionalPhaseType.LUTEAL, 17) == FunctionalPhaseType.POWER
    
    # Day 20+: Nurture Phase
    assert map_to_functional_phase(TraditionalPhaseType.LUTEAL, 22) == FunctionalPhaseType.NURTURE

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
    
    assert "Fase Tradicional: Menstruacion" in report
    assert "Fase Funcional: Power" in report
    assert "🍽️ Estilo Alimenticio" in report
    assert phase.dietary_style in report
    assert "⏱️ Protocolo de Ayuno" in report
    assert phase.fasting_protocol in report
    assert "Started period" in report
