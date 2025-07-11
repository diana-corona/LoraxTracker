"""
Event model definition for tracking cycle events and states.
"""
from datetime import date
from typing import Optional
from pydantic import BaseModel, Field

class CycleEvent(BaseModel):
    """
    Represents a cycle tracking event with date, state, and optional metrics.
    """
    user_id: str
    date: date
    state: str = Field(..., pattern="^(menstruacion|folicular|ovulacion|lutea)$")
    pain_level: Optional[int] = Field(None, ge=0, le=5)
    energy_level: Optional[int] = Field(None, ge=0, le=5)
    notes: Optional[str] = None
