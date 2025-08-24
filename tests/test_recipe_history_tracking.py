"""Tests for recipe history tracking functionality."""
import pytest
from unittest.mock import Mock, patch

from src.services.recipe import RecipeService
from src.services.recipe_selection_storage import RecipeSelectionStorage
from src.handlers.telegram.commands.weeklyplan import handle_weeklyplan_command, handle_recipe_callback

@pytest.fixture
def mock_telegram():
    """Create mock telegram client."""
    with patch('src.handlers.telegram.commands.weeklyplan.get_telegram') as mock:
        mock_client = Mock()
        mock.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_recipe_service():
    """Create mock recipe service."""
    with patch('src.services.recipe.RecipeService') as mock:
        mock_service = Mock()
        mock.return_value = mock_service
        yield mock_service

@pytest.fixture
def mock_dynamo():
    """Create mock dynamo client."""
    with patch('src.handlers.telegram.commands.weeklyplan.get_dynamo') as mock:
        mock_client = Mock()
        mock.return_value = mock_client
        mock_client.query_items.return_value = []  # No events by default
        yield mock_client

def test_recipe_loading_does_not_save_history(mock_telegram, mock_recipe_service, mock_dynamo):
    """Verify recipe loading doesn't save to history."""
    # Setup
    user_id = "test_user"
    chat_id = "test_chat"
    
    # Setup recipe service mock
    mock_recipes = [
        {'id': 'recipe1', 'title': 'Recipe 1', 'prep_time': 15},
        {'id': 'recipe2', 'title': 'Recipe 2', 'prep_time': 20}
    ]
    mock_recipe_service.get_recipes_by_meal_type.return_value = mock_recipes
    
    # Run weeklyplan command
    handle_weeklyplan_command(user_id, chat_id)
    
    # Verify save_recipe_history was not called during loading
    mock_recipe_service.save_recipe_history.assert_not_called()

def test_recipe_selection_saves_to_history(mock_telegram, mock_recipe_service, mock_dynamo):
    """Verify only selected recipes are saved to history."""
    # Setup
    user_id = "test_user"
    chat_id = "test_chat"
    message_id = "test_message"
    recipe_id = "recipe1"
    
    # Setup recipe service mock
    mock_recipes = [
        {'id': recipe_id, 'title': 'Recipe 1', 'prep_time': 15}
    ]
    mock_recipe_service.get_recipes_by_meal_type.return_value = mock_recipes
    
    # Enable multi-select mode
    RecipeSelectionStorage.set_multi_select_mode(user_id)
    
    # Create callback event for recipe selection
    event = {
        "body": {
            "callback_query": {
                "from": {"id": user_id},
                "message": {
                    "chat": {"id": chat_id},
                    "message_id": message_id
                },
                "data": f"recipe_breakfast_{recipe_id}_power"
            }
        }
    }
    
    # Handle recipe selection callback
    with patch('src.handlers.telegram.commands.weeklyplan.analyze_cycle_phase') as mock_phase:
        mock_phase.return_value.functional_phase.value = 'power'
        handle_recipe_callback(event, test_mode=True)
    
    # Verify save_recipe_history was called only for the selected recipe
    mock_recipe_service.save_recipe_history.assert_called_once_with(
        user_id=user_id,
        recipe_id=recipe_id,
        meal_type='breakfast',  # Default meal type when using toggle_recipe_
        phase='power'
    )

def test_recipe_limit_enforcement(mock_telegram, mock_recipe_service, mock_dynamo):
    """Verify exactly 2 recipes per meal are shown."""
    # Setup
    user_id = "test_user"
    chat_id = "test_chat"
    
    # Mock more than 2 recipes being available
    mock_recipes = [
        {'id': f'recipe{i}', 'title': f'Recipe {i}', 'prep_time': 15}
        for i in range(5)  # Create 5 recipes
    ]
    mock_recipe_service.get_recipes_by_meal_type.return_value = mock_recipes
    
    # Run weeklyplan command
    handle_weeklyplan_command(user_id, chat_id)
    
    # Verify get_recipes_by_meal_type was called with limit=2
    call_args = mock_recipe_service.get_recipes_by_meal_type.call_args_list
    for args in call_args:
        assert args[1].get('limit') == 2, "Recipe limit should be 2"
