"""
User model definition for the Lorax Tracker system.
"""
from typing import Optional
from pydantic import BaseModel, Field


class User(BaseModel):
    """
    Represents a user in the system, either principal or partner.
    """
    user_id: str
    chat_id_private: str
    chat_id_group: Optional[str] = None
    partner_id: Optional[str] = None
    user_type: str = Field(..., pattern="^(principal|pareja)$")
    name: Optional[str] = None
    registration_date: str
