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
    MENSTRUATION = "menstruacion"
    FOLLICULAR = "folicular"
    OVULATION = "ovulacion"
    LUTEAL = "lutea"

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
    duration: int
    typical_symptoms: list[str]
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
