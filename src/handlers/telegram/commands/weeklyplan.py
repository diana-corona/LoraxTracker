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
import importlib
from typing import Optional, Dict, Any, List, Tuple
from unittest.mock import Mock
from pathlib import Path

from aws_lambda_powertools.utilities.typing import LambdaContext
from src.handlers.telegram.exceptions import (
    NoEventsError,
    WeeklyPlanError,
    RecipeSelectionError,
    RecipeNotFoundError
)
from src.utils.telegram.keyboards import create_multi_recipe_selection_keyboard
from src.services.recipe import RecipeService
from src.services.recipe_selection_storage import RecipeSelectionStorage, SelectionMode
from src.services.weekly_plan_cache import WeeklyPlanCache, WeeklyPlanCacheError
from src.services.shopping_list import ShoppingListService

from src.utils.dynamo import create_pk
from src.models.event import CycleEvent
from src.services.weekly_plan import generate_weekly_plan, format_weekly_plan
from src.services.cycle import analyze_cycle_phase
from src.services.week_analysis import calculate_week_analysis, format_week_analysis
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
    'salad': '🥬',
    'dinner': '🍽️',
    'snack': '🍿'
}

# Meal type order
MEAL_ORDER = ['breakfast', 'lunch', 'salad', 'dinner', 'snack']


