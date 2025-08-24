"""Test suite for multi-recipe selection feature."""
import pytest
import logging
from unittest.mock import Mock, patch, call
from src.services.recipe_selection_storage import RecipeSelectionStorage, SelectionMode, RecipeSelection
from src.utils.telegram.keyboards import create_multi_recipe_selection_keyboard
from src.handlers.telegram.commands.weeklyplan import handle_recipe_callback
from src.utils.logging import logger

# Set up debug logging for tests
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s - %(message)s - %(extra)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

class TestMultiRecipeSelection:
    """Test class for multi-recipe selection functionality."""
    
    def setup_method(self):
        """Reset selection storage before each test."""
        RecipeSelectionStorage._selections.clear()
    
    def test_multi_select_mode_initialization(self):
        """Test that multi-select mode is properly initialized."""
        user_id = "test_user_123"
        RecipeSelectionStorage.set_multi_select_mode(user_id)
        
        selection = RecipeSelectionStorage.get_selection(user_id)
        assert selection.mode == SelectionMode.MULTI_SELECT
        assert selection.selected_recipes == []
    
    def test_toggle_recipe_selection(self):
        """Test toggling recipe selections on and off."""
        user_id = "test_user_123"
        RecipeSelectionStorage.set_multi_select_mode(user_id)
        selection = RecipeSelectionStorage.get_selection(user_id)
        
        # Test adding recipe
        selection.toggle_recipe("recipe_1")
        assert "recipe_1" in selection.selected_recipes
        assert selection.is_recipe_selected("recipe_1")
        
        # Test removing recipe
        selection.toggle_recipe("recipe_1")
        assert "recipe_1" not in selection.selected_recipes
        assert not selection.is_recipe_selected("recipe_1")
    
    def test_multiple_recipe_selections(self):
        """Test selecting multiple recipes."""
        user_id = "test_user_123"
        RecipeSelectionStorage.set_multi_select_mode(user_id)
        selection = RecipeSelectionStorage.get_selection(user_id)
        
        recipes = ["breakfast_1", "lunch_1", "dinner_1", "snack_1"]
        for recipe_id in recipes:
            selection.toggle_recipe(recipe_id)
        
        assert len(selection.selected_recipes) == 4
        for recipe_id in recipes:
            assert selection.is_recipe_selected(recipe_id)
            
    def test_clear_selections(self):
        """Test clearing all selections."""
        user_id = "test_user_123"
        RecipeSelectionStorage.set_multi_select_mode(user_id)
        selection = RecipeSelectionStorage.get_selection(user_id)
        
        # Add some selections
        recipes = ["recipe_1", "recipe_2"]
        for recipe_id in recipes:
            selection.toggle_recipe(recipe_id)
            
        # Clear selections
        selection.clear_selections()
        assert len(selection.selected_recipes) == 0
        
    def test_is_complete_multi_select(self):
        """Test is_complete with multi-select mode."""
        user_id = "test_user_123"
        RecipeSelectionStorage.set_multi_select_mode(user_id)
        selection = RecipeSelectionStorage.get_selection(user_id)
        
        # Should be incomplete with no selections
        assert not selection.is_complete()
        
        # Should be complete with any number of selections
        selection.toggle_recipe("recipe_1")
        assert selection.is_complete()
        
        selection.toggle_recipe("recipe_2")
        assert selection.is_complete()

