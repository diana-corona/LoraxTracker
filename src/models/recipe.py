"""
Recipe data models for meal plan integration.

This module provides data structures for representing recipes, meal recommendations,
and recipe history within the hormonal cycle tracking system.
"""
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

from src.models.phase import FunctionalPhaseType


@dataclass
class Recipe:
    """
    Individual recipe model.
    
    Represents a single recipe with all its components including ingredients,
    instructions, nutritional phase alignment, and metadata.
    
    Attributes:
        title: Recipe name/title
        phase: Hormonal phase this recipe is optimal for (populated during categorization)
        prep_time: Preparation time in minutes
        tags: List of meal types (breakfast, lunch, dinner, snack)
        ingredients: List of recipe ingredients with amounts
        instructions: List of cooking steps
        notes: Optional additional notes or tips
        url: Optional link to source or additional information
        file_path: Path to the original markdown file
    """
    title: str
    phase: Optional[str]
    prep_time: int
    tags: List[str]
    ingredients: List[str]
    instructions: List[str]
    notes: Optional[str]
    url: Optional[str]
    file_path: str


@dataclass
class MealRecommendation:
    """
    Enhanced meal recommendation with specific recipes.
    
    Represents a meal suggestion (breakfast, lunch, dinner, snack) with
    one or more recipe options and total preparation time.
    
    Attributes:
        meal_type: Type of meal (breakfast, lunch, dinner, snack)
        recipes: List of recipe options for this meal
        prep_time_total: Total preparation time for all recipes in minutes
    """
    meal_type: str
    recipes: List[Recipe]
    prep_time_total: int


@dataclass
class RecipeHistory:
    """
    Model representing a recipe shown to a user.
    
    Tracks when recipes were shown as options during meal planning to
    support recipe rotation and avoid repetition.
    
    Attributes:
        user_id: The Telegram user ID
        recipe_id: Recipe identifier (filename without extension)
        meal_type: Type of meal (breakfast, lunch, dinner, snack)
        phase: The hormonal phase when recipe was shown
        shown_at: ISO format date when recipe was shown as an option
    """
    user_id: str
    recipe_id: str
    meal_type: str
    phase: str
    shown_at: str

@dataclass
class RecipeRecommendations:
    """
    Collection of recipe recommendations for a specific phase.
    
    Contains all meal recommendations and supporting information for a
    particular hormonal phase period.
    
    Attributes:
        phase: The functional phase these recommendations are for
        meals: List of meal recommendations (breakfast, lunch, dinner, snacks)
        shopping_list_preview: Preview of key ingredients needed for shopping
    """
    phase: FunctionalPhaseType
    meals: List[MealRecommendation]
    shopping_list_preview: List[str]
