"""
Weekly plan command module.

This module provides functionality for generating on-demand weekly plans
and recipe selections through a Telegram command interface.

The module handles both the initial weekly plan generation and the subsequent
recipe selection process through interactive Telegram keyboards.

Typical usage:
    # Initial command
    User: /weeklyplan
    Bot: *Displays weekly plan*
         *Shows breakfast recipe options*
    
    # Recipe selection
    User: *Clicks recipe option*
    Bot: *Shows next meal type options*
         *Continues until all meals selected*
         *Finally shows shopping list*

Components:
    - handle_weeklyplan_command: Primary command handler
    - handle_recipe_callback: Handles recipe selection interactions
    - RecipeSelectionStorage: Manages recipe selection state
"""

import os
from datetime import datetime
import json
from typing import Optional, Dict, Any, List

from aws_lambda_powertools.utilities.typing import LambdaContext
from src.handlers.telegram.exceptions import (
    NoEventsError,
    WeeklyPlanError,
    RecipeSelectionError,
    RecipeNotFoundError
)
from src.utils.telegram.keyboards import create_recipe_selection_keyboard
from src.services.recipe import RecipeService
from src.services.recipe_selection_storage import RecipeSelectionStorage
from src.services.shopping_list import ShoppingListService

from src.utils.dynamo import create_pk
from src.models.event import CycleEvent
from src.services.weekly_plan import generate_weekly_plan, format_weekly_plan
from src.services.cycle import analyze_cycle_phase
from src.utils.clients import get_telegram, get_dynamo, get_clients
from src.utils.auth import Authorization
from src.utils.logging import logger

def get_all_clients():
    """Get all required clients."""
    dynamo = get_dynamo()
    telegram = get_telegram()
    auth = Authorization(dynamo_client=dynamo)
    return dynamo, telegram, auth

def get_table_name() -> str:
    """Get DynamoDB table name with stage suffix."""
    service = os.environ.get('POWERTOOLS_SERVICE_NAME', 'lorax-tracker')
    stage = os.environ.get('STAGE', 'dev')
    return f"{service}-{stage}-TrackerTable"

# Map of meal types to emojis
MEAL_EMOJIS = {
    'breakfast': '🥞',
    'lunch': '🥗',
    'dinner': '🍽️',
    'snack': '🍿'
}