class TestMultiRecipeKeyboard:
    """Test class for multi-recipe selection keyboard."""
    
    def test_keyboard_creation_with_no_selections(self):
        """Test keyboard creation with no recipes selected."""
        recipes_by_meal_type = {
            'breakfast': [
                {'id': 'pancakes', 'title': 'Fluffy Pancakes', 'prep_time': 15},
                {'id': 'oats', 'title': 'Overnight Oats', 'prep_time': 5}
            ],
            'lunch': [
                {'id': 'salad', 'title': 'Quinoa Salad', 'prep_time': 20},
                {'id': 'wrap', 'title': 'Turkey Wrap', 'prep_time': 10}
            ]
        }
        
        keyboard = create_multi_recipe_selection_keyboard(recipes_by_meal_type)
        
        # Check keyboard has proper structure
        assert 'inline_keyboard' in keyboard
        buttons = keyboard['inline_keyboard']
        
        # Check for meal headers and recipe buttons
        button_texts = [btn['text'] for row in buttons for btn in row if 'text' in btn]
        assert any('BREAKFAST' in text for text in button_texts)
        assert any('LUNCH' in text for text in button_texts)
        assert any('⭕ Fluffy Pancakes' in text for text in button_texts)
        assert any('⭕ Overnight Oats' in text for text in button_texts)
        
        # Check no shopping list button without selections
        assert not any('Generate Shopping List' in text for text in button_texts)
    
    def test_keyboard_creation_with_selections(self):
        """Test keyboard shows selected recipes with checkmarks."""
        recipes_by_meal_type = {
            'breakfast': [
                {'id': 'pancakes', 'title': 'Fluffy Pancakes', 'prep_time': 15},
                {'id': 'oats', 'title': 'Overnight Oats', 'prep_time': 5}
            ]
        }
        selected_recipes = ['pancakes']
        
        keyboard = create_multi_recipe_selection_keyboard(recipes_by_meal_type, selected_recipes)
        button_texts = [btn['text'] for row in keyboard['inline_keyboard'] for btn in row if 'text' in btn]
        
        # Check selected recipe has checkmark, unselected has circle
        assert any('✅ Fluffy Pancakes' in text for text in button_texts)
        assert any('⭕ Overnight Oats' in text for text in button_texts)
        
        # Check utility buttons appear (new UX: no separate Generate button)
        assert any('Done Selecting' in text for text in button_texts)
        assert not any('Generate Shopping List' in text for text in button_texts)
    
    def test_keyboard_utility_buttons(self):
        """Test utility buttons appear correctly."""
        recipes_by_meal_type = {
            'breakfast': [
                {'id': 'pancakes', 'title': 'Fluffy Pancakes', 'prep_time': 15},
                {'id': 'oats', 'title': 'Overnight Oats', 'prep_time': 5}
            ]
        }
        
        # Test with no selections
        keyboard = create_multi_recipe_selection_keyboard(recipes_by_meal_type)
        button_texts = [btn['text'] for row in keyboard['inline_keyboard'] for btn in row if 'text' in btn]
        
        # Should only have Select All
        assert not any('Clear All' in text for text in button_texts)
        assert any('Select All' in text for text in button_texts)
        
        # Test with some selections
        selected_recipes = ['pancakes']
        keyboard = create_multi_recipe_selection_keyboard(recipes_by_meal_type, selected_recipes)
        button_texts = [btn['text'] for row in keyboard['inline_keyboard'] for btn in row if 'text' in btn]
        
        # Should have both Clear All and Select All
        assert any('Clear All' in text for text in button_texts)
        assert any('Select All' in text for text in button_texts)
        
        # Test with all selected
        selected_recipes = ['pancakes', 'oats']
        keyboard = create_multi_recipe_selection_keyboard(recipes_by_meal_type, selected_recipes)
        button_texts = [btn['text'] for row in keyboard['inline_keyboard'] for btn in row if 'text' in btn]
        
        # Should only have Clear All
        assert any('Clear All' in text for text in button_texts)
        assert not any('Select All' in text for text in button_texts)
        
    def test_recipe_limit_enforcement(self):
        """Test that no more than 2 recipes are shown per meal type."""
        recipes_by_meal_type = {
            'breakfast': [
                {'id': 'breakfast1', 'title': 'Breakfast 1', 'prep_time': 15},
                {'id': 'breakfast2', 'title': 'Breakfast 2', 'prep_time': 20},
                {'id': 'breakfast3', 'title': 'Breakfast 3', 'prep_time': 25}  # Extra recipe
            ],
            'lunch': [
                {'id': 'lunch1', 'title': 'Lunch 1', 'prep_time': 15},
                {'id': 'lunch2', 'title': 'Lunch 2', 'prep_time': 20},
                {'id': 'lunch3', 'title': 'Lunch 3', 'prep_time': 25},  # Extra recipe
                {'id': 'lunch4', 'title': 'Lunch 4', 'prep_time': 30}   # Extra recipe
            ]
        }
        
        keyboard = create_multi_recipe_selection_keyboard(recipes_by_meal_type)
        buttons = keyboard['inline_keyboard']
        
        # Count recipe buttons for each meal type
        breakfast_recipes = [
            btn['text'] for row in buttons for btn in row 
            if 'Breakfast' in btn['text'] and ('⭕' in btn['text'] or '✅' in btn['text'])
        ]
        lunch_recipes = [
            btn['text'] for row in buttons for btn in row 
            if 'Lunch' in btn['text'] and ('⭕' in btn['text'] or '✅' in btn['text'])
        ]
        
        # Verify limits
        assert len(breakfast_recipes) == 2, f"Expected 2 breakfast recipes, got {len(breakfast_recipes)}"
        assert len(lunch_recipes) == 2, f"Expected 2 lunch recipes, got {len(lunch_recipes)}"
        
        # Verify specific recipes
        assert any('Breakfast 1' in text for text in breakfast_recipes)
        assert any('Breakfast 2' in text for text in breakfast_recipes)
        assert not any('Breakfast 3' in text for text in breakfast_recipes)
        
        assert any('Lunch 1' in text for text in lunch_recipes)
        assert any('Lunch 2' in text for text in lunch_recipes)
        assert not any('Lunch 3' in text for text in lunch_recipes)
        assert not any('Lunch 4' in text for text in lunch_recipes)