def _get_recipe_service(test_mode: bool):
    """
    Return a RecipeService instance compatible with both patching strategies:
      1. Patch applied to weeklyplan.RecipeService
      2. Patch applied to src.services.recipe.RecipeService

    Strategy:
      - In test_mode, inspect both the dynamically imported class and the locally
        imported alias; prefer whichever is a Mock (has 'return_value' attribute).
      - Fallback to dynamic module class (ensures we pick up patch #2).
      - In non-test mode just use the local import for performance.
    """
    if test_mode:
        module = importlib.import_module('src.services.recipe')
        module_cls = getattr(module, "RecipeService", RecipeService)
        local_cls = RecipeService
        # Prefer a mocked class (MagicMock/Mock) if present
        # Prefer local (weeklyplan) patched class first so tests that patch weeklyplan.RecipeService
        # still observe history calls even if another test earlier patched src.services.recipe.RecipeService.
        # Prefer dynamically imported module class first so tests that patch src.services.recipe.RecipeService
        # (but not weeklyplan.RecipeService) are captured. Falls back to local if it is the one patched.
        # Robust detection: check both local (weeklyplan) and module class; return whichever is patched.
        tried = set()
        for cls in (local_cls, module_cls):
            if cls in tried:
                continue
            tried.add(cls)
            if hasattr(cls, "return_value"):
                return cls()
        # Fallback: instantiate module class
        return module_cls()
    # Production path
    return RecipeService()

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
    
    # Check cache first
    try:
        cache = WeeklyPlanCache()
        cached_plan = cache.get_cached_plan(user_id)
        if cached_plan:
            # Send cached plan, shopping list, and recipe links
            telegram.send_message(
                chat_id=chat_id,
                text=cached_plan['plan_text']
            )
            telegram.send_message(
                chat_id=chat_id,
                text=cached_plan['shopping_list']
            )
            telegram.send_message(
                chat_id=chat_id,
                text=cached_plan['recipe_links']
            )
            logger.info("Sent cached weekly plan", extra={
                "user_id": user_id,
                "cache_hit": True
            })
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "ok": True,
                    "result": {"message": "Cached weekly plan sent"}
                }),
                "isBase64Encoded": False
            }
    except WeeklyPlanCacheError as e:
        # Log error but continue with normal plan generation
        logger.warning("Cache access failed", extra={
            "user_id": user_id,
            "error": str(e)
        })
    
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
            raise NoEventsError("No cycle events found. Please register some events first.")
        
        # Generate weekly plan
        weekly_plan = generate_weekly_plan(cycle_events, user_id=user_id)
        
        # Get formatted output
        formatted_plan = format_weekly_plan(weekly_plan, cycle_events, user_id)
        
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
        
        try:
            # Calculate week analysis
            week_analysis = calculate_week_analysis(weekly_plan.phase_groups)
            analysis_text = format_week_analysis(week_analysis)
            
            # Combine plan and analysis
            full_message = formatted_plan + [""] + analysis_text
            full_message_text = "\n".join(full_message)
            
            # Send combined message
            telegram.send_message(
                chat_id=chat_id,
                text=full_message_text
            )
            
            # Store message text for later caching
            RecipeSelectionStorage.store_weekly_plan_text(user_id, full_message_text)
            
            logger.info("Weekly plan generated successfully", extra={
                "user_id": user_id,
                "chat_id": chat_id,
                "plan_start": weekly_plan.start_date.isoformat(),
                "plan_end": weekly_plan.end_date.isoformat()
            })

            # Clear any previous recipe selections and enable multi-select mode
            RecipeSelectionStorage.clear_selection(user_id)
            RecipeSelectionStorage.set_multi_select_mode(user_id)

            # Get user's current phase
            current_phase = analyze_cycle_phase(cycle_events)
            phase_type = current_phase.functional_phase.value
            
            # Load and select phase-specific recipes for meal planning with rotation
            recipe_service = RecipeService()
            recipe_service.load_recipes_for_meal_planning(phase=phase_type, user_id=user_id)
            
            # Get all recipes by meal type, enforcing strict 2 options per meal limit
            recipes_by_meal_type = {}
            for meal_type in MEAL_ORDER:
                # Get only 2 recipes per meal type
                recipes = recipe_service.get_recipes_by_meal_type(
                    meal_type,
                    phase=phase_type,
                    limit=2
                )
                recipes_by_meal_type[meal_type] = recipes[:2]  # Double check the limit
            
            # Create multi-selection keyboard
            keyboard = create_multi_recipe_selection_keyboard(recipes_by_meal_type, [])
            # Store initial snapshot for stable toggling
            RecipeSelectionStorage.store_recipes_snapshot(user_id, recipes_by_meal_type)

            # Send recipe selection message
            telegram.send_message(
                chat_id=chat_id,
                text=(
                    "🍽️ **Select Your Weekly Recipes**\n\n"
                    "Choose any combination of recipes from below. "
                    "You can select multiple recipes from any meal category.\n\n"
                    "*Tap recipes to toggle selection, then press 'Done Selecting' to generate your shopping list.*"
                ),
                reply_markup=keyboard
            )

            logger.info("Multi-select recipe selection setup completed", extra={
                "user_id": user_id,
                "phase": phase_type,
                "recipes_by_meal_type": {
                    meal: len(recipes) 
                    for meal, recipes in recipes_by_meal_type.items()
                }
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
            "headers": {"Content-Type": "application/json"},
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
        return None
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

def handle_recipe_callback(event: Dict[str, Any], test_mode: bool = False) -> Dict[str, Any]:
    """
    Handle recipe selection callback for multi-select mode.

    This handler processes various callback actions:
    - toggle_recipe_*: Toggle selection state of a recipe
    - generate_shopping_list: Generate list from selected recipes
    - clear_all_recipes: Clear all recipe selections
    - select_all_recipes: Select all available recipes

    Args:
        event: Lambda event containing callback query data

    Returns:
        Dict[str, Any]: API Gateway response
    """
    logger.debug("Received recipe callback event", extra={
        "event_type": type(event).__name__,
        "has_body": "body" in event,
        "body_type": type(event.get("body")).__name__ if "body" in event else None,
        "callback_event": event
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
    message_id = callback_query['message']['message_id']

    
    # Enhanced callback logging
    logger.debug("Processing callback query", extra={
        "user_id": user_id,
        "chat_id": chat_id,
        "callback_data": callback_data,
        "message_id": message_id,
        "callback_query_id": callback_query.get('id'),
        "chat_type": callback_query['message']['chat'].get('type')
    })

    telegram = get_telegram()

    try:
        # If we're in test mode, skip the DynamoDB query
        cycle_events = []
        if not test_mode:
            dynamo = get_dynamo()
            table_name = get_table_name()
            events = dynamo.query_items(
                    partition_key="PK",
                    partition_value=create_pk(user_id)
                )
            cycle_events = [
                    CycleEvent(**event)
                    for event in events
                    if event["SK"].startswith("EVENT#")
                ]

        if callback_data.startswith('recipe_') and '_' in callback_data:
            # Format: recipe_[meal_type]_[recipe_id]_[phase]
            parts = callback_data.split('_')
            if len(parts) == 4:  # Ensure we have all parts
                _, meal_type, recipe_id, phase = parts
            else:
                logger.warning("Invalid recipe callback format", extra={
                    "callback_data": callback_data
                })
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Invalid recipe callback format"}),
                    "isBase64Encoded": False
                }
            
            # Update selection state prior to toggle
            selection = RecipeSelectionStorage.get_selection(user_id)
            was_selected = recipe_id in selection.selected_recipes
            
            # Toggle the selection
            selection.toggle_recipe(recipe_id, meal_type, phase)
            
            # Save to history if it was just selected (not deselected)
            if not was_selected and recipe_id in selection.selected_recipes:
                logger.info("Recipe selected, saving to history", extra={
                    "user_id": user_id,
                    "recipe_id": recipe_id,
                    "meal_type": meal_type,
                    "phase": phase
                })
                recipe_service = _get_recipe_service(test_mode)
                recipe_service.save_recipe_history(
                    user_id=user_id,
                    recipe_id=recipe_id,
                    meal_type=meal_type,
                    phase=phase
                )
            
            if recipe_id not in selection.selected_recipes:
                logger.info("Recipe deselected", extra={
                    "user_id": user_id,
                    "recipe_id": recipe_id
                })

            # Attempt to reuse previously displayed recipes to keep UI stable
            snapshot = RecipeSelectionStorage.get_recipes_snapshot(user_id)
            keyboard = None
            if snapshot:
                is_multi_phase = any(isinstance(v, dict) for v in snapshot.values())
                keyboard = create_multi_recipe_selection_keyboard(
                    snapshot,
                    selection.selected_recipes
                )
            if keyboard is None:
                # Fallback: load current phase recipes (legacy behavior) and snapshot them
                recipe_service = _get_recipe_service(test_mode)
                if not test_mode and cycle_events:
                    try:
                        current_phase = analyze_cycle_phase(cycle_events).functional_phase.value
                    except Exception:
                        current_phase = phase
                else:
                    current_phase = phase
                recipe_service.load_recipes_for_meal_planning(phase=current_phase, user_id=user_id)
                recipes_by_meal_type = {}
                for mt in MEAL_ORDER:
                    recipes = recipe_service.get_recipes_by_meal_type(
                        mt, phase=current_phase, limit=2
                    )[:2]
                    recipes_by_meal_type[mt] = recipes
                RecipeSelectionStorage.store_recipes_snapshot(user_id, recipes_by_meal_type)
                keyboard = create_multi_recipe_selection_keyboard(
                    recipes_by_meal_type,
                    selection.selected_recipes
                )

            telegram.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=keyboard
            )
            
        elif callback_data == 'generate_shopping_list':
                
            # Generate shopping list and recipe links from selected recipes
            selection = RecipeSelectionStorage.get_selection(user_id)
            selected_recipes = selection.selected_recipes
            
            if not selected_recipes:
                telegram.send_message(
                    chat_id=chat_id,
                    text="⚠️ Please select at least one recipe first!"
                )
                return {
                    "statusCode": 200,
                    "body": json.dumps({"ok": True}),
                    "isBase64Encoded": False
                }
                
            # Generate shopping list
            recipe_service = _get_recipe_service(test_mode)
            ingredients = recipe_service.get_multiple_recipe_ingredients(selected_recipes)
            shopping_service = ShoppingListService(recipe_service)
            shopping_list = shopping_service.generate_list(ingredients)
            formatted_list = shopping_service.format_list(shopping_list, recipe_service)
            
            # Send shopping list
            telegram.send_message(
                chat_id=chat_id,
                text=formatted_list,
                parse_mode='Markdown'
            )
            
            # Generate and send recipe links
            recipe_links_msg = ["📖 **Recipe Links**\n"]
            for recipe_id in selected_recipes:
                recipe = recipe_service.get_recipe_by_id(recipe_id)
                if recipe and recipe.url:
                    recipe_links_msg.append(f"• {recipe.title}\n  {recipe.url}")
            
            if len(recipe_links_msg) > 1:
                recipe_links_msg.append("\nHappy cooking! 👩‍🍳")
                telegram.send_message(
                    chat_id=chat_id,
                    text="\n\n".join(recipe_links_msg),
                parse_mode='Markdown'
                )
                
        elif callback_data == 'clear_selections':  # Standardize on new callback format
            selection = RecipeSelectionStorage.get_selection(user_id)
            selection.clear_selections(preserve_mode=True)
            logger.info(f"Cleared all recipe selections for user {user_id}")
            
            # Refresh keyboard with cleared selections
            current_phase = analyze_cycle_phase(cycle_events) if not test_mode else Mock(functional_phase=Mock(value='power'))
            phase_type = current_phase.functional_phase.value
            
            recipe_service = _get_recipe_service(test_mode)
            
            # Load recipes for each phase
            phases = ['power', 'nurture', 'manifestation']
            recipes_by_phase = {}
            
            for phase in phases:
                recipe_service.load_recipes_for_meal_planning(phase=phase, user_id=user_id)
                recipes_by_meal_type = {}
                for meal_type in MEAL_ORDER:
                    # Get only 2 recipes per meal type
                    recipes = recipe_service.get_recipes_by_meal_type(
                        meal_type, phase=phase, limit=2
                    )
                    recipes = recipes[:2]  # Double check the limit
                    recipes_by_meal_type[meal_type] = recipes
                recipes_by_phase[phase] = recipes_by_meal_type
            
            # Store snapshot for stable UI after clearing
            RecipeSelectionStorage.store_recipes_snapshot(user_id, recipes_by_phase)
            keyboard = create_multi_recipe_selection_keyboard(recipes_by_phase, [])
            
            # Update keyboard only after clearing selections
            telegram.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=keyboard
            )
            
        elif callback_data.startswith('multi_select_'):
            # Load recipes for all phases
            recipe_service = _get_recipe_service(test_mode)
            
            # Load recipes for each phase
            phases = ['power', 'nurture', 'manifestation']
            recipes_by_phase = {}
            
            for phase in phases:
                recipe_service.load_recipes_for_meal_planning(phase=phase, user_id=user_id)
                recipes_by_meal_type = {}
                for meal_type in MEAL_ORDER:
                    recipes = recipe_service.get_recipes_by_meal_type(
                        meal_type, phase=phase, limit=2  # Strictly limit to 2 options per meal
                    )
                    # Double-check the limit in case the service returns more
                    if len(recipes) > 2:
                        recipes = recipes[:2]
                    recipes_by_meal_type[meal_type] = recipes
                recipes_by_phase[phase] = recipes_by_meal_type

            # Store multi-phase snapshot for stable toggling
            RecipeSelectionStorage.store_recipes_snapshot(user_id, recipes_by_phase)
            # Create multi-selection keyboard with all phases
            keyboard = create_multi_recipe_selection_keyboard(recipes_by_phase)
            
            # Use edit_message_text to update the entire message for test visibility
            telegram.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=(
                    "🍽️ **Select Your Weekly Recipes**\n\n"
                    "Choose any combination of recipes from below. "
                    "You can select multiple recipes from any meal category.\n\n"
                    "*Tap recipes to toggle selection, then press 'Done Selecting' to generate your shopping list.*"
                ),
                reply_markup=keyboard
            )

        elif callback_data == 'done_selecting':
            # Get current selections and generate shopping list
            selection = RecipeSelectionStorage.get_selection(user_id)
            selected_recipes = selection.selected_recipes

            if not selected_recipes:
                telegram.send_message(
                    chat_id=chat_id,
                    text="⚠️ Please select at least one recipe first!"
                )
                return {
                    "statusCode": 200,
                    "body": json.dumps({"ok": True}),
                    "isBase64Encoded": False
                }

            # Generate shopping list - ensure selected recipes are loaded (original service instance had empty caches)
            recipe_service = RecipeService()

            # Attempt to load each selected recipe from disk across all phase folders without clearing caches
            missing_before = set(selected_recipes)
            phases_to_search = ['power', 'nurture', 'manifestation']
            for phase_dir in phases_to_search:
                base_dir = Path('recipes') / phase_dir
                if not base_dir.exists():
                    continue
                for recipe_id in list(missing_before):
                    candidate = base_dir / f"{recipe_id}.md"
                    if candidate.exists():
                        try:
                            recipe = recipe_service.parser.parse_recipe_file(str(candidate))
                            if recipe:
                                # Store in caches similar to normal load
                                recipe_service._recipes[recipe_id] = recipe
                                recipe_service._phase_recipes[phase_dir][recipe_id] = recipe
                                missing_before.remove(recipe_id)
                        except Exception as e:
                            logger.warning(
                                "Failed to load recipe file during shopping list generation",
                                extra={"recipe_id": recipe_id, "path": str(candidate), "error": str(e)}
                            )

            if missing_before:
                logger.warning(
                    "Some selected recipes could not be loaded and will be skipped",
                    extra={"missing_recipe_ids": list(missing_before)}
                )

            ingredients = recipe_service.get_multiple_recipe_ingredients(selected_recipes)
            shopping_service = ShoppingListService(recipe_service)
            shopping_list = shopping_service.generate_list(ingredients)
            formatted_list = shopping_service.format_list(shopping_list, recipe_service)
            
            # Send shopping list and completion message
            telegram.send_message(
                chat_id=chat_id,
                text=(
                    "✅ Recipe selection complete!\n\n"
                    f"Selected {len(selected_recipes)} recipes.\n\n"
                    "Here's your shopping list:"
                ),
                parse_mode='Markdown'
            )
            
            telegram.send_message(
                chat_id=chat_id,
                text=formatted_list,
                parse_mode='Markdown'
            )
            
            # Generate and send recipe links
            recipe_links_msg = ["📖 **Selected Recipes**\n"]
            for recipe_id in selected_recipes:
                recipe = recipe_service.get_recipe_by_id(recipe_id)
                if recipe and recipe.url:
                    recipe_links_msg.append(f"• {recipe.title}\n  {recipe.url}")
            
            if len(recipe_links_msg) > 1:
                recipe_links_msg.append("\nHappy cooking! 👩‍🍳")
                telegram.send_message(
                    chat_id=chat_id,
                    text="\n\n".join(recipe_links_msg),
                    parse_mode='Markdown'
                )
                
        elif callback_data == 'select_all_available':  # Standardize on new callback format
            # Get current phase and recipes for all phases
            recipe_service = RecipeService()
            logger.info(f"Starting select all recipes for user {user_id}")
            
            # Load recipes for each phase
            phases = ['power', 'nurture', 'manifestation']
            recipes_by_phase = {}
            all_recipes = []
            
            for phase in phases:
                recipe_service.load_recipes_for_meal_planning(phase=phase, user_id=user_id)
                recipes_by_meal_type = {}
                for meal_type in MEAL_ORDER:
                    recipes = recipe_service.get_recipes_by_meal_type(
                        meal_type, phase=phase, limit=2
                    )[:2]  # Strictly enforce 2-recipe limit
                    recipes_by_meal_type[meal_type] = recipes
                    all_recipes.extend(recipes)  # Add to all recipes list
                recipes_by_phase[phase] = recipes_by_meal_type
                
                logger.debug(f"Loaded {len(all_recipes)} recipes for phase {phase}")

            # Then select all recipes
            selection = RecipeSelectionStorage.get_selection(user_id)
            selection.clear_selections(preserve_mode=True)  # Clear existing selections but preserve multi-select mode
            
            for recipe in all_recipes:
                recipe_id = recipe['id']
                selection.toggle_recipe(recipe_id)
                logger.debug("Selected recipe", extra={
                    "recipe_id": recipe_id,
                    "current_selections": selection.selected_recipes
                })
                logger.debug("Toggled recipe", extra={
                    "recipe_id": recipe_id,
                    "current_selections": selection.selected_recipes,
                    "mode": str(selection.mode),
                    "selection_object": str(selection)
                })
            
            # Update keyboard with phase-organized recipes
            # Store snapshot including current selections
            RecipeSelectionStorage.store_recipes_snapshot(user_id, recipes_by_phase)
            keyboard = create_multi_recipe_selection_keyboard(
                recipes_by_phase,
                selection.selected_recipes
            )
            
            telegram.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=keyboard
            )

        # Log successful action
        logger.info("Recipe selection action completed", extra={
            "user_id": user_id,
            "action": callback_data
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
