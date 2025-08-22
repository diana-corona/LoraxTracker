"""
Shopping list generation service.

This module provides functionality for generating formatted shopping lists
from recipe ingredients, handling categorization and formatting.

Typical usage:
    service = ShoppingListService(recipe_service)
    shopping_list = service.generate_list(recipe_ingredients)
    formatted_list = service.format_list(shopping_list)
"""
from typing import List, Dict, Any
from dataclasses import dataclass, field

from src.services.recipe import RecipeService

@dataclass
class ShoppingList:
    """Model representing a categorized shopping list."""
    proteins: Dict[str, int] = field(default_factory=dict)
    produce: Dict[str, int] = field(default_factory=dict)
    dairy: Dict[str, int] = field(default_factory=dict)
    condiments: Dict[str, int] = field(default_factory=dict)
    baking: Dict[str, int] = field(default_factory=dict)
    nuts: Dict[str, int] = field(default_factory=dict)
    pantry: Dict[str, int] = field(default_factory=dict)

class ShoppingListService:
    """Service for generating and formatting shopping lists."""

    def __init__(self, recipe_service: RecipeService):
        """Initialize with recipe service for ingredient processing."""
        self.recipe_service = recipe_service

    # Shopping list category emojis
    CATEGORY_ICONS = {
        'proteins': '🥩',
        'produce': '🥬',
        'dairy': '🥛',
        'baking': '🥖',
        'nuts': '🥜',
        'condiments': '🫙',
        'pantry': '🏠'
    }

    def generate_list(self, ingredients: Any) -> ShoppingList:
        """
        Generate a shopping list from recipe ingredients.

        Args:
            ingredients: Recipe ingredients object with categorized items

        Returns:
            ShoppingList: Categorized shopping list with ingredient counts
        """
        shopping_list = ShoppingList()
        
        for category in ['proteins', 'produce', 'dairy', 'condiments', 'baking', 'nuts', 'pantry']:
            category_items = getattr(ingredients, category, set())
            category_list = getattr(shopping_list, category)
            
            # Add base ingredients to list with counts
            for item in category_items:
                base_ingredient = self.recipe_service.extract_base_ingredient(item)
                if base_ingredient:  # Skip empty strings
                    category_list[base_ingredient] = category_list.get(base_ingredient, 0) + 1

        return shopping_list

    def format_list(self, shopping_list: ShoppingList, recipe_service) -> str:
        """
        Format shopping list into human-readable text with x1/x2/x3 indicators.

        Args:
            shopping_list: ShoppingList to format with ingredient counts
            recipe_service: RecipeService instance for pantry item checking

        Returns:
            str: Formatted shopping list text with emojis and categories
        """
        formatted = ["🛒 Shopping List\n"]
        
        # Add non-pantry ingredients by category
        for category in ['proteins', 'produce', 'dairy', 'condiments', 'baking', 'nuts']:
            items = getattr(shopping_list, category)
            if items:
                emoji = self.CATEGORY_ICONS.get(category, '•')
                formatted.extend([
                    f"\n{emoji} {category.title()}:",
                    *[f"  • {item} (x{count})" for item, count in sorted(items.items())]
                ])

        # Add pantry items note if any were used
        # Show pantry items
        pantry_items = [item for item, count in shopping_list.pantry.items() if recipe_service.is_pantry_item(item)]
        if pantry_items:
            formatted.extend([
                "\n🏠 Pantry Items to Check:",
                "(These basic ingredients are assumed to be in most kitchens)",
                *[f"  • {item}" for item in sorted(pantry_items)]
            ])

        return "\n".join(formatted)
