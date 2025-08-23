"""
Phase model definition for menstrual cycle phases.
"""
from enum import Enum
from datetime import date
from typing import Optional
from pydantic import BaseModel

class TraditionalPhaseType(str, Enum):
    """
    Traditional menstrual cycle phases.
    """
    MENSTRUATION = "menstruation"
    FOLLICULAR = "follicular"
    OVULATION = "ovulation"
    LUTEAL = "luteal"

class FunctionalPhaseType(str, Enum):
    """
    Functional phases based on Dr. Mindy Pelz's approach.
    """
    POWER = "power"           # Menstruation and early follicular
    MANIFESTATION = "manifestation"  # Ovulation
    NURTURE = "nurture"       # Luteal

class Phase(BaseModel):
    """
    Represents a specific phase in the menstrual cycle.
    """
    traditional_phase: TraditionalPhaseType
    functional_phase: FunctionalPhaseType
    start_date: date
    end_date: date
    duration: int  # Traditional phase duration
    functional_phase_duration: int  # Days remaining in current functional phase
    functional_phase_start: date
    functional_phase_end: date
    typical_symptoms: Optional[list[str]] = None
    dietary_style: str
    fasting_protocol: str
    food_recommendations: list[str]
    activity_recommendations: list[str]
    supplement_recommendations: Optional[list[str]] = None
    user_notes: Optional[str] = None

    @property
    def is_fasting_recommended(self) -> bool:
        """Check if fasting is recommended for this phase."""
        return self.functional_phase == FunctionalPhaseType.POWER
