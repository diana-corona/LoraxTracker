"""
Recommendation model for cycle-based lifestyle suggestions.
"""
from typing import Optional, List
from datetime import date
from pydantic import BaseModel, Field

class RecommendationType(BaseModel):
    """
    Defines a type of recommendation with its category and priority.
    """
    category: str = Field(..., pattern="^(ejercicio|nutricion|descanso|actividad|emocional)$")
    priority: int = Field(..., ge=1, le=5)
    description: str

class Recommendation(BaseModel):
    """
    Represents a personalized recommendation for a specific phase.
    """
    user_id: str
    phase_type: str = Field(..., pattern="^(menstruacion|folicular|ovulacion|lutea)$")
    date: date
    recommendations: List[RecommendationType]
    user_feedback: Optional[str] = None
    effectiveness_rating: Optional[int] = Field(None, ge=1, le=5)
    is_implemented: bool = False
