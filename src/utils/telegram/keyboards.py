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

def create_recipe_selection_keyboard(
    recipes: List[Dict[str, Any]],
    meal_type: str,
    show_multi_option: bool = False,
    week_analysis: Optional[Dict[str, PhaseDistribution]] = None
) -> Dict[str, Any]:
    """
    Create inline keyboard for recipe selection with phase labels.
    
    Args:
        recipes: List of recipe dictionaries containing title, prep_time, and phase
        meal_type: Type of meal (breakfast, lunch, dinner, snack)
        show_multi_option: Whether to show option for selecting multiple phase-specific recipes
        week_analysis: Optional week analysis to show phase distribution
        
    Returns:
        InlineKeyboardMarkup with recipe options and skip option
    """
    buttons = []
    phase_emojis = {
        "power": "⚡",
        "nurture": "🌱",
        "manifestation": "✨"
    }
    
    # Add week analysis if provided
    if week_analysis and show_multi_option:
        multi_select_callback = f"multi_select_{meal_type}"
        distribution = [
            f"{phase.title()} {phase_emojis.get(phase, '')}: {data.percentage:.0%}"
            for phase, data in week_analysis.items()
        ]
        buttons.append([
            InlineKeyboardButton(
                f"📊 Select recipes for multiple phases ({', '.join(distribution)})",
                callback_data=multi_select_callback
            )
        ])
        buttons.append([])  # Empty row for spacing

    # Group recipes by phase
    recipes_by_phase: Dict[str, List[Dict]] = {}
    for recipe in recipes:
        phase = recipe.get('phase', 'unknown').lower()
        if phase not in recipes_by_phase:
            recipes_by_phase[phase] = []
        recipes_by_phase[phase].append(recipe)

    # Add recipes grouped by phase
    for phase, phase_recipes in sorted(recipes_by_phase.items()):
        phase_emoji = phase_emojis.get(phase, "")
        if len(recipes_by_phase) > 1:  # Only add phase headers if multiple phases
            buttons.append([InlineKeyboardButton(
                f"{phase_emoji} {phase.title()} Phase Recipes",
                callback_data=f"phase_header_{phase}"  # Non-functional button
            )])
        
        for recipe in phase_recipes:
            callback_data = f"recipe_{meal_type}_{recipe['id']}"
            if show_multi_option:
                callback_data = f"recipe_{meal_type}_{recipe['id']}_{phase}"
            
            button_text = f"{recipe['title']} ({recipe['prep_time']} min)"
            if len(recipes_by_phase) == 1:  # Add phase emoji if not grouped
                button_text = f"{phase_emoji} {button_text}"
                
            buttons.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    # Add skip meal option
    if buttons:  # Add spacer before skip button if we have other buttons
        buttons.append([])
    skip_callback_data = f"recipe_{meal_type}_skip"
    skip_button = [InlineKeyboardButton("Skip this meal 🚫", callback_data=skip_callback_data)]
    buttons.append(skip_button)
    
    markup = InlineKeyboardMarkup(buttons)
    return to_dict(markup)
