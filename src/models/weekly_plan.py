"""
Model definitions for weekly cycle planning.
"""
from typing import List, Optional
from datetime import date
from pydantic import BaseModel

from src.models.phase import TraditionalPhaseType, FunctionalPhaseType

class PhaseRecommendations(BaseModel):
    """Recommendations for a specific phase."""
    fasting_protocol: str
    foods: List[str]
    activities: List[str]
    supplements: Optional[List[str]] = None

class PhaseGroup(BaseModel):
    """
    Represents a group of consecutive days in the same phase.
    """
    start_date: date
    end_date: date
    traditional_phase: TraditionalPhaseType
    functional_phase: FunctionalPhaseType
    recommendations: PhaseRecommendations

class WeeklyPlan(BaseModel):
    """
    Represents a weekly cycle plan with phase predictions and recommendations.
    """
    start_date: date
    end_date: date
    next_cycle_date: Optional[date]
    avg_cycle_duration: Optional[int]
    warning: Optional[str]
    phase_groups: List[PhaseGroup]
