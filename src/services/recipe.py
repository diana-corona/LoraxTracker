"""
Recipe service for managing recipes and their ingredients.
"""
import os
import re
from datetime import datetime, timedelta
import time
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from pathlib import Path
from boto3.dynamodb.conditions import Key

try:
    from aws_lambda_powertools import Logger
    logger = Logger()
except ImportError:
    # Fallback for local testing without aws_lambda_powertools
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

from src.utils.recipe_parser import RecipeMarkdownParser
from src.models.recipe import Recipe, RecipeHistory
from src.utils.dynamo import get_dynamo, create_pk, create_recipe_history_sk

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
            'onion', 'garlic', 'tomato', 'carrot', 'celery', 'bell pepper',
            'lettuce', 'spinach', 'kale', 'cucumber', 'zucchini', 'potato',
            'lemon', 'lime', 'orange', 'apple', 'banana', 'berry', 'blueberry',
            'strawberry', 'herbs', 'cilantro', 'parsley', 'basil', 'chive',
            'pepper', 'peppers', 'bell peppers'
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
        """Initialize recipe service with parser and DynamoDB client."""
        self.parser = RecipeMarkdownParser()
        self._recipes: Dict[str, Recipe] = {}
        self._phase_recipes: Dict[str, Dict[str, Recipe]] = {
            'power': {},
            'nurture': {},
            'manifestation': {}
        }
        self.dynamo = get_dynamo()

    def get_recipe_history(self, user_id: str, days: int = 30) -> List[str]:
        """
        Get recipes shown to user in last N days.
        
        Args:
            user_id: Telegram user ID to get history for
            days: Number of days of history to look back (default 30)
            
        Returns:
            List of recipe IDs that were shown to the user
        """
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        items = self.dynamo.query_items(
            partition_key="PK",
            partition_value=create_pk(user_id),
            sort_key_condition=Key('SK').begins_with('RECIPE#')
        )
        # Extract recipe_id from RECIPE#recipe_id#date format
        return [item['SK'].split('#')[1] for item in items]

    def save_recipe_history(
        self, 
        user_id: str, 
        recipe_id: str,
        meal_type: str,
        phase: str
    ) -> None:
        """
        Save recipe selection to history.
        
        Args:
            user_id: Telegram user ID
            recipe_id: Recipe identifier (filename without extension)
            meal_type: Type of meal (breakfast, lunch, dinner, snack)
            phase: The hormonal phase when recipe was shown
        """
        now = datetime.now().isoformat()
        ttl = int(time.time()) + (30 * 24 * 60 * 60)  # 30 days
        
        self.dynamo.put_item({
            'PK': create_pk(user_id),
            'SK': create_recipe_history_sk(recipe_id, now),
            'meal_type': meal_type,
            'phase': phase,
            'ttl': ttl
        })
        
        logger.info("Saved recipe history", extra={
            "user_id": user_id,
            "recipe_id": recipe_id,
            "meal_type": meal_type,
            "phase": phase
        })

    def load_recipes_for_meal_planning(self, phase: str, user_id: Optional[str] = None) -> None:
        """
        Load a limited set of recipes for meal planning (2 per meal type) for a specific phase.
        
        Args:
            phase: The phase to load recipes for (power, nurture, manifestation)
            user_id: Optional user ID to enable recipe rotation
        """
        if phase not in self._phase_recipes:
            logger.warning(f"Invalid phase: {phase}")
            return

        # Clear existing recipes
        self._recipes.clear()
        for p in self._phase_recipes:
            self._phase_recipes[p].clear()

        # Get recently shown recipes if user_id provided
        recent_recipes = set()
        if user_id:
            try:
                recent_recipes = set(self.get_recipe_history(user_id))
                logger.info("Retrieved recipe history", extra={
                    "user_id": user_id,
                    "recent_count": len(recent_recipes)
                })
            except Exception as e:
                logger.warning(
                    "Failed to get recipe history, proceeding without rotation",
                    extra={
                        "user_id": user_id,
                        "error": str(e)
                    }
                )

        recipes_dir = Path("recipes") / phase
        if not recipes_dir.is_dir():
            logger.warning(f"Recipe directory not found for phase: {phase}")
            return

        meal_type_counts = {
            'breakfast': 0,
            'lunch': 0,
            'dinner': 0,
            'snack': 0
        }

        # Load all available recipes
        recipe_files = [f for f in recipes_dir.glob("*.md") if f.name != 'TEMPLATE_RECIPE.md']
        fresh_recipes = [f for f in recipe_files if f.stem not in recent_recipes]
        fallback_recipes = [f for f in recipe_files if f.stem in recent_recipes]

        def load_recipe(recipe_file: Path) -> Optional[Recipe]:
            """Helper to load a recipe file safely."""
            try:
                return self.parser.parse_recipe_file(str(recipe_file))
            except Exception as e:
                logger.error(f"Error loading recipe {recipe_file}: {str(e)}")
                return None

        # Index recipes by meal type
        meal_type_fresh_recipes: Dict[str, List[tuple[Path, Recipe]]] = {
            'breakfast': [],
            'lunch': [],
            'dinner': [],
            'snack': []
        }

        # First pass: Index all fresh recipes by meal type
        for recipe_file in fresh_recipes:
            recipe = load_recipe(recipe_file)
            if recipe:
                for meal_type in meal_type_counts.keys():
                    if meal_type in recipe.tags:
                        meal_type_fresh_recipes[meal_type].append((recipe_file, recipe))
        
        # Process fresh recipes for each meal type
        for meal_type in meal_type_counts.keys():
            fresh_recipes_for_type = sorted(
                [(f, r) for f, r in meal_type_fresh_recipes[meal_type]],
                key=lambda x: x[0].stem
            )
            
            # Sort all fresh recipes for this meal type
            sorted_recipes = sorted(fresh_recipes_for_type, key=lambda x: x[0].stem)
            
            # First try to load all fresh recipes
            for recipe_file, recipe in sorted_recipes:
                recipe_id = recipe_file.stem
                # Skip if we already have enough recipes
                if meal_type_counts[meal_type] >= 2:
                    break
                    
                self._recipes[recipe_id] = recipe
                self._phase_recipes[phase][recipe_id] = recipe
                meal_type_counts[meal_type] += 1
                logger.info(
                    f"Loaded fresh {meal_type} recipe: {recipe.title}",
                    extra={
                        "recipe_id": recipe_id,
                        "phase": phase,
                        "is_fresh": True
                    }
                )

            # Only use fallbacks if we have no fresh recipes at all
            if meal_type_counts[meal_type] == 0:
                # Try fallback recipes
                for recipe_file in fallback_recipes:
                    # Skip if we have enough recipes
                    if meal_type_counts[meal_type] >= 2:
                        break
                        
                    recipe = load_recipe(recipe_file)
                    if recipe and meal_type in recipe.tags:
                        recipe_id = recipe_file.stem
                        self._recipes[recipe_id] = recipe
                        self._phase_recipes[phase][recipe_id] = recipe
                        meal_type_counts[meal_type] += 1
                        logger.info(
                            f"Loaded fallback {meal_type} recipe: {recipe.title}",
                            extra={
                                "recipe_id": recipe_id,
                                "phase": phase,
                                "is_fresh": False
                            }
                        )

        logger.info(f"Loaded recipes for meal planning - Phase: {phase}, Counts: {meal_type_counts}")

    def get_recipe_by_id(self, recipe_id: str) -> Optional[Recipe]:
        """Get recipe by its ID (filename without extension)."""
        recipe = self._recipes.get(recipe_id)
        if not recipe:
            logger.warning(f"Recipe not found: {recipe_id}")
        return recipe

    def get_recipes_by_meal_type(
        self, 
        meal_type: str, 
        phase: Optional[str] = None, 
        limit: Optional[int] = None,
        exclude_recipe_ids: Optional[List[str]] = None
    ) -> List[Dict[str, str]]:
        """
        Get recipes for a specific meal type, optionally filtered by phase and limited to N options.
        
        Args:
            meal_type: Type of meal (breakfast, lunch, dinner, snack)
            phase: Optional phase to filter by (power, nurture, manifestation)
            limit: Optional maximum number of recipes to return
            exclude_recipe_ids: Optional list of recipe IDs to exclude from results
        
        Returns:
            List of dictionaries containing recipe information
        """
        # Get recipes from specific phase if provided, otherwise use all recipes
        source_recipes = self._phase_recipes.get(phase, {}) if phase else self._recipes
        
        exclude_recipe_ids = set(exclude_recipe_ids or [])
        
        # Filter recipes by meal type and exclusions
        recipes = [
            {
                'id': recipe_id,
                'title': recipe.title,
                'prep_time': recipe.prep_time
            }
            for recipe_id, recipe in source_recipes.items()
            if meal_type in recipe.tags and recipe_id not in exclude_recipe_ids
        ]

        # Log warning if few recipes available after exclusions
        if exclude_recipe_ids and len(recipes) < 2:
            logger.warning(
                "Few recipes available after exclusions",
                extra={
                    "meal_type": meal_type,
                    "phase": phase,
                    "available_count": len(recipes),
                    "excluded_count": len(exclude_recipe_ids)
                }
            )

        # Limit number of recipes if specified
        if limit and len(recipes) > limit:
            recipes = recipes[:limit]
        
        logger.info(
            f"Found {len(recipes)} recipes for meal type: {meal_type}",
            extra={
                "phase": phase,
                "excluded_count": len(exclude_recipe_ids),
                "limit": limit
            }
        )
        return recipes

    def extract_base_ingredient(self, ingredient: str) -> str:
        """
        Extract the base ingredient name from a full ingredient description.
        
        Args:
            ingredient: Full ingredient description (e.g. "4 heads garlic, tops sliced off")
            
        Returns:
            str: Base ingredient name (e.g. "garlic")
            
        Example:
            >>> extract_base_ingredient("2 boneless skinless chicken breasts")
            'chicken'
            >>> extract_base_ingredient("500g lean ground beef")
            'beef'
        """
        # Normalize proteins first
        protein_mappings = {
            'chicken': [
                r'chicken\s*\w*',  # chicken breast, chicken thigh, etc.
                r'boneless\s*skinless\s*chicken',
            ],
            'beef': [
                r'beef\s*\w*',  # beef steak, beef roast, etc.
                r'ground\s*beef',
                r'steak',
            ],
            'pork': [
                r'pork\s*\w*',  # pork chop, pork loin, etc.
                r'ham',
                r'bacon',
            ],
            'fish': [
                r'salmon',
                r'tuna',
                r'cod',
                r'tilapia',
                r'fish\s*\w*',
            ]
        }
        
        # Try to match proteins first
        cleaned = ingredient.lower()
        for base_protein, patterns in protein_mappings.items():
            for pattern in patterns:
                if re.search(pattern, cleaned, re.IGNORECASE):
                    return base_protein
        
        # If not a protein, remove amounts and measurements
        patterns_to_remove = [
            r'^\d+\.?\d*\s*',  # Numbers at start
            r'[¼½¾⅛]',  # Unicode fractions
            r'[-/]',  # Remove hyphens and slashes
            r'\(.*?\)',  # Remove parenthetical content
            r'cups?|tablespoons?|tbsp|tsp|teaspoons?|pounds?|lbs?|ounces?|oz|heads?|medium|large|small|handful|pinch|dash',
            r'diced|chopped|sliced|minced|peeled|grated|crushed|ground|boneless|skinless',
            r'fresh|dried|frozen|canned|cooked|raw|prepared',
            r'optional|to taste',
            r'whole|clove(s)?',  # Common descriptors
            r',.*$'  # Remove everything after a comma
        ]
        
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Clean up extra spaces, including spaces around hyphens
        cleaned = ' '.join(cleaned.split())
        cleaned = cleaned.strip()
        
        return cleaned

    def categorize_ingredient(self, ingredient: str) -> str:
        """Categorize an ingredient based on keyword matching."""
        # Extract base ingredient first
        base_ingredient = self.extract_base_ingredient(ingredient)
        ingredient_lower = base_ingredient.lower()
        
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
