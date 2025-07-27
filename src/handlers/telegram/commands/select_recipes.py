"""
Recipe selection command module.

This module provides functionality for selecting recipes and generating
shopping lists through a Telegram command interface.

Typical usage:
    User sends: /select_recipes
    Bot responds with meal selection options
"""
import json
from typing import Dict, Any

from aws_lambda_powertools import Logger

from src.utils.clients import get_telegram, get_clients
from src.utils.telegram.keyboards import create_recipe_selection_keyboard
from src.services.recipe_selection_storage import RecipeSelectionStorage
from src.services.recipe import RecipeService, CategorizedIngredients

logger = Logger()

# Shopping list category emojis
SHOPPING_ICONS = {
    'proteins': '🥩',
    'produce': '🥬',
    'dairy': '🥛',
    'baking': '🥖',
    'nuts': '🥜',
    'condiments': '🫙',
    'pantry': '🏠'
}

# Map of meal types to emojis
MEAL_EMOJIS = {
    'breakfast': '🥞',
    'lunch': '🥗',
    'dinner': '🍽️',
    'snack': '🍿'
}

def handle_select_recipes_command(user_id: str, chat_id: str) -> Dict[str, Any]:
    """
    Handle /select_recipes command to start recipe selection process.

    Args:
        user_id: The Telegram user ID
        chat_id: The Telegram chat ID

    Returns:
        Dict containing the response status and message
    """
    logger.info("Starting recipe selection process", extra={
        "user_id": user_id,
        "chat_id": chat_id
    })

    # Clear any previous selections
    RecipeSelectionStorage.clear_selection(user_id)

    # Get telegram client
    telegram = get_telegram()

    try:
        # Get recipes for breakfast
        recipe_service = RecipeService()
        breakfast_recipes = recipe_service.get_recipes_by_meal_type('breakfast')
        keyboard = create_recipe_selection_keyboard(breakfast_recipes, 'breakfast')

        # Send initial selection message
        telegram.send_message(
            chat_id=chat_id,
            text=(
                "Let's select your recipes! 📝\n\n"
                f"{MEAL_EMOJIS['breakfast']} First, choose your breakfast:"
            ),
            reply_markup=keyboard
        )

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"ok": True}),
            "isBase64Encoded": False
        }

    except Exception as e:
        logger.exception(
            "Error starting recipe selection",
            extra={
                "user_id": user_id,
                "error_type": e.__class__.__name__
            }
        )
        telegram.send_message(
            chat_id=chat_id,
            text="Sorry, there was an error starting recipe selection. Please try again later."
        )
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "ok": False,
                "error_code": 500,
                "description": str(e)
            }),
            "isBase64Encoded": False
        }

def handle_recipe_callback(callback_query: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle recipe selection callback from inline keyboard.

    Args:
        callback_query: The callback query from Telegram

    Returns:
        Dict containing the response status and message
    """
    user_id = str(callback_query['from']['id'])
    chat_id = str(callback_query['message']['chat']['id'])
    callback_data = callback_query['data']
    
    # Extract meal type and recipe id from callback data
    # Format: recipe_<meal_type>_<recipe_id>
    _, meal_type, recipe_id = callback_data.split('_', 2)

    logger.info("Processing recipe selection", extra={
        "user_id": user_id,
        "meal_type": meal_type,
        "recipe_id": recipe_id
    })

    telegram = get_telegram()

    try:
        # Update selection storage
        RecipeSelectionStorage.update_selection(user_id, meal_type, recipe_id)
        selection = RecipeSelectionStorage.get_selection(user_id)

        # Get recipes for next selection
        recipe_service = RecipeService()

        # Determine next meal type to select
        meal_types = ['breakfast', 'lunch', 'dinner', 'snack']
        current_idx = meal_types.index(meal_type)
        
        if current_idx < len(meal_types) - 1:
            # Show next meal selection
            next_meal = meal_types[current_idx + 1]
            next_recipes = recipe_service.get_recipes_by_meal_type(next_meal)
            keyboard = create_recipe_selection_keyboard(next_recipes, next_meal)
            
            telegram.send_message(
                chat_id=chat_id,
                text=f"{MEAL_EMOJIS[next_meal]} Now, choose your {next_meal}:",
                reply_markup=keyboard
            )
        else:
            # Get all selected recipe IDs
            selected_recipe_ids = list(selection.to_dict().values())

            # Get combined ingredients for all selected recipes
            ingredients = recipe_service.get_multiple_recipe_ingredients(selected_recipe_ids)

            # Generate formatted shopping list
            shopping_list = ["🛒 Shopping List\n"]
            
            # Add non-pantry ingredients by category
            for category in ['proteins', 'produce', 'dairy', 'condiments', 'baking', 'nuts']:
                items = getattr(ingredients, category)
                if items:
                    emoji = SHOPPING_ICONS.get(category, '•')
                    shopping_list.extend([
                        f"\n{emoji} {category.title()}:",
                        *[f"  • {item}" for item in sorted(items)]
                    ])

            # Add pantry items note if any were used
            pantry_items = [item for item in ingredients.pantry if recipe_service.is_pantry_item(item)]
            if pantry_items:
                shopping_list.extend([
                    "\n🏠 Pantry Items to Check:",
                    "(These basic ingredients are assumed to be in most kitchens)",
                    *[f"  • {item}" for item in sorted(pantry_items)]
                ])

            # Send final list
            telegram.send_message(
                chat_id=chat_id,
                text="\n".join(shopping_list)
            )

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"ok": True}),
            "isBase64Encoded": False
        }

    except Exception as e:
        logger.exception(
            "Error processing recipe selection",
            extra={
                "user_id": user_id,
                "error_type": e.__class__.__name__
            }
        )
        telegram.send_message(
            chat_id=chat_id,
            text="Sorry, there was an error processing your selection. Please try again later."
        )
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "ok": False,
                "error_code": 500,
                "description": str(e)
            }),
            "isBase64Encoded": False
        }
