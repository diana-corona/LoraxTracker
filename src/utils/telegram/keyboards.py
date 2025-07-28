"""
Keyboard layout definitions for Telegram bot interactions.
"""
from typing import List, Dict, Any, Union
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

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

def create_recipe_selection_keyboard(recipes: List[Dict[str, Any]], meal_type: str) -> Dict[str, Any]:
    """
    Create inline keyboard for recipe selection.
    
    Args:
        recipes: List of recipe dictionaries containing title and prep_time
        meal_type: Type of meal (breakfast, lunch, dinner, snack)
        
    Returns:
        InlineKeyboardMarkup with recipe options
    """
    buttons = []
    for recipe in recipes:
        callback_data = f"recipe_{meal_type}_{recipe['id']}"
        button_text = f"{recipe['title']} ({recipe['prep_time']} min)"
        buttons.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    markup = InlineKeyboardMarkup(buttons)
    return to_dict(markup)
