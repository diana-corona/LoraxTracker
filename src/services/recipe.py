"""
Recipe service for managing recipes and their ingredients.
"""
import os
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from pathlib import Path

try:
    from aws_lambda_powertools import Logger
    logger = Logger()
except ImportError:
    # Fallback for local testing without aws_lambda_powertools
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

from src.utils.recipe_parser import RecipeMarkdownParser
from src.models.recipe import Recipe

@dataclass
class CategorizedIngredients:
    """Container for ingredients categorized by type."""
    proteins: Set[str] = field(default_factory=set)
    produce: Set[str] = field(default_factory=set)
    dairy: Set[str] = field(default_factory=set)
    condiments: Set[str] = field(default_factory=set)
    baking: Set[str] = field(default_factory=set)
    nuts: Set[str] = field(default_factory=set)
    pantry: Set[str] = field(default_factory=set)

class RecipeService:
    """Service for managing recipes and their ingredients."""

    # Common pantry items that are assumed to be in most kitchens
    PANTRY_ITEMS = {
        'salt', 'black pepper', 'olive oil', 'garlic powder', 'paprika',
        'sugar', 'baking powder', 'Italian seasoning'
    }

    # Ingredient category patterns
    CATEGORY_PATTERNS = {
        'proteins': {
            'chicken', 'beef', 'salmon', 'fish', 'pork', 'turkey', 'shrimp', 'tuna',
            'tofu', 'tempeh', 'seitan'
        },
        'produce': {
            'onion', 'garlic', 'tomato', 'carrot', 'celery', 'pepper', 'lettuce',
            'spinach', 'kale', 'cucumber', 'zucchini', 'potato', 'lemon', 'lime',
            'orange', 'apple', 'banana', 'berry', 'blueberry', 'strawberry',
            'herbs', 'cilantro', 'parsley', 'basil', 'chive'
        },
        'dairy': {
            'milk', 'cream', 'cheese', 'butter', 'yogurt', 'egg', 'eggs'
        },
        'condiments': {
            'mayonnaise', 'mustard', 'ketchup', 'vinegar', 'sauce', 'dressing'
        },
        'baking': {
            'flour', 'sugar', 'baking powder', 'baking soda', 'yeast', 'extract',
            'vanilla', 'cocoa'
        },
        'nuts': {
            'almond', 'walnut', 'pecan', 'cashew', 'pistachio', 'peanut',
            'hazelnut', 'macadamia'
        }
    }

    def __init__(self):
        """Initialize recipe service with parser."""
        self.parser = RecipeMarkdownParser()
        self._recipes: Dict[str, Recipe] = {}
        self._phase_recipes: Dict[str, Dict[str, Recipe]] = {
            'power': {},
            'nurture': {},
            'manifestation': {}
        }
        self._load_recipes()

    def _load_recipes(self) -> None:
        """Load all recipes from the recipes directory."""
        recipes_dir = Path("recipes")
        for recipe_dir in recipes_dir.glob("**/[!.]*"):  # Ignore hidden directories
            if recipe_dir.is_dir() and recipe_dir.name not in {'to-process', 'uncategorized'}:
                phase = recipe_dir.name  # Directory name indicates phase
                for recipe_file in recipe_dir.glob("*.md"):
                    if recipe_file.name != 'TEMPLATE_RECIPE.md':
                        try:
                            recipe = self.parser.parse_recipe_file(str(recipe_file))
                            if recipe:
                                recipe_id = recipe_file.stem
                                self._recipes[recipe_id] = recipe
                                if phase in self._phase_recipes:
                                    self._phase_recipes[phase][recipe_id] = recipe
                                logger.info(f"Loaded recipe: {recipe.title} for phase {phase}")
                        except Exception as e:
                            logger.error(f"Error loading recipe {recipe_file}: {str(e)}")

    def get_recipe_by_id(self, recipe_id: str) -> Optional[Recipe]:
        """Get recipe by its ID (filename without extension)."""
        recipe = self._recipes.get(recipe_id)
        if not recipe:
            logger.warning(f"Recipe not found: {recipe_id}")
        return recipe

    def get_recipes_by_meal_type(self, meal_type: str, phase: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Get recipes for a specific meal type, optionally filtered by phase and limited to N options.
        
        Args:
            meal_type: Type of meal (breakfast, lunch, dinner, snack)
            phase: Optional phase to filter by (power, nurture, manifestation)
            limit: Optional maximum number of recipes to return
        """
        # Get recipes from specific phase if provided, otherwise use all recipes
        source_recipes = self._phase_recipes.get(phase, {}) if phase else self._recipes
        
        recipes = [
            {
                'id': recipe_id,
                'title': recipe.title,
                'prep_time': recipe.prep_time
            }
            for recipe_id, recipe in source_recipes.items()
            if meal_type in recipe.tags
        ]

        # Limit number of recipes if specified
        if limit and len(recipes) > limit:
            recipes = recipes[:limit]
        
        logger.info(f"Found {len(recipes)} recipes for meal type: {meal_type}" + (f" in phase {phase}" if phase else ""))
        return recipes

    def categorize_ingredient(self, ingredient: str) -> str:
        """Categorize an ingredient based on keyword matching."""
        ingredient_lower = ingredient.lower()
        
        # First check if it's a pantry item
        if any(item in ingredient_lower for item in self.PANTRY_ITEMS):
            return 'pantry'
        
        # Then check other categories
        for category, patterns in self.CATEGORY_PATTERNS.items():
            if any(pattern in ingredient_lower for pattern in patterns):
                return category
        
        logger.debug(f"Uncategorized ingredient defaulting to pantry: {ingredient}")
        return 'pantry'

    def get_recipe_ingredients(self, recipe_id: str) -> CategorizedIngredients:
        """Get categorized ingredients for a recipe."""
        recipe = self.get_recipe_by_id(recipe_id)
        if not recipe:
            logger.warning(f"Cannot get ingredients, recipe not found: {recipe_id}")
            return CategorizedIngredients()

        ingredients = CategorizedIngredients()
        
        for ingredient in recipe.ingredients:
            category = self.categorize_ingredient(ingredient)
            if hasattr(ingredients, category):
                getattr(ingredients, category).add(ingredient)
            else:
                ingredients.pantry.add(ingredient)

        logger.info(f"Categorized {len(recipe.ingredients)} ingredients for recipe: {recipe.title}")
        return ingredients

    def get_multiple_recipe_ingredients(self, recipe_ids: List[str]) -> CategorizedIngredients:
        """Get combined categorized ingredients for multiple recipes."""
        combined = CategorizedIngredients()
        
        for recipe_id in recipe_ids:
            recipe_ingredients = self.get_recipe_ingredients(recipe_id)
            for category in ['proteins', 'produce', 'dairy', 'condiments', 'baking', 'nuts', 'pantry']:
                getattr(combined, category).update(getattr(recipe_ingredients, category))

        logger.info(f"Combined ingredients for {len(recipe_ids)} recipes")
        return combined

    def is_pantry_item(self, ingredient: str) -> bool:
        """Check if an ingredient is a common pantry item."""
        return any(item in ingredient.lower() for item in self.PANTRY_ITEMS)
