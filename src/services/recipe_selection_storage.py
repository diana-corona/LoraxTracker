"""
Storage service for managing recipe selections during the multi-step selection process.
"""
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum

class SelectionMode(Enum):
    """Recipe selection mode."""
    SINGLE = "single"
    MULTI_PHASE = "multi_phase"
    MULTI_SELECT = "multi_select"  # New mode for single-screen multi-selection

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
    selected_recipes: List[str] = field(default_factory=list)  # New field for multi-select mode
    weekly_plan_text: Optional[str] = None  # Store weekly plan text
    
    def __init__(self, mode: SelectionMode = SelectionMode.SINGLE):
        """Initialize with empty selections."""
        self.breakfast = []
        self.lunch = []
        self.dinner = []
        self.snack = []
        self.mode = mode
        self.selected_recipes = []
        self.weekly_plan_text = None
        # Snapshot of the recipes shown to the user when the selection keyboard was built.
        # This preserves stability so toggling selections does not load a different set.
        # Can hold either:
        #   - single-phase: Dict[meal_type, List[recipes]]
        #   - multi-phase: Dict[phase, Dict[meal_type, List[recipes]]]
        self.recipes_snapshot: Optional[Dict] = None

    def is_complete(self) -> bool:
        """
        Check if all required meal types have been selected.
        
        For single mode, each meal type needs exactly one selection (or skip).
        For multi-phase mode, each meal type needs at least one selection (or skip).
        For multi-select mode, at least one recipe must be selected total.
        """
        if self.mode == SelectionMode.MULTI_SELECT:
            return len(self.selected_recipes) > 0
            
        meal_types = [self.breakfast, self.lunch, self.dinner, self.snack]
        
        if self.mode == SelectionMode.SINGLE:
            return all(len(meal) == 1 for meal in meal_types)
        else:
            return all(len(meal) >= 1 for meal in meal_types)

    def to_dict(self) -> Dict[str, List[Dict[str, str]]]:
        """Convert selections to dictionary format."""
        if self.mode == SelectionMode.MULTI_SELECT:
            return {
                'mode': self.mode.value,
                'selected_recipes': self.selected_recipes,
                'weekly_plan_text': self.weekly_plan_text
            }

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
            'mode': self.mode.value,
            'weekly_plan_text': self.weekly_plan_text
        }
        
    def get_selected_recipes(self) -> List[str]:
        """Get list of all currently selected recipe IDs (excluding skips)."""
        if self.mode == SelectionMode.MULTI_SELECT:
            return [r for r in self.selected_recipes if r != 'skip']
            
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
            phase: Phase this recipe is for (required for multi-phase mode non-skip selections)
        """
        # Create PhaseRecipeSelection object
        selection = PhaseRecipeSelection(recipe_id=recipe_id, phase=phase)

        # Handle multi-select mode
        if self.mode == SelectionMode.MULTI_SELECT:
            self.toggle_recipe(recipe_id, meal_type, phase)  # Pass all info to toggle_recipe
            return

        # Skip selections don't require phase even in multi-phase mode
        if self.mode == SelectionMode.MULTI_PHASE and not phase and recipe_id != 'skip':
            raise ValueError("Phase is required for multi-phase selections")
            
        meal_selections = getattr(self, meal_type)
        
        if self.mode == SelectionMode.SINGLE:
            # Replace any existing selection
            setattr(self, meal_type, [selection])
        else:
            # Add to existing selections
            meal_selections.append(selection)

    def toggle_recipe(self, recipe_id: str, meal_type: Optional[str] = None, phase: Optional[str] = None) -> None:
        """Toggle a recipe selection on/off in multi-select mode."""
        if self.mode != SelectionMode.MULTI_SELECT:
            raise ValueError("toggle_recipe can only be used in multi-select mode")
            
        if recipe_id in self.selected_recipes:
            self.selected_recipes.remove(recipe_id)
            # Also remove from meal-specific lists
            for m_type in ['breakfast', 'lunch', 'dinner', 'snack']:
                meal_selections = getattr(self, m_type)
                meal_selections[:] = [s for s in meal_selections if s.recipe_id != recipe_id]
        else:
            self.selected_recipes.append(recipe_id)
            # If meal_type and phase provided, add to specific meal list
            if meal_type:
                meal_selections = getattr(self, meal_type)
                meal_selections.append(PhaseRecipeSelection(recipe_id=recipe_id, phase=phase))
    
    def is_recipe_selected(self, recipe_id: str) -> bool:
        """Check if a recipe is currently selected in multi-select mode."""
        if self.mode != SelectionMode.MULTI_SELECT:
            raise ValueError("is_recipe_selected can only be used in multi-select mode")
        return recipe_id in self.selected_recipes

    def clear_selections(self, preserve_mode: bool = False) -> None:
        """
        Clear all recipe selections and associated data.
        
        Args:
            preserve_mode: If True, keep the current selection mode. Otherwise reset to SINGLE.
        """
        current_mode = self.mode if preserve_mode else SelectionMode.SINGLE
        
        # Clear selections
        self.breakfast.clear()
        self.lunch.clear()
        self.dinner.clear()
        self.snack.clear()
        self.selected_recipes.clear()
        
        # Clear weekly plan text when clearing selections
        self.weekly_plan_text = None
        # Preserve snapshot only if still in multi-select mode; otherwise clear
        if current_mode != SelectionMode.MULTI_SELECT:
            self.recipes_snapshot = None
        else:
            # Even in multi-select mode, clear selected state but keep snapshot for stable UI
            pass
        
        # Set mode after clearing
        self.mode = current_mode

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
    def set_multi_select_mode(cls, user_id: str) -> None:
        """
        Enable multi-select mode for user.

        Implementation detail:
        Tests (and runtime) may call this multiple times. Previously, if a selection
        object already existed we only flipped the mode flag and left any prior
        recipe IDs intact. Because RecipeSelectionStorage is a process‑global
        in‑memory singleton, earlier tests (or earlier command flows) could leave
        stale recipe IDs behind for the same user id ("123" in tests). This caused
        the very first toggle in a new test to be treated as a DEselection
        (was_selected=True) and therefore skipped history persistence.

        To ensure deterministic behavior we now:
          - Preserve the stored weekly_plan_text (if any)
          - Clear all prior recipe selections
          - Set mode to MULTI_SELECT

        This guarantees a clean slate each time multi-select mode is (re)enabled.
        """
        if user_id in cls._selections:
            sel = cls._selections[user_id]
            saved_plan = sel.weekly_plan_text
            # Clear previous selections but preserve mode temporarily
            sel.clear_selections(preserve_mode=True)
            sel.weekly_plan_text = saved_plan
            sel.mode = SelectionMode.MULTI_SELECT
        else:
            cls._selections[user_id] = RecipeSelection(mode=SelectionMode.MULTI_SELECT)
    
    @classmethod
    def store_weekly_plan_text(cls, user_id: str, text: str) -> None:
        """
        Store weekly plan text for later use in caching.
        
        Args:
            user_id: User ID to store text for
            text: Weekly plan text to store
        """
        selection = cls.get_selection(user_id)
        selection.weekly_plan_text = text

    @classmethod
    def store_recipes_snapshot(cls, user_id: str, snapshot: Dict) -> None:
        """
        Store the recipes snapshot (single or multi-phase) used to build the keyboard.

        Args:
            user_id: User ID
            snapshot: Dict of recipes keyed by meal_type or phase->meal_type
        """
        selection = cls.get_selection(user_id)
        selection.recipes_snapshot = snapshot

    @classmethod
    def get_recipes_snapshot(cls, user_id: str) -> Optional[Dict]:
        """Return previously stored recipes snapshot (if any)."""
        return cls.get_selection(user_id).recipes_snapshot
    
    @classmethod
    def clear_selection(cls, user_id: str) -> None:
        """Clear user's selections."""
        selection = cls.get_selection(user_id)
        selection.clear_selections()
