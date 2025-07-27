"""
Storage service for managing recipe selections during the multi-step selection process.
"""
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class RecipeSelection:
    breakfast: Optional[str] = None
    lunch: Optional[str] = None
    dinner: Optional[str] = None
    snack: Optional[str] = None

    def is_complete(self) -> bool:
        """Check if all meal types have been selected."""
        return all([
            self.breakfast,
            self.lunch,
            self.dinner,
            self.snack
        ])

    def to_dict(self) -> Dict[str, str]:
        """Convert selections to dictionary."""
        return {
            'breakfast': self.breakfast,
            'lunch': self.lunch,
            'dinner': self.dinner,
            'snack': self.snack
        }

class RecipeSelectionStorage:
    """In-memory storage for user recipe selections."""
    
    _selections: Dict[str, RecipeSelection] = {}
    
    @classmethod
    def get_selection(cls, user_id: str) -> RecipeSelection:
        """Get or create selection for user."""
        if user_id not in cls._selections:
            cls._selections[user_id] = RecipeSelection()
        return cls._selections[user_id]
    
    @classmethod
    def update_selection(cls, user_id: str, meal_type: str, recipe_id: str) -> None:
        """Update recipe selection for a meal type."""
        selection = cls.get_selection(user_id)
        setattr(selection, meal_type, recipe_id)
    
    @classmethod
    def clear_selection(cls, user_id: str) -> None:
        """Clear user's selections."""
        if user_id in cls._selections:
            del cls._selections[user_id]
