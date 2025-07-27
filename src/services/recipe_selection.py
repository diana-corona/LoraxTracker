"""
Service for recipe selection and shopping list generation.

This module provides functionality for presenting recipe options with embedded URLs
and generating shopping lists based on selected recipes while filtering out basic
household ingredients.
"""
from typing import Dict, List, Set, Optional
from dataclasses import dataclass

from src.models.recipe import Recipe, MealRecommendation
from src.services.constants import (
    MEAL_ICONS, 
    SHOPPING_ICONS,
    BASIC_INGREDIENTS
)

@dataclass
class MealSelection:
    """Selected recipe for a specific meal type."""
    meal_type: str
    recipe: Recipe

@dataclass
class ShoppingList:
    """Organized shopping list with categorized ingredients."""
    categories: Dict[str, Set[str]]
    basic_ingredients: Set[str]

class RecipeSelectionService:
    """Service for managing recipe selections and generating shopping lists."""
    
    @staticmethod
    def format_recipe_options(recommendations: List[MealRecommendation]) -> str:
        """
        Format recipe options with embedded URLs for display.
        
        Args:
            recommendations: List of meal recommendations to format
            
        Returns:
            Formatted string with recipe options and URLs
            
        Example:
            >>> recommendations = [breakfast_meals, lunch_meals, ...]
            >>> print(RecipeSelectionService.format_recipe_options(recommendations))
            Please select your preferred recipes:
            
            🥞 Breakfast (choose 1):
            1. [Almond Blueberry Muffins](https://...)
            2. [Budget Vegetable Frittata](https://...)
            ...
        """
        lines = ["Please select your preferred recipes:", ""]
        
        for meal in recommendations:
            # Add meal type header with emoji
            icon = MEAL_ICONS.get(meal.meal_type.lower(), "•")
            lines.append(f"{icon} {meal.meal_type.title()} (choose 1):")
            
            # Add numbered recipe options with URLs
            for i, recipe in enumerate(meal.recipes, 1):
                url_part = f"]({recipe.url})" if recipe.url else "]"
                lines.append(f"{i}. [{recipe.title}{url_part} ({recipe.prep_time} min)")
            
            lines.append("")  # Add blank line between meal types
            
        return "\n".join(lines)

    @staticmethod
    def generate_shopping_list(selections: List[MealSelection]) -> ShoppingList:
        """
        Generate a categorized shopping list from selected recipes.
        
        Args:
            selections: List of meal selections containing chosen recipes
            
        Returns:
            ShoppingList object with categorized ingredients and basic ingredients
            
        Example:
            >>> selections = [breakfast_choice, lunch_choice, ...]
            >>> shopping_list = RecipeSelectionService.generate_shopping_list(selections)
            >>> print(shopping_list.categories['proteins'])
            {'salmon', 'chicken breast', ...}
        """
        # Initialize category sets
        categories: Dict[str, Set[str]] = {
            "proteins": set(),
            "vegetables": set(),
            "fruits": set(),
            "pantry": set(),
            "others": set()
        }
        basic_needed: Set[str] = set()
        
        # Process each selected recipe
        for selection in selections:
            recipe = selection.recipe
            for ingredient in recipe.ingredients:
                # Clean up ingredient text (remove amounts)
                cleaned = RecipeSelectionService._clean_ingredient(ingredient)
                
                if cleaned.lower() in BASIC_INGREDIENTS:
                    basic_needed.add(cleaned)
                    continue
                    
                # Categorize ingredient (simplified categorization)
                category = RecipeSelectionService._categorize_ingredient(cleaned)
                categories[category].add(cleaned)
        
        return ShoppingList(categories, basic_needed)

    @staticmethod
    def format_shopping_list(shopping_list: ShoppingList) -> str:
        """
        Format a shopping list for display with category icons.
        
        Args:
            shopping_list: ShoppingList object to format
            
        Returns:
            Formatted string ready for display
            
        Example:
            >>> formatted = RecipeSelectionService.format_shopping_list(shopping_list)
            >>> print(formatted)
            🛒 Shopping List
            
            🥩 Proteins:
              • chicken breast
              • salmon
            ...
        """
        lines = ["🛒 Shopping List", ""]
        
        # Add categories with items
        for category, items in shopping_list.categories.items():
            if items:  # Only include non-empty categories
                icon = SHOPPING_ICONS.get(category, "•")
                lines.extend([
                    f"{icon} {category.title()}:",
                    *[f"  • {item}" for item in sorted(items)],
                    ""
                ])
        
        # Add basic ingredients section if any are needed
        if shopping_list.basic_ingredients:
            lines.extend([
                f"{SHOPPING_ICONS['basic']} Basic Ingredients to Check:",
                *[f"  • {item}" for item in sorted(shopping_list.basic_ingredients)],
                ""
            ])
        
        return "\n".join(lines)

    @staticmethod
    def _clean_ingredient(ingredient: str) -> str:
        """Remove amounts and standardize ingredient text."""
        # Split on common delimiters and take the last part
        parts = [p.strip() for p in ingredient.split(",")]
        name = parts[-1]
        
        # Remove common measurement patterns and modifiers
        measurements = ["cup", "tablespoon", "teaspoon", "pound", "ounce", "gram"]
        modifiers = ["large", "small", "medium", "fresh", "dried", "whole", "chopped", "minced"]
        
        words = name.split()
        # Remove leading measurements and numbers
        while words and (
            words[0].isdigit() or
            words[0][0].isdigit() or
            any(m in words[0].lower() for m in measurements)
        ):
            words.pop(0)
            
        # Remove common modifiers
        words = [w for w in words if w.lower() not in modifiers]
        
        return " ".join(words).strip()

    @staticmethod
    def _categorize_ingredient(ingredient: str) -> str:
        """
        Categorize an ingredient based on common patterns.
        This is a simplified categorization - in practice you might want
        a more comprehensive ingredient database.
        """
        ingredient = ingredient.lower()
        
        if any(protein in ingredient for protein in 
               ["chicken", "fish", "salmon", "beef", "pork", "egg", "tofu"]):
            return "proteins"
            
        if any(veggie in ingredient for veggie in 
               ["carrot", "broccoli", "spinach", "lettuce", "onion", "garlic"]):
            return "vegetables"
            
        if any(fruit in ingredient for fruit in 
               ["apple", "banana", "berries", "berry", "orange", "lemon", "lime", "blueberry", "strawberry", "raspberry"]):
            return "fruits"
            
        if any(pantry in ingredient for pantry in 
               ["flour", "sugar", "oil", "vinegar", "sauce", "spice", "herb", "gum", "powder", "extract"]):
            return "pantry"
            
        # If we haven't categorized it yet, check if it's in basic ingredients
        if ingredient in BASIC_INGREDIENTS:
            return "pantry"
            
        return "others"
