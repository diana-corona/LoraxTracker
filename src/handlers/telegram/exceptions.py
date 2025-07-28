"""
Custom exceptions for Telegram handlers.
"""

class TelegramHandlerError(Exception):
    """Base exception for Telegram handler errors."""
    pass

class RecipeSelectionError(TelegramHandlerError):
    """Raised when there's an error in recipe selection process."""
    pass

class WeeklyPlanError(TelegramHandlerError):
    """Raised when there's an error generating weekly plan."""
    pass

class NoEventsError(WeeklyPlanError):
    """Raised when no cycle events are found for the user."""
    pass

class RecipeNotFoundError(RecipeSelectionError):
    """Raised when required recipes are not found."""
    pass
