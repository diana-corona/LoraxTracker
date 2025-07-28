"""
Weekly plan command module.

This module provides functionality for generating on-demand weekly plans
and recipe selections through a Telegram command interface.

Typical usage:
    User sends: /weeklyplan
    Bot responds with a personalized weekly plan and recipe selection options
"""
import json
from typing import Optional, Dict, Any, List

from aws_lambda_powertools import Logger
from src.utils.telegram.keyboards import create_recipe_selection_keyboard
from src.services.recipe import RecipeService
from src.services.recipe_selection_storage import RecipeSelectionStorage

from src.utils.dynamo import create_pk
from src.models.event import CycleEvent
from src.services.weekly_plan import generate_weekly_plan, format_weekly_plan
from src.services.cycle import analyze_cycle_phase
from src.utils.clients import get_telegram, get_dynamo, get_clients

logger = Logger()

# Map of meal types to emojis
MEAL_EMOJIS = {
    'breakfast': '🥞',
    'lunch': '🥗',
    'dinner': '🍽️',
    'snack': '🍿'
}

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

def handle_weeklyplan_command(user_id: str, chat_id: str) -> Dict[str, Any]:
    """
    Handle /weeklyplan command to generate an on-demand weekly plan and start recipe selection.

    This handler retrieves cycle events, generates a personalized weekly plan,
    and initiates the recipe selection process for the user's current phase.

    Args:
        user_id: The Telegram user ID
        chat_id: The Telegram chat ID

    Returns:
        Dict containing the response status and message

    Raises:
        ValueError: If no cycle events found
        Exception: For unexpected errors during plan generation
    """
    
    logger.info("Processing weeklyplan command", extra={
        "user_id": user_id,
        "chat_id": chat_id
    })

    # Get clients lazily
    dynamo, telegram = get_clients()

    try:
        # Get user's events
        events = dynamo.query_items(
            partition_key="PK",
            partition_value=create_pk(user_id)
        )
        
        # Convert to CycleEvent objects
        cycle_events = [
            CycleEvent(**event)
            for event in events
            if event["SK"].startswith("EVENT#")
        ]
        
        if not cycle_events:
            logger.warning("No cycle events found", extra={
                "user_id": user_id
            })
            raise ValueError("No cycle events found. Please register some events first.")
            
        # Generate and format weekly plan
        weekly_plan = generate_weekly_plan(cycle_events)
        formatted_plan = format_weekly_plan(weekly_plan)
        
        # Send plan
        telegram.send_message(
            chat_id=chat_id,
            text="\n".join(formatted_plan)
        )
        
        logger.info("Weekly plan generated successfully", extra={
            "user_id": user_id,
            "chat_id": chat_id,
            "plan_start": weekly_plan.start_date.isoformat(),
            "plan_end": weekly_plan.end_date.isoformat()
        })

        # Clear any previous recipe selections
        RecipeSelectionStorage.clear_selection(user_id)
        
        # Get user's current phase
        current_phase = analyze_cycle_phase(cycle_events)
        phase_type = current_phase.functional_phase.value
        
        # Start recipe selection process with phase-specific recipes
        recipe_service = RecipeService()
        breakfast_recipes = recipe_service.get_recipes_by_meal_type('breakfast', phase=phase_type, limit=2)
        keyboard = create_recipe_selection_keyboard(breakfast_recipes, 'breakfast')

        # Send recipe selection message
        telegram.send_message(
            chat_id=chat_id,
            text=(
                "Let's select recipes for your meal plan! 📝\n\n"
                f"{MEAL_EMOJIS['breakfast']} First, choose your breakfast:"
            ),
            reply_markup=keyboard
        )
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "ok": True,
                "result": {"message": "Weekly plan sent"}
            }),
            "isBase64Encoded": False
        }
        
    except ValueError as e:
        telegram.send_message(
            chat_id=chat_id,
            text=f"⚠️ {str(e)}"
        )
    except Exception as e:
        logger.exception(
            "Error generating weekly plan",
            extra={
                "user_id": user_id,
                "error_type": e.__class__.__name__
            }
        )
        telegram.send_message(
            chat_id=chat_id,
            text="Sorry, there was an error generating your weekly plan. Please try again later."
        )
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
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

        # Get current phase
        events = get_dynamo().query_items(
            partition_key="PK",
            partition_value=create_pk(user_id)
        )
        cycle_events = [
            CycleEvent(**event)
            for event in events
            if event["SK"].startswith("EVENT#")
        ]
        current_phase = analyze_cycle_phase(cycle_events)
        phase_type = current_phase.functional_phase.value

        # Get recipes for next selection
        recipe_service = RecipeService()

        # Determine next meal type to select
        meal_types = ['breakfast', 'lunch', 'dinner', 'snack']
        current_idx = meal_types.index(meal_type)
        
        if current_idx < len(meal_types) - 1:
            # Show next meal selection with phase-specific options
            next_meal = meal_types[current_idx + 1]
            next_recipes = recipe_service.get_recipes_by_meal_type(next_meal, phase=phase_type, limit=2)
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
