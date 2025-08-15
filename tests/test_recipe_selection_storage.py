"""
Tests for recipe selection storage.
"""
import pytest
from src.services.recipe_selection_storage import (
    RecipeSelectionStorage,
    RecipeSelection,
    SelectionMode,
    PhaseRecipeSelection
)

def test_store_weekly_plan_text():
    """Test storing and retrieving weekly plan text."""
    user_id = "123"
    RecipeSelectionStorage.clear_selection(user_id)
    
    plan_text = "Test weekly plan text"
    RecipeSelectionStorage.store_weekly_plan_text(user_id, plan_text)
    
    selection = RecipeSelectionStorage.get_selection(user_id)
    assert selection.weekly_plan_text == plan_text

def test_weekly_plan_text_in_dict():
    """Test weekly plan text is included in dictionary output."""
    user_id = "123"
    RecipeSelectionStorage.clear_selection(user_id)
    
    plan_text = "Test weekly plan text"
    RecipeSelectionStorage.store_weekly_plan_text(user_id, plan_text)
    
    selection = RecipeSelectionStorage.get_selection(user_id)
    selection_dict = selection.to_dict()
    assert selection_dict['weekly_plan_text'] == plan_text

def test_clear_selection_removes_plan_text():
    """Test that clearing selection also removes weekly plan text."""
    user_id = "123"
    RecipeSelectionStorage.clear_selection(user_id)
    
    plan_text = "Test weekly plan text"
    RecipeSelectionStorage.store_weekly_plan_text(user_id, plan_text)
    
    # Clear and verify it's gone
    RecipeSelectionStorage.clear_selection(user_id)
    new_selection = RecipeSelectionStorage.get_selection(user_id)
    assert new_selection.weekly_plan_text is None

def test_recipe_selection_default_init():
    """Test recipe selection initialization includes weekly plan text."""
    selection = RecipeSelection()
    assert selection.weekly_plan_text is None
    assert 'weekly_plan_text' in selection.to_dict()

def test_update_selection_preserves_plan_text():
    """Test that updating recipe selection preserves weekly plan text."""
    user_id = "123"
    RecipeSelectionStorage.clear_selection(user_id)
    
    # Store plan text
    plan_text = "Test weekly plan text"
    RecipeSelectionStorage.store_weekly_plan_text(user_id, plan_text)
    
    # Update selection
    RecipeSelectionStorage.update_selection(
        user_id=user_id,
        meal_type="breakfast",
        recipe_id="test-recipe"
    )
    
    # Verify plan text is preserved
    selection = RecipeSelectionStorage.get_selection(user_id)
    assert selection.weekly_plan_text == plan_text

def test_set_multi_phase_preserves_plan_text():
    """Test that enabling multi-phase mode preserves weekly plan text."""
    user_id = "123"
    RecipeSelectionStorage.clear_selection(user_id)
    
    # Store plan text
    plan_text = "Test weekly plan text"
    RecipeSelectionStorage.store_weekly_plan_text(user_id, plan_text)
    
    # Enable multi-phase mode
    RecipeSelectionStorage.set_multi_phase_mode(user_id)
    
    # Verify plan text is preserved
    selection = RecipeSelectionStorage.get_selection(user_id)
    assert selection.weekly_plan_text == plan_text
    assert selection.mode == SelectionMode.MULTI_PHASE

def test_get_non_existent_selection():
    """Test getting selection for user without any stored data."""
    user_id = "non_existent"
    RecipeSelectionStorage.clear_selection(user_id)
    
    selection = RecipeSelectionStorage.get_selection(user_id)
    assert selection.weekly_plan_text is None
    assert selection.mode == SelectionMode.SINGLE
    assert not selection.breakfast
    assert not selection.lunch
    assert not selection.dinner
    assert not selection.snack

def test_add_selection_with_phase():
    """Test adding a recipe selection with phase information."""
    user_id = "123"
    RecipeSelectionStorage.clear_selection(user_id)
    RecipeSelectionStorage.set_multi_phase_mode(user_id)
    
    # Store plan text
    plan_text = "Test weekly plan text"
    RecipeSelectionStorage.store_weekly_plan_text(user_id, plan_text)
    
    # Add selection with phase
    RecipeSelectionStorage.update_selection(
        user_id=user_id,
        meal_type="breakfast",
        recipe_id="test-recipe",
        phase="power"
    )
    
    selection = RecipeSelectionStorage.get_selection(user_id)
    assert selection.weekly_plan_text == plan_text
    assert selection.breakfast[0].recipe_id == "test-recipe"
    assert selection.breakfast[0].phase == "power"

def test_skip_selection_without_phase():
    """Test that skip selections work without phase even in multi-phase mode."""
    user_id = "123"
    RecipeSelectionStorage.clear_selection(user_id)
    RecipeSelectionStorage.set_multi_phase_mode(user_id)
    
    # Try to skip a meal in multi-phase mode without phase
    RecipeSelectionStorage.update_selection(
        user_id=user_id,
        meal_type="breakfast",
        recipe_id="skip"
    )
    
    selection = RecipeSelectionStorage.get_selection(user_id)
    assert selection.breakfast[0].recipe_id == "skip"
    assert selection.mode == SelectionMode.MULTI_PHASE

def test_to_dict_with_selections_and_plan():
    """Test dictionary output with both selections and plan text."""
    user_id = "123"
    RecipeSelectionStorage.clear_selection(user_id)
    
    # Store plan text
    plan_text = "Test weekly plan text"
    RecipeSelectionStorage.store_weekly_plan_text(user_id, plan_text)
    
    # Add some selections
    RecipeSelectionStorage.update_selection(
        user_id=user_id,
        meal_type="breakfast",
        recipe_id="breakfast-recipe"
    )
    RecipeSelectionStorage.update_selection(
        user_id=user_id,
        meal_type="lunch",
        recipe_id="lunch-recipe"
    )
    
    selection = RecipeSelectionStorage.get_selection(user_id)
    data = selection.to_dict()
    
    assert data['weekly_plan_text'] == plan_text
    assert data['breakfast'][0]['recipe_id'] == "breakfast-recipe"
    assert data['lunch'][0]['recipe_id'] == "lunch-recipe"
    assert data['mode'] == SelectionMode.SINGLE.value
