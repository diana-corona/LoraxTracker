"""
Model definitions for weekly cycle planning.
"""
from typing import List, Optional, Dict, Any
from datetime import date, timedelta
from pydantic import BaseModel, computed_field

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
    Represents a group of consecutive days in the same phase, with enhanced
    functional phase information and transition details.
    """
    start_date: date
    end_date: date
    traditional_phase: TraditionalPhaseType
    functional_phase: FunctionalPhaseType
    functional_phase_duration: int  # Days remaining in current functional phase
    functional_phase_start: date
    functional_phase_end: date
    is_power_phase_second_occurrence: Optional[bool] = False  # For Power phase tracking
    next_functional_phase: Optional[FunctionalPhaseType] = None  # For transition warnings
    next_phase_recommendations: Optional[PhaseRecommendations] = None  # For transition info
    recommendations: PhaseRecommendations
    
    @computed_field
    def has_phase_transition(self) -> bool:
        """Check if this group ends with a functional phase transition."""
        return self.next_functional_phase is not None and self.next_functional_phase != self.functional_phase
    
    @computed_field
    def transition_message(self) -> Optional[str]:
        """Generate phase transition message if applicable."""
        if not self.has_phase_transition:
            return None
            
        # Base transition message
        message = [
            f"Phase Transition: {self.functional_phase.value.title()} phase ends "
            f"{self.end_date.strftime('%a %d')}, {self.next_functional_phase.value.title()} "
            f"begins {(self.end_date + timedelta(days=1)).strftime('%a %d')}"
        ]
        
        # Add fasting protocol changes if available
        if self.next_phase_recommendations:
            message.append(
                f"⏱️ Fasting changes: {self.recommendations.fasting_protocol} → "
                f"{self.next_phase_recommendations.fasting_protocol}"
            )
        
        return "\n".join(message)

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
