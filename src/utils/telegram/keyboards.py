"""
Keyboard layout definitions for Telegram bot interactions.
"""
from typing import List, Dict, Any, Union, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.services.week_analysis import PhaseDistribution

def to_dict(markup: InlineKeyboardMarkup) -> Dict[str, Any]:
    """
    Convert InlineKeyboardMarkup to a dictionary format that Telegram API expects.
    
    Args:
        markup: InlineKeyboardMarkup object
        
    Returns:
        Dictionary representation of the keyboard markup
    """
    return {
        "inline_keyboard": [
            [
                {"text": btn.text, "callback_data": btn.callback_data}
                for btn in row
            ]
            for row in markup.inline_keyboard
        ]
    }

def create_inline_keyboard(buttons: List[List[Dict[str, str]]]) -> InlineKeyboardMarkup:
    """
    Create an inline keyboard from a list of button definitions.
    
    Args:
        buttons: List of button rows, where each button is a dict with 'text' and 'callback_data'
        
    Returns:
        InlineKeyboardMarkup with the specified buttons
    """
    keyboard = []
    for row in buttons:
        keyboard_row = []
        for button in row:
            keyboard_row.append(
                InlineKeyboardButton(
                    text=button['text'],
                    callback_data=button['callback_data']
                )
            )
        keyboard.append(keyboard_row)
    markup = InlineKeyboardMarkup(keyboard)
    return to_dict(markup)

def create_rating_keyboard() -> Dict[str, Any]:
    """
    Create an inline keyboard for rating recipes.
    
    Returns:
        InlineKeyboardMarkup with rating buttons (1-5)
    """
    buttons = [[{
        'text': str(i),
        'callback_data': f'rate_{i}'
    } for i in range(1, 6)]]
    return create_inline_keyboard(buttons)

# Map of meal types to emojis
MEAL_EMOJIS = {
    'breakfast': '🥞',
    'lunch': '🥗',
    'salad': '🥬',
    'dinner': '🍽️',
    'snack': '🍿'
}

def create_recipe_selection_keyboard(
    recipes: List[Dict[str, Any]],
    meal_type: str,
    show_multi_option: bool = False,
    week_analysis: Optional[Dict[str, PhaseDistribution]] = None,
    current_phase: Optional[str] = None,
    selected_recipe_ids: List[str] = None,
    max_recipes_per_meal: int = 2
) -> Dict[str, Any]:
    """
    Create an inline keyboard for recipe selection (legacy function).
    Maintained for backward compatibility with tests.

    Args:
        recipes: List of recipe dictionaries
        meal_type: Type of meal (breakfast, lunch, dinner, snack)
        show_multi_option: Whether to show multi-select option
        week_analysis: Optional phase distribution analysis
        
    Returns:
        Dict[str, Any]: Keyboard markup dictionary
    """
    selected_recipe_ids = selected_recipe_ids or []
    buttons = []
    
    if show_multi_option and week_analysis:
        # Sort phases by percentage
        sorted_phases = sorted(
            week_analysis.items(),
            key=lambda x: x[1].percentage,
            reverse=True
        )
        
        # Add multi-select option at top
        phase_info = [
            f"{p.title()} {'⚡' if p == 'power' else '🌱'}: {round(dist.percentage * 100)}%"
            for p, dist in sorted_phases
        ]
        buttons.append([InlineKeyboardButton(
            f"Select from multiple phases ({', '.join(phase_info)})",
            callback_data=f"multi_select_{meal_type}"
        )])
        buttons.append([])  # Spacer
        
        # Process all phases in order of percentage
        for phase, dist in sorted_phases:
                phase_recipes = [r for r in recipes if r.get('phase') == phase]
                if phase_recipes:
                    # Add phase header
                    emoji = "⚡" if phase == 'power' else "🌱"  # Set emoji based on phase
                    buttons.append([InlineKeyboardButton(
                        f"{emoji} {phase.title()} Phase Recipes ({int(dist.percentage * 100)}%)",
                        callback_data=f"header_{phase}"
                    )])
                    
                    # Add recipes for this phase (strictly limited)
                    for recipe in phase_recipes[:max_recipes_per_meal]:
                        phase_emoji = "⚡" if recipe.get('phase') == 'power' else "🌱"
                        is_selected = recipe['id'] in selected_recipe_ids
                        checkbox = "✅" if is_selected else "⭕"
                        buttons.append([InlineKeyboardButton(
                            f"{phase_emoji} {checkbox} {recipe['title']} ({recipe['prep_time']} min)",
                            callback_data=f"recipe_{meal_type}_{recipe['id']}_{phase}"
                        )])
                    
    else:
        # Standard single-phase layout (strictly limited)
        for recipe in recipes[:max_recipes_per_meal]:
            phase_emoji = "⚡" if recipe.get('phase') == 'power' else "🌱" if recipe.get('phase') == 'nurture' else "✨"
            # Only show checkbox in multi-select mode
            button_text = f"{phase_emoji} {recipe['title']} ({recipe['prep_time']} min)"
            buttons.append([InlineKeyboardButton(
                button_text,
                callback_data=f"recipe_{meal_type}_{recipe['id']}_{recipe.get('phase', 'none')}"
            )])
    
    # Add spacer
    buttons.append([])
    
    # Add skip button
    buttons.append([InlineKeyboardButton(
        "Skip this meal 🚫",
        callback_data=f"recipe_{meal_type}_skip"
    )])
    
    markup = InlineKeyboardMarkup(buttons)
    return to_dict(markup)

