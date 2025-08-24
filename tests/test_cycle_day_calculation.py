from datetime import date, timedelta

from src.models.event import CycleEvent
from src.models.phase import FunctionalPhaseType, TraditionalPhaseType
from src.services.phase import get_current_phase
from src.services.utils import calculate_cycle_day


def test_cycle_day_with_future_logged_menstruation_day():
    """
    Regresssion test:
    When the user logs all menstruation days up to the expected end date (including
    a future day relative to 'today'), the cycle day must be calculated from the
    FIRST day of the contiguous menstruation block, not the last logged day.

    Previously:
      Period logged 2025-08-21 .. 2025-08-25
      Today = 2025-08-24
      Old logic used last logged (25) -> (24 - 25) + 1 = 0 -> no mapping -> NURTURE
    Now:
      Start date = 2025-08-21
      Cycle day = (24 - 21) + 1 = 4 -> POWER phase
    """
    start = date(2025, 8, 21)
    # User logs 5 menstruation days including a future day (Aug 25) relative to target_date Aug 24
    events = [
        CycleEvent(
            user_id="u1",
            date=start + timedelta(days=offset),
            state=TraditionalPhaseType.MENSTRUATION.value
        )
        for offset in range(5)  # 21,22,23,24,25
    ]

    target_date = date(2025, 8, 24)  # Day 4 of period
    cycle_day = calculate_cycle_day(events, target_date)
    assert cycle_day == 4

    phase = get_current_phase(events, target_date)
    assert phase.traditional_phase == TraditionalPhaseType.MENSTRUATION
    assert phase.functional_phase == FunctionalPhaseType.POWER
    # Remaining days in menstruation (5-day fixed duration): days 1-5 -> on day 4 -> 2 days incl today & tomorrow
    assert phase.duration == 5
