"""
Recipe service for meal plan integration.

This module provides core business logic for managing recipes, generating
recommendations, and creating meal plans based on hormonal cycle phases.
"""
import os
import random
from typing import Dict, List, Optional
from collections import Counter

try:
    from aws_lambda_powertools import Logger
    logger = Logger()
except ImportError:
    # Fallback for local testing without aws_lambda_powertools
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

from src.models.phase import FunctionalPhaseType
from src.models.recipe import Recipe, MealRecommendation, RecipeRecommendations
from src.utils.recipe_parser import RecipeMarkdownParser

class RecipeService:
    """Service for managing recipe operations."""
    
    parser = None  # Class-level attribute for easier mocking in tests
    
    def __init__(self, recipes_base_path: str = "recipes"):
        """
        Initialize recipe service.
        
        Args:
            recipes_base_path: Base path to recipes folder
        """
        self.recipes_base_path = recipes_base_path
        if RecipeService.parser is None:
            RecipeService.parser = RecipeMarkdownParser(recipes_base_path)
        self._recipe_cache: Dict[str, List[Recipe]] = {}
        
        # Phase folder mapping
        self.phase_folders = {
            FunctionalPhaseType.POWER: "power",
            FunctionalPhaseType.MANIFESTATION: "manifestation", 
            FunctionalPhaseType.NURTURE: "nurture"
        }
    
    def load_recipes_by_phase(self, phase: FunctionalPhaseType) -> List[Recipe]:
        """
        Load all recipes for a specific phase.
        
        Args:
            phase: Functional phase to load recipes for
            
        Returns:
            List of Recipe objects for the specified phase
        """
        # Check cache first
        cache_key = phase.value
        if cache_key in self._recipe_cache:
            logger.info(f"Loading {phase.value} recipes from cache")
            return self._recipe_cache[cache_key]
        
        recipes = []
        phase_folder = self.phase_folders.get(phase)
        
        if not phase_folder:
            logger.warning(f"No folder mapping found for phase: {phase}")
            return recipes
        
        recipes_dir = os.path.join(self.recipes_base_path, phase_folder)
        
        if not os.path.exists(recipes_dir):
            logger.warning(f"Recipe directory not found: {recipes_dir}")
            return recipes
        
        try:
            # Scan for .md files
            for filename in os.listdir(recipes_dir):
                if filename.endswith('.md'):
                    file_path = os.path.join(recipes_dir, filename)
                    
                    try:
                        recipe = self.parser.parse_recipe_file(file_path)
                        if recipe:
                            recipes.append(recipe)
                        else:
                            logger.warning(f"Failed to parse recipe: {file_path}")
                    except Exception as e:
                        logger.error(f"Error parsing recipe {file_path}: {str(e)}")
                        continue
            
            # Cache the results
            self._recipe_cache[cache_key] = recipes
            logger.info(f"Loaded {len(recipes)} recipes for {phase.value} phase")
            
        except Exception as e:
            logger.error(f"Error scanning recipe directory {recipes_dir}: {str(e)}")
        
        return recipes
    
    def get_recipe_recommendations(
        self, 
        phase: FunctionalPhaseType,
        days_in_phase: int = 7
    ) -> RecipeRecommendations:
        """
        Generate recipe recommendations for a phase period.
        
        Args:
            phase: Functional phase to generate recommendations for
            days_in_phase: Number of days in this phase period
            
        Returns:
            RecipeRecommendations object with meal suggestions
        """
        try:
            # Load recipes for this phase
            recipes = self.load_recipes_by_phase(phase)
            
            if not recipes:
                logger.warning(f"No recipes found for {phase.value} phase")
                return RecipeRecommendations(
                    phase=phase,
                    meals=[],
                    shopping_list_preview=[]
                )
            
            # Balance meal types and select representative recipes
            meal_recommendations = self.balance_meal_types(recipes)
            
            # Generate shopping list preview
            selected_recipes = []
            for meal_rec in meal_recommendations:
                selected_recipes.extend(meal_rec.recipes)
            
            shopping_preview = self.generate_shopping_preview(selected_recipes)
            
            logger.info(f"Generated {len(meal_recommendations)} meal recommendations for {phase.value}")
            
            return RecipeRecommendations(
                phase=phase,
                meals=meal_recommendations,
                shopping_list_preview=shopping_preview
            )
            
        except Exception as e:
            logger.error(f"Error generating recipe recommendations for {phase.value}: {str(e)}")
            return RecipeRecommendations(
                phase=phase,
                meals=[],
                shopping_list_preview=[]
            )
    
    def balance_meal_types(self, recipes: List[Recipe]) -> List[MealRecommendation]:
        """
        Ensure balanced meal type distribution.
        
        Args:
            recipes: List of available recipes
            
        Returns:
            List of MealRecommendation objects with balanced meal types
        """
        # Categorize recipes by meal type
        meal_categories = {
            'breakfast': [],
            'lunch': [],
            'dinner': [],
            'snack': []
        }
        
        for recipe in recipes:
            for tag in recipe.tags:
                tag_lower = tag.lower().strip()
                if tag_lower in meal_categories:
                    meal_categories[tag_lower].append(recipe)
        
        meal_recommendations = []
        
        # Select recipes for each meal type
        for meal_type, available_recipes in meal_categories.items():
            if not available_recipes:
                continue
            
            # Select 1-2 recipes per meal type based on variety
            selected_recipes = self._select_diverse_recipes(available_recipes, max_recipes=2)
            
            if selected_recipes:
                total_prep_time = sum(recipe.prep_time for recipe in selected_recipes)
                meal_recommendations.append(MealRecommendation(
                    meal_type=meal_type,
                    recipes=selected_recipes,
                    prep_time_total=total_prep_time
                ))
        
        # If no specific meal types found, select general recipes
        if not meal_recommendations:
            logger.info("No specific meal types found, selecting general recipes")
            selected_recipes = self._select_diverse_recipes(recipes, max_recipes=4)
            if selected_recipes:
                total_prep_time = sum(recipe.prep_time for recipe in selected_recipes)
                meal_recommendations.append(MealRecommendation(
                    meal_type="general",
                    recipes=selected_recipes,
                    prep_time_total=total_prep_time
                ))
        
        return meal_recommendations
    
    def generate_shopping_preview(self, recipes: List[Recipe]) -> List[str]:
        """
        Generate preview of key ingredients needed for shopping.
        
        Args:
            recipes: List of selected recipes
            
        Returns:
            List of top ingredients for shopping list
        """
        if not recipes:
            return []
        
        # Extract and count ingredients
        ingredient_counter = Counter()
        
        for recipe in recipes:
            for ingredient in recipe.ingredients:
                # Extract main ingredient name (remove amounts/measurements)
                clean_ingredient = self._extract_main_ingredient(ingredient)
                if clean_ingredient:
                    ingredient_counter[clean_ingredient] += 1
        
        # Get top 5-8 most common ingredients
        top_ingredients = [
            ingredient for ingredient, count in ingredient_counter.most_common(8)
        ]
        
        return top_ingredients
    
    def _select_diverse_recipes(self, recipes: List[Recipe], max_recipes: int = 2) -> List[Recipe]:
        """
        Select diverse recipes avoiding ingredient overlap.
        
        Args:
            recipes: Available recipes to select from
            max_recipes: Maximum number of recipes to select
            
        Returns:
            List of selected diverse recipes
        """
        if not recipes:
            return []
        
        if len(recipes) <= max_recipes:
            return recipes
        
        selected = []
        used_ingredients = set()
        
        # Group recipes by main ingredients
        recipe_groups = {}
        for recipe in recipes:
            main_ingredients = set()
            for ingredient in recipe.ingredients[:5]:  # Check first 5 ingredients
                main_ingredient = self._extract_main_ingredient(ingredient)
                if main_ingredient:
                    main_ingredients.add(main_ingredient.lower())
            
            # Use first main ingredient as group key
            if main_ingredients:
                key = sorted(main_ingredients)[0]
                if key not in recipe_groups:
                    recipe_groups[key] = []
                recipe_groups[key].append(recipe)
        
        # Select one recipe from each diverse ingredient group
        sorted_groups = sorted(recipe_groups.items(), key=lambda x: len(x[1]), reverse=True)
        for ingredient, group_recipes in sorted_groups:
            if len(selected) >= max_recipes:
                break
            
            # Skip if we already have a recipe with this main ingredient
            if ingredient in used_ingredients:
                continue
            
            # Select recipe from group with lowest prep time
            recipe = min(group_recipes, key=lambda r: r.prep_time)
            selected.append(recipe)
            used_ingredients.add(ingredient)
        
        # If we still need more recipes and have unused groups, add from them
        remaining_groups = [group for ing, group in sorted_groups if ing not in used_ingredients]
        while len(selected) < max_recipes and remaining_groups:
            group = remaining_groups.pop(0)
            recipe = min(group, key=lambda r: r.prep_time)
            selected.append(recipe)
        
        return selected[:max_recipes]
    
    def _extract_main_ingredient(self, ingredient_line: str) -> Optional[str]:
        """
        Extract main ingredient name from ingredient line.
        
        Args:
            ingredient_line: Full ingredient line with amounts
            
        Returns:
            Main ingredient name without measurements
        """
        # Remove common measurements and numbers
        import re
        
        # Remove measurements like "1 cup", "2 tablespoons", etc.
        cleaned = re.sub(r'^\d+(?:\.\d+)?\s*(?:cups?|tablespoons?|teaspoons?|tbsp|tsp|oz|pounds?|lbs?|grams?|kg|ml|liters?)\s*', '', ingredient_line, flags=re.IGNORECASE)
        
        # Remove fractions like "1/2", "3/4"
        cleaned = re.sub(r'^\d+/\d+\s*', '', cleaned)
        
        # Remove parenthetical descriptions
        cleaned = re.sub(r'\([^)]*\)', '', cleaned)
        
        # List of words to ignore or remove
        ignore_words = {'of', 'to', 'the', 'a', 'an', 'fresh', 'dried', 'frozen', 'and'}
        connecting_words = {'and', 'or', 'with', '&'}
        
        # Split and clean words
        words = cleaned.strip().split()
        if not words:
            return None
            
        # Filter out connecting words and ignored words
        significant_words = []
        skip_next = False
        for i, word in enumerate(words):
            if skip_next:
                skip_next = False
                continue
                
            word_lower = word.lower()
            
            # Skip if it's in our ignore or connecting words lists
            if word_lower in ignore_words or word_lower in connecting_words:
                continue
                
            # Skip measurements
            if re.match(r'^(?:cup|tablespoon|teaspoon|tbsp|tsp|oz|pound|lb|gram|kg|ml|liter)s?$', word, re.IGNORECASE):
                continue
                
            significant_words.append(word_lower)
            
            # Only take first two significant ingredients if connected by 'and'
            if len(significant_words) == 2 and i < len(words) - 1 and words[i+1].lower() in connecting_words:
                break
        
        if not significant_words:
            return None
            
        return ' '.join(significant_words)