def handle_weeklyplan_command(user_id: str, chat_id: str, message: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Handle /weeklyplan command to generate a weekly plan and start recipe selection.

    This handler orchestrates the weekly plan generation process:
    1. Retrieves user's cycle events
    2. Generates a personalized weekly plan based on cycle phase
    3. Formats and sends the plan to the user
    4. Initiates recipe selection workflow starting with breakfast

    Args:
        user_id: The Telegram user ID to generate plan for
        chat_id: The Telegram chat ID to send responses to

    Returns:
        Dict[str, Any]: API Gateway response containing:
            {
                "statusCode": int,
                "headers": Dict[str, str],
                "body": str,
                "isBase64Encoded": bool
            }

    Raises:
        ValueError: If no cycle events found for the user
        ResourceNotFoundError: If required recipes not found
        AuthorizationError: If user is not authorized
        Exception: For unexpected errors during plan generation
    """
    
    logger.info("Processing weeklyplan command", extra={
        "user_id": user_id,
        "chat_id": chat_id,
        "command_timestamp": datetime.now().isoformat()
    })

    # Get all clients with auth
    dynamo, telegram, auth = get_all_clients()
    
    # Verify user authorization
    try:
        if not auth.check_user_authorized(user_id):
            logger.warning(f"Unauthorized weeklyplan access attempt", extra={"user_id": user_id})
            telegram.send_message(
                chat_id=chat_id,
                text="⚠️ You are not authorized to use this command."
            )
            return {
                "statusCode": 403,
                "body": json.dumps({
                    "ok": False,
                    "error_code": "UNAUTHORIZED",
                    "description": "User not authorized"
                })
            }
    except Exception as e:
        logger.error(
            "Error checking user authorization",
            extra={
                "user_id": user_id,
                "error": str(e),
                "error_type": e.__class__.__name__
            }
        )

    try:
        # Get user's events
        table_name = get_table_name()
        logger.debug(f"Using table: {table_name}")
        events = dynamo.query_items(
            partition_key="PK",
            partition_value=create_pk(user_id)
        )
        logger.info(f"Found {len(events)} total events for user {user_id}")
        
        # Convert to CycleEvent objects with error tracking
        cycle_events = []
        for event in events:
            try:
                if event["SK"].startswith("EVENT#"):
                    cycle_events.append(CycleEvent(**event))
            except Exception as e:
                logger.warning(
                    "Failed to parse cycle event",
                    extra={
                        "user_id": user_id,
                        "event": event,
                        "error": str(e),
                        "error_type": e.__class__.__name__
                    }
                )
                continue
        
        logger.info(f"Successfully parsed {len(cycle_events)} cycle events")
        
        if not cycle_events:
            logger.warning(
                "No valid cycle events found for user",
                extra={
                    "user_id": user_id,
                    "total_events": len(events),
                    "action": "weekly_plan_generation"
                }
            )
            raise NoEventsError("No cycle events found. Please register a cycle event first using the /registrar command.")
        
        # Generate and format weekly plan
        weekly_plan = generate_weekly_plan(cycle_events)
        formatted_plan = format_weekly_plan(weekly_plan)
        
        # Check if next phase should be shown
        next_phase_info = None
        if weekly_plan.phase_groups:
            last_group = weekly_plan.phase_groups[-1]
            days_until_transition = (last_group.functional_phase_end - datetime.now().date()).days
            next_phase = last_group.next_functional_phase.value if last_group.next_functional_phase else None
            
            logger.info("Phase transition check", extra={
                "user_id": user_id,
                "current_phase": last_group.functional_phase.value,
                "next_phase": next_phase,
                "days_until_transition": days_until_transition,
                "has_next_phase": bool(last_group.next_functional_phase),
                "has_next_recs": bool(last_group.next_phase_recommendations)
            })
            
            if days_until_transition <= 3:
                next_phase_info = {
                    "phase": next_phase,
                    "days": days_until_transition,
                    "has_recs": bool(last_group.next_phase_recommendations)
                }
        
        logger.info(
            "Generated weekly plan",
            extra={
                "user_id": user_id,
                "plan_start": weekly_plan.start_date.isoformat(),
                "plan_end": weekly_plan.end_date.isoformat(),
                "phase_groups": len(weekly_plan.phase_groups),
                "next_phase_info": next_phase_info
            }
        )
        
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
        
        try:
            # Get user's current phase
            current_phase = analyze_cycle_phase(cycle_events)
            phase_type = current_phase.functional_phase.value
            
            # Load and select phase-specific recipes for meal planning with rotation
            recipe_service = RecipeService()
            recipe_service.load_recipes_for_meal_planning(phase=phase_type, user_id=user_id)
            
            # Get breakfast recipes and save to history
            breakfast_recipes = recipe_service.get_recipes_by_meal_type('breakfast', phase=phase_type, limit=2)
            for recipe in breakfast_recipes:
                recipe_service.save_recipe_history(
                    user_id=user_id,
                    recipe_id=recipe['id'],
                    meal_type='breakfast',
                    phase=phase_type
                )
            
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

            logger.info("Recipe selection setup completed", extra={
                "user_id": user_id,
                "phase": phase_type,
                "recipes_count": len(breakfast_recipes)
            })

        except Exception as e:
            logger.exception(
                "Failed to setup recipe selection",
                extra={
                    "user_id": user_id,
                    "error_type": e.__class__.__name__
                }
            )
            raise WeeklyPlanError("Error setting up recipe selection") from e
        
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
        
    except NoEventsError as e:
        logger.warning("Weekly plan generation failed - no events", extra={
            "user_id": user_id,
            "error": str(e),
            "error_type": "NO_EVENTS"
        })
        telegram.send_message(
            chat_id=chat_id,
            text=f"⚠️ {str(e)}"
        )
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "ok": False,
                "error_code": "NO_EVENTS",
                "description": str(e)
            }),
            "isBase64Encoded": False
        }
    except WeeklyPlanError as e:
        logger.error("Weekly plan generation failed", extra={
            "user_id": user_id,
            "error": str(e),
            "error_type": "WEEKLY_PLAN_ERROR"
        })
        telegram.send_message(
            chat_id=chat_id,
            text=f"⚠️ Error generating weekly plan: {str(e)}"
        )
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "ok": False,
                "error_code": "WEEKLY_PLAN_ERROR",
                "description": str(e)
            }),
            "isBase64Encoded": False
        }
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

def handle_recipe_callback(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle recipe selection callback from inline keyboard.

    Processes user's recipe selections through the meal planning workflow:
    1. Updates selection storage with chosen recipe
    2. Determines next meal type to select
    3. Either shows next meal options or generates shopping list
    4. Handles all meal types: breakfast, lunch, dinner, snack

    Args:
        event: Lambda event containing:
            body: Dict containing:
                callback_query: The Telegram callback query containing:
                    - from: Dict with user ID
                    - message: Dict with chat info
                    - data: String in format "recipe_<meal_type>_<recipe_id>"

    Returns:
        Dict[str, Any]: API Gateway response containing:
            {
                "statusCode": int,
                "headers": Dict[str, str],
                "body": str,
                "isBase64Encoded": bool
            }

    Raises:
        AuthorizationError: If user is not authorized
        ValueError: If callback data is malformed
        ResourceNotFoundError: If required recipes not found
        Exception: For unexpected errors during selection process
    """
    # Extract callback query from wrapped event
    logger.debug("Received recipe callback event", extra={
        "event_type": type(event).__name__,
        "has_body": "body" in event,
        "body_type": type(event.get("body")).__name__ if "body" in event else None,
        "callback_event": event  # Log the full event for debugging
    })
    
    # Parse body if it's a string
    body = event["body"]
    if isinstance(body, str):
        body = json.loads(body)
    
    logger.debug("Parsed callback body", extra={
        "body_keys": list(body.keys()) if isinstance(body, dict) else None
    })
    
    callback_query = body["callback_query"]
    user_id = str(callback_query['from']['id'])
    chat_id = str(callback_query['message']['chat']['id'])
    callback_data = callback_query['data']
    
    # Enhanced callback logging
    logger.debug("Processing callback query", extra={
        "user_id": user_id,
        "chat_id": chat_id,
        "callback_data": callback_data,
        "message_id": callback_query['message'].get('message_id'),
        "callback_query_id": callback_query.get('id'),
        "from_user": callback_query['from'],
        "chat_type": callback_query['message']['chat'].get('type'),
        "full_callback_query": callback_query  # Log full callback for debugging
    })
    
    _, meal_type, recipe_id = callback_data.split('_', 2)

    logger.info("Processing recipe selection", extra={
        "user_id": user_id,
        "meal_type": meal_type,
        "recipe_id": recipe_id
    })

    telegram = get_telegram()

    try:
        if not callback_data.startswith('recipe_'):
            raise RecipeSelectionError("Invalid callback data format")

        # Update selection storage
        try:
            RecipeSelectionStorage.update_selection(user_id, meal_type, recipe_id)
            selection = RecipeSelectionStorage.get_selection(user_id)
        except Exception as e:
            raise RecipeSelectionError(f"Failed to update recipe selection: {str(e)}")

        # Get current phase
        table_name = get_table_name()
        logger.debug(f"Using table for recipe selection: {table_name}")
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
        recipe_service.load_recipes_for_meal_planning(phase=phase_type)

        # Determine next meal type to select
        meal_types = ['breakfast', 'lunch', 'dinner', 'snack']
        current_idx = meal_types.index(meal_type)
        
        if current_idx < len(meal_types) - 1:
            # Show next meal selection with phase-specific options
            next_meal = meal_types[current_idx + 1]
            # Get currently selected recipes to exclude
            selected_recipes = RecipeSelectionStorage.get_selection(user_id).get_selected_recipes()
            
            # Get recipes for next meal, excluding already selected ones
            next_recipes = recipe_service.get_recipes_by_meal_type(
                meal_type=next_meal,
                phase=phase_type,
                limit=2,
                exclude_recipe_ids=selected_recipes
            )
            
            # Save shown recipes to history
            for recipe in next_recipes:
                recipe_service.save_recipe_history(
                    user_id=user_id,
                    recipe_id=recipe['id'],
                    meal_type=next_meal,
                    phase=phase_type
                )
                
            keyboard = create_recipe_selection_keyboard(next_recipes, next_meal)
            
            telegram.send_message(
                chat_id=chat_id,
                text=f"{MEAL_EMOJIS[next_meal]} Now, choose your {next_meal}:",
                reply_markup=keyboard
            )
        else:
            # Get selected recipes (excluding skipped meals)
            selections = selection.to_dict()
            selected_recipe_ids = [
                recipe_id for recipe_id in selections.values() 
                if recipe_id != 'skip'
            ]
            
            if not selected_recipe_ids:
                # All meals were skipped
                telegram.send_message(
                    chat_id=chat_id,
                    text="No shopping list generated as all meals were skipped."
                )
            else:
                # Generate shopping list and recipe links together
                selected_recipes = []
                missing_urls = []

                # First collect recipe information
                ingredients = recipe_service.get_multiple_recipe_ingredients(selected_recipe_ids)
                shopping_service = ShoppingListService(recipe_service)
                shopping_list = shopping_service.generate_list(ingredients)
                formatted_list = shopping_service.format_list(shopping_list, recipe_service)

                # Send shopping list
                telegram.send_message(
                    chat_id=chat_id,
                    text=formatted_list
                )

                # Then process recipe links
                for recipe_id in selected_recipe_ids:
                    recipe = recipe_service.get_recipe_by_id(recipe_id)
                    if recipe:
                        if recipe.url:
                            selected_recipes.append((recipe.title, recipe.url))
                        else:
                            missing_urls.append(recipe.title)

                if missing_urls:
                    logger.warning("Some recipes missing URLs", extra={
                        "user_id": user_id,
                        "recipes": missing_urls
                    })

                if selected_recipes:
                    recipe_links_msg = ["📖 Recipe Links\n"]
                    meal_types = ['breakfast', 'lunch', 'dinner', 'snack']
                    selections = selection.to_dict()
                    
                    for meal_type, emoji in zip(meal_types, [MEAL_EMOJIS[m] for m in meal_types]):
                        recipe_id = selections.get(meal_type)
                        if recipe_id and recipe_id != 'skip':
                            recipe = recipe_service.get_recipe_by_id(recipe_id)
                            if recipe and recipe.url:
                                recipe_links_msg.append(f"{emoji} {meal_type.title()}: {recipe.title}\n{recipe.url}")
                    
                    recipe_links_msg.append("\nHappy cooking! 👩‍🍳")
                    
                    # Send recipe links message
                    telegram.send_message(
                        chat_id=chat_id,
                        text="\n\n".join(recipe_links_msg)
                    )

                    logger.info("Sent recipe links", extra={
                        "user_id": user_id,
                        "recipe_count": len(selected_recipes)
                    })
                else:
                    logger.info("No recipe links to send", extra={
                        "user_id": user_id,
                        "selected_recipes": len(selected_recipe_ids),
                        "has_urls": 0
                    })

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"ok": True}),
            "isBase64Encoded": False
        }

    except RecipeSelectionError as e:
        logger.error("Recipe selection error", extra={
            "user_id": user_id,
            "meal_type": meal_type,
            "recipe_id": recipe_id,
            "error": str(e),
            "error_type": "RECIPE_SELECTION_ERROR",
            "callback_event": event  # Log raw event for debugging
        })
        telegram.send_message(
            chat_id=chat_id,
            text=f"⚠️ Error selecting recipe: {str(e)}"
        )
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "ok": False,
                "error_code": "RECIPE_SELECTION_ERROR",
                "description": str(e)
            }),
            "isBase64Encoded": False
        }
    except RecipeNotFoundError as e:
        logger.error("Required recipes not found", extra={
            "user_id": user_id,
            "meal_type": meal_type,
            "phase_type": phase_type if 'phase_type' in locals() else None,
            "error": str(e),
            "error_type": "RECIPE_NOT_FOUND",
            "callback_event": event  # Log raw event for debugging
        })
        telegram.send_message(
            chat_id=chat_id,
            text=f"⚠️ Could not find required recipes: {str(e)}"
        )
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "ok": False,
                "error_code": "RECIPE_NOT_FOUND",
                "description": str(e)
            }),
            "isBase64Encoded": False
        }
    except Exception as e:
        logger.exception(
            "Unexpected error in recipe selection",
            extra={
            "user_id": user_id,
            "meal_type": meal_type,
            "recipe_id": recipe_id,
            "error_type": e.__class__.__name__,
            "callback_event": event  # Log raw event for debugging
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
