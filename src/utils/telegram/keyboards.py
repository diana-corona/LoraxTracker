"""
Keyboard layout definitions for Telegram bot interactions.
"""
from typing import List, Dict, Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def create_recipe_selection_keyboard(recipes: List[Dict[str, Any]], meal_type: str) -> InlineKeyboardMarkup:
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
    return InlineKeyboardMarkup(buttons)