class TestMultiRecipeCallbacks:
    """Test class for multi-recipe selection callbacks."""
    
    @pytest.fixture
    def mock_telegram(self):
        """Create mock telegram client."""
        with patch('src.handlers.telegram.commands.weeklyplan.get_telegram') as mock:
            mock_client = Mock()
            mock.return_value = mock_client
            yield mock_client
            
    @pytest.fixture
    def mock_recipe_service(self):
        """Create mock recipe service."""
        with patch('src.handlers.telegram.commands.weeklyplan.RecipeService') as mock:
            mock_service = Mock()
            mock.return_value = mock_service
            yield mock_service
            
    def test_toggle_recipe_callback(self, mock_telegram, mock_recipe_service):
        """Test recipe toggle callback handling."""
        user_id = "123"
        chat_id = "456"
        message_id = "789"
        
        # Setup recipe service mock
        mock_recipe_service.get_recipes_by_meal_type.return_value = [
            {'id': 'recipe1', 'title': 'Recipe 1', 'prep_time': 15}
        ]
        
        # Enable multi-select mode
        RecipeSelectionStorage.set_multi_select_mode(user_id)
        
        # Create callback event
        event = {
            "body": {
                "callback_query": {
                    "from": {"id": user_id},
                    "message": {
                        "chat": {"id": chat_id},
                        "message_id": message_id
                    },
                    "data": "recipe_breakfast_recipe1_power"
                }
            }
        }
        
        # Test callback
        response = handle_recipe_callback(event, test_mode=True)
            
        assert response["statusCode"] == 200
        
        # Verify selection was toggled
        selection = RecipeSelectionStorage.get_selection(user_id)
        assert "recipe1" in selection.selected_recipes
        
        # Verify keyboard was updated
        mock_telegram.edit_message_reply_markup.assert_called_once()
        
    def test_recipe_history_tracking(self, mock_telegram, mock_recipe_service):
        """Test that recipes are saved to history only when selected."""
        user_id = "123"
        chat_id = "456"
        message_id = "789"
        
        # Setup recipe service mock
        mock_recipe_service.get_recipes_by_meal_type.return_value = [
            {'id': 'recipe1', 'title': 'Recipe 1', 'prep_time': 15}
        ]
        
        # Enable multi-select mode
        RecipeSelectionStorage.set_multi_select_mode(user_id)
        
        # Create toggle ON event
        event_toggle_on = {
            "body": {
                "callback_query": {
                    "from": {"id": user_id},
                    "message": {
                        "chat": {"id": chat_id},
                        "message_id": message_id
                    },
                    "data": "recipe_breakfast_recipe1_power"
                }
            }
        }
        
        # Test toggle ON callback
        response = handle_recipe_callback(event_toggle_on, test_mode=True)
        assert response["statusCode"] == 200
        
        # Verify recipe was saved to history when selected
        mock_recipe_service.save_recipe_history.assert_called_with(
            user_id=user_id,
            recipe_id="recipe1",
            meal_type="breakfast",
            phase="power"
        )
        
        # Reset mock call count
        mock_recipe_service.save_recipe_history.reset_mock()
        
        # Create toggle OFF event (same recipe)
        event_toggle_off = {
            "body": {
                "callback_query": {
                    "from": {"id": user_id},
                    "message": {
                        "chat": {"id": chat_id},
                        "message_id": message_id
                    },
                    "data": "recipe_breakfast_recipe1_power"
                }
            }
        }
        
        # Test toggle OFF callback
        response = handle_recipe_callback(event_toggle_off, test_mode=True)
        assert response["statusCode"] == 200
        
        # Verify recipe was NOT saved to history when deselected
        mock_recipe_service.save_recipe_history.assert_not_called()
        
    def test_generate_shopping_list_callback(self, mock_telegram, mock_recipe_service):
        """Test generate shopping list callback."""
        user_id = "123"
        chat_id = "456"
        
        # Setup recipe service mock
        mock_recipe_service.get_multiple_recipe_ingredients.return_value = ["ingredient1"]
        mock_recipe_service.get_recipe_by_id.return_value = Mock(
            title="Test Recipe",
            url="http://example.com/recipe"
        )
        
        # Enable multi-select mode and add selection
        RecipeSelectionStorage.clear_selection(user_id)  # Clear any existing selections
        RecipeSelectionStorage.set_multi_select_mode(user_id)
        selection = RecipeSelectionStorage.get_selection(user_id)
        selection.toggle_recipe("recipe1")
        
        # Double verify recipe was selected and persisted
        assert "recipe1" in selection.selected_recipes
        selection = RecipeSelectionStorage.get_selection(user_id)
        assert "recipe1" in selection.selected_recipes
        
        # Create callback event
        event = {
            "body": {
                "callback_query": {
                    "from": {"id": user_id},
                    "message": {
                        "chat": {"id": chat_id},
                        "message_id": "789"
                    },
                    "data": "generate_shopping_list"
                }
            }
        }
        
        # Test callback
        with patch('src.handlers.telegram.commands.weeklyplan.ShoppingListService') as mock_shopping:
            mock_shopping.return_value.format_list.return_value = "Shopping list"
            response = handle_recipe_callback(event, test_mode=True)
            
        assert response["statusCode"] == 200
        
        # Verify both shopping list and recipe links were sent (in that order)
        assert len(mock_telegram.send_message.call_args_list) == 2
        # First call should be shopping list
        assert mock_telegram.send_message.call_args_list[0] == call(
            chat_id=chat_id,
            text="Shopping list",
            parse_mode='Markdown'
        )
        # Second call should be recipe links
        assert mock_telegram.send_message.call_args_list[1] == call(
            chat_id=chat_id,
            text='📖 **Recipe Links**\n\n\n• Test Recipe\n  http://example.com/recipe\n\n\nHappy cooking! 👩‍🍳',
            parse_mode='Markdown'
        )
        
    def test_clear_selections_callback(self, mock_telegram, mock_recipe_service):
        """Test clear selections callback."""
        user_id = "123"
        chat_id = "456"
        message_id = "789"
        
        # Setup recipe service mock
        mock_recipe_service.get_recipes_by_meal_type.return_value = [
            {'id': 'recipe1', 'title': 'Recipe 1', 'prep_time': 15}
        ]
        
        # Enable multi-select mode and add selections
        RecipeSelectionStorage.set_multi_select_mode(user_id)
        selection = RecipeSelectionStorage.get_selection(user_id)
        selection.toggle_recipe("recipe1")
        selection.toggle_recipe("recipe2")
        
        # Create callback event
        event = {
            "body": {
                "callback_query": {
                    "from": {"id": user_id},
                    "message": {
                        "chat": {"id": chat_id},
                        "message_id": message_id
                    },
                    "data": "clear_selections"
                }
            }
        }
        
        # Test callback
        with patch('src.handlers.telegram.commands.weeklyplan.analyze_cycle_phase') as mock_phase:
            mock_phase.return_value.functional_phase.value = 'power'
            response = handle_recipe_callback(event, test_mode=True)
            
        assert response["statusCode"] == 200
        
        # Verify selections were cleared
        selection = RecipeSelectionStorage.get_selection(user_id)
        assert len(selection.selected_recipes) == 0
        
        # Verify keyboard was updated
        mock_telegram.edit_message_reply_markup.assert_called_once()
        
    def test_select_all_available_callback(self, mock_telegram, mock_recipe_service):
        """Test select all available recipes callback."""
        user_id = "123"
        chat_id = "456"
        message_id = "789"
        
        # Setup recipe service mock with test recipes for each meal type
        test_recipes = {
            'breakfast': [
                {'id': 'breakfast1', 'title': 'Breakfast 1', 'prep_time': 15},
                {'id': 'breakfast2', 'title': 'Breakfast 2', 'prep_time': 20}
            ],
            'lunch': [
                {'id': 'lunch1', 'title': 'Lunch 1', 'prep_time': 15},
                {'id': 'lunch2', 'title': 'Lunch 2', 'prep_time': 20}
            ],
            'dinner': [
                {'id': 'dinner1', 'title': 'Dinner 1', 'prep_time': 15},
                {'id': 'dinner2', 'title': 'Dinner 2', 'prep_time': 20}
            ],
            'snack': [
                {'id': 'snack1', 'title': 'Snack 1', 'prep_time': 15},
                {'id': 'snack2', 'title': 'Snack 2', 'prep_time': 20}
            ]
        }
        
        # Clear any existing selections and enable multi-select mode
        RecipeSelectionStorage.clear_selection(user_id)
        RecipeSelectionStorage.set_multi_select_mode(user_id)
        selection = RecipeSelectionStorage.get_selection(user_id)
        
        # Verify initial state
        assert len(selection.selected_recipes) == 0
        
        # Mock get_recipes_by_meal_type to return different recipes for each meal type
        def get_recipes_by_meal_type(meal_type: str, phase: str = None, limit: int = None):
            return test_recipes.get(meal_type, [])
        mock_recipe_service.get_recipes_by_meal_type.side_effect = get_recipes_by_meal_type
        mock_recipe_service.load_recipes_for_meal_planning.return_value = None
        
        # Create callback event
        event = {
            "body": {
                "callback_query": {
                    "from": {"id": user_id},
                    "message": {
                        "chat": {"id": chat_id},
                        "message_id": message_id
                    },
                    "data": "select_all_available"
                }
            }
        }
        
        # Test callback
        with patch('src.handlers.telegram.commands.weeklyplan.analyze_cycle_phase') as mock_phase:
            mock_phase.return_value.functional_phase.value = 'power'
            response = handle_recipe_callback(event, test_mode=True)
            
        assert response["statusCode"] == 200
        
        # Verify selection immediately after callback
        selection = RecipeSelectionStorage.get_selection(user_id)
        selected_recipes = selection.selected_recipes
        
        # Debug logging
        print(f"Selected recipes after callback: {selected_recipes}")
        all_recipe_ids = [r['id'] for recipes in test_recipes.values() for r in recipes]
        print(f"Expected recipes: {all_recipe_ids}")
        
        # Verify all recipes were selected once
        assert len(selected_recipes) == len(all_recipe_ids), \
            f"Expected {len(all_recipe_ids)} selections but got {len(selected_recipes)}"
        for recipe_id in all_recipe_ids:
            assert recipe_id in selected_recipes, \
                f"Recipe {recipe_id} not found in selections {selected_recipes}"
        
        # Verify keyboard was updated
        mock_telegram.edit_message_reply_markup.assert_called_once()
