"""
Model definitions for weekly cycle planning.
"""
from typing import List, Optional, Dict, Any
from datetime import date
from pydantic import BaseModel

from src.models.phase import TraditionalPhaseType, FunctionalPhaseType

class PhaseRecommendations(BaseModel):
    """
    Recommendations for a specific phase.
    
    Enhanced to include recipe suggestions and meal planning information
    alongside traditional recommendations for fasting, foods, and activities.
    """
    fasting_protocol: str
    foods: List[str]
    activities: List[str]
    supplements: Optional[List[str]] = None
    # Enhanced recipe fields
    recipe_suggestions: Optional[List[Dict[str, Any]]] = None
    meal_plan_preview: Optional[List[str]] = None
    shopping_preview: Optional[List[str]] = None

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