def create_multi_recipe_selection_keyboard(
    recipes_data: Union[Dict[str, List[Dict[str, Any]]], Dict[str, Dict[str, List[Dict[str, Any]]]]],
    selected_recipe_ids: List[str] = None,
    current_phase: Optional[str] = None,
    max_recipes_per_meal: int = 2
) -> Dict[str, Any]:
    """
    Create inline keyboard for multi-recipe selection with all meals shown at once.
    Supports both single-phase and multi-phase recipe data structures.
    
    Args:
        recipes_data: Either:
            - Dict[meal_type, recipe_list] for single phase
            - Dict[phase, Dict[meal_type, recipe_list]] for multi-phase
        selected_recipe_ids: List of currently selected recipe IDs
        current_phase: Optional current phase to highlight
        
    Returns:
        InlineKeyboardMarkup with all recipes grouped by meal type and phase
    """
    selected_recipe_ids = selected_recipe_ids or []
    buttons = []
    
    meal_order = ['breakfast', 'lunch', 'salad', 'dinner', 'snack']
    total_selected = len(selected_recipe_ids)
    
    # Determine if we have multi-phase data
    is_multi_phase = any(isinstance(v, dict) for v in recipes_data.values())
    
    if is_multi_phase:
        # Multi-phase structure
        phase_order = ['power', 'nurture', 'manifestation']
        for meal_type in meal_order:
            recipes_in_meal = False
            # Add meal type header
            emoji = MEAL_EMOJIS.get(meal_type, '🍽️')
            buttons.append([InlineKeyboardButton(
                f"{emoji} {meal_type.upper()}",
                callback_data=f"header_{meal_type}"
            )])
            
            # Add recipes for each phase
            for phase in phase_order:
                phase_recipes = recipes_data.get(phase, {}).get(meal_type, [])
                if phase_recipes:
                    recipes_in_meal = True
                    # Add phase subheader
                    phase_emoji = "⚡" if phase == 'power' else "🌱" if phase == 'nurture' else "✨"
                    buttons.append([InlineKeyboardButton(
                        f"{phase_emoji} {phase.title()} Phase",
                        callback_data=f"header_{phase}"
                    )])
                    
                    # Add recipes for this phase (strictly limited)
                    for recipe in phase_recipes[:max_recipes_per_meal]:
                        is_selected = recipe['id'] in selected_recipe_ids
                        checkbox = "✅" if is_selected else "⭕"
                        # Add multi-selection indicator and callback
                        button_text = f"{phase_emoji} {checkbox} {recipe['title']} ({recipe['prep_time']} min)"
                        buttons.append([InlineKeyboardButton(
                            button_text,
                            callback_data=f"recipe_{meal_type}_{recipe['id']}_{phase}"
                        )])
            
            if recipes_in_meal:
                buttons.append([])  # Add spacing between meal types
    else:
        # Single phase structure (original behavior)
        for meal_type in meal_order:
            recipes = recipes_data.get(meal_type, [])
            if not recipes:
                continue
                
            # Add meal type header
            emoji = MEAL_EMOJIS.get(meal_type, '🍽️')
            buttons.append([InlineKeyboardButton(
                f"{emoji} {meal_type.upper()}",
                callback_data=f"header_{meal_type}"
            )])
            
            # Sort recipes to show power phase first
            sorted_recipes = sorted(recipes, key=lambda r: r.get('phase') != 'power')
            
            # Add recipes (strictly limited)
            for recipe in sorted_recipes[:max_recipes_per_meal]:
                is_selected = recipe['id'] in selected_recipe_ids
                checkbox = "✅" if is_selected else "⭕"
                if recipe.get('phase'):
                    phase_emoji = "⚡" if recipe.get('phase') == 'power' else "🌱"
                    button_text = f"{phase_emoji} {checkbox} {recipe['title']} ({recipe['prep_time']} min)"
                else:
                    button_text = f"{checkbox} {recipe['title']} ({recipe['prep_time']} min)"
                
                buttons.append([InlineKeyboardButton(
                    button_text,
                    callback_data=f"recipe_{meal_type}_{recipe['id']}_{recipe.get('phase', 'none')}"
                )])
            
            # Add spacing between meal types
            buttons.append([])
    
    # (Removed) Generate Shopping List button to simplify UX in favor of single 'Done Selecting' action
    
    # Add utility buttons with multi-selection indicators
    utility_row = []
    if total_selected > 0:
        utility_row.append(InlineKeyboardButton(
            "🔄 Clear All Selections",
            callback_data="clear_selections"  # Changed to be more explicit
        ))
        utility_row.append(InlineKeyboardButton(
            "✅ Done Selecting",  # Added done button for multi-selection
            callback_data="done_selecting"
        ))
    
    # Only show select all if there are recipes to select
    if is_multi_phase:
        total_recipes = sum(
            len(phase_data.get(meal_type, []))
            for phase in ['power', 'nurture', 'manifestation']
            for meal_type in meal_order
            for phase_data in [recipes_data.get(phase, {})]
        )
    else:
        total_recipes = sum(len(recipes) for recipes in recipes_data.values())
    
    if total_recipes > 0 and total_selected < total_recipes:
        utility_row.append(InlineKeyboardButton(
            "✨ Select All Available",
            callback_data="select_all_available"  # Changed to be more explicit
        ))
    
    if utility_row:
        buttons.append(utility_row)
    
    markup = InlineKeyboardMarkup(buttons)
    return to_dict(markup)
