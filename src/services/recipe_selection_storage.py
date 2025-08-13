"""
Storage service for managing recipe selections during the multi-step selection process.
"""
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum

class SelectionMode(Enum):
    """Recipe selection mode."""
    SINGLE = "single"
    MULTI_PHASE = "multi_phase"

@dataclass
class PhaseRecipeSelection:
    """Phase-specific recipe selections."""
    recipe_id: Optional[str] = None
    phase: Optional[str] = None

@dataclass
class RecipeSelection:
    """Enhanced recipe selection supporting both single and multi-phase selections."""
    breakfast: List[PhaseRecipeSelection]
    lunch: List[PhaseRecipeSelection]
    dinner: List[PhaseRecipeSelection]
    snack: List[PhaseRecipeSelection]
    mode: SelectionMode

    def __init__(self, mode: SelectionMode = SelectionMode.SINGLE):
        """Initialize with empty selections."""
        self.breakfast = []
        self.lunch = []
        self.dinner = []
        self.snack = []
        self.mode = mode

    def is_complete(self) -> bool:
        """
        Check if all required meal types have been selected.
        
        For single mode, each meal type needs exactly one selection (or skip).
        For multi-phase mode, each meal type needs at least one selection (or skip).
        """
        meal_types = [self.breakfast, self.lunch, self.dinner, self.snack]
        
        if self.mode == SelectionMode.SINGLE:
            return all(len(meal) == 1 for meal in meal_types)
        else:
            return all(len(meal) >= 1 for meal in meal_types)

    def to_dict(self) -> Dict[str, List[Dict[str, str]]]:
        """Convert selections to dictionary format."""
        return {
            'breakfast': [
                {'recipe_id': s.recipe_id, 'phase': s.phase}
                for s in self.breakfast if s.recipe_id
            ],
            'lunch': [
                {'recipe_id': s.recipe_id, 'phase': s.phase}
                for s in self.lunch if s.recipe_id
            ],
            'dinner': [
                {'recipe_id': s.recipe_id, 'phase': s.phase}
                for s in self.dinner if s.recipe_id
            ],
            'snack': [
                {'recipe_id': s.recipe_id, 'phase': s.phase}
                for s in self.snack if s.recipe_id
            ],
            'mode': self.mode.value
        }
        
    def get_selected_recipes(self) -> List[str]:
        """Get list of all currently selected recipe IDs (excluding skips)."""
        all_selections = (
            self.breakfast +
            self.lunch +
            self.dinner +
            self.snack
        )
        return [
            s.recipe_id for s in all_selections
            if s.recipe_id and s.recipe_id != 'skip'
        ]

    def add_selection(self, meal_type: str, recipe_id: str, phase: Optional[str] = None) -> None:
        """
        Add a recipe selection for a meal type.
        
        Args:
            meal_type: Type of meal (breakfast, lunch, dinner, snack)
            recipe_id: ID of selected recipe
            phase: Phase this recipe is for (required for multi-phase mode)
        """
        if self.mode == SelectionMode.MULTI_PHASE and not phase:
            raise ValueError("Phase is required for multi-phase selections")
            
        selection = PhaseRecipeSelection(recipe_id=recipe_id, phase=phase)
        meal_selections = getattr(self, meal_type)
        
        if self.mode == SelectionMode.SINGLE:
            # Replace any existing selection
            setattr(self, meal_type, [selection])
        else:
            # Add to existing selections
            meal_selections.append(selection)

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
    def update_selection(
        cls, 
        user_id: str, 
        meal_type: str, 
        recipe_id: str,
        phase: Optional[str] = None
    ) -> None:
        """
        Update recipe selection for a meal type.
        
        Args:
            user_id: User making the selection
            meal_type: Type of meal (breakfast, lunch, dinner, snack)
            recipe_id: ID of selected recipe
            phase: Optional phase for multi-phase selections
        """
        selection = cls.get_selection(user_id)
        selection.add_selection(meal_type, recipe_id, phase)
    
    @classmethod
    def set_multi_phase_mode(cls, user_id: str) -> None:
        """Enable multi-phase selection mode for user."""
        if user_id in cls._selections:
            cls._selections[user_id].mode = SelectionMode.MULTI_PHASE
        else:
            cls._selections[user_id] = RecipeSelection(mode=SelectionMode.MULTI_PHASE)
    
    @classmethod
    def clear_selection(cls, user_id: str) -> None:
        """Clear user's selections."""
        if user_id in cls._selections:
            del cls._selections[user_id]
