"""
Shopping list generation service.

This module provides functionality for generating formatted shopping lists
from recipe ingredients, handling categorization and formatting.

Typical usage:
    service = ShoppingListService()
    shopping_list = service.generate_list(recipe_ingredients)
    formatted_list = service.format_list(shopping_list)
"""
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class ShoppingList:
    """Model representing a categorized shopping list."""
    proteins: List[str]
    produce: List[str]
    dairy: List[str]
    condiments: List[str]
    baking: List[str]
    nuts: List[str]
    pantry: List[str]

class ShoppingListService:
    """Service for generating and formatting shopping lists."""

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
            ShoppingList: Categorized shopping list
        """
        return ShoppingList(
            proteins=getattr(ingredients, 'proteins', []),
            produce=getattr(ingredients, 'produce', []),
            dairy=getattr(ingredients, 'dairy', []),
            condiments=getattr(ingredients, 'condiments', []),
            baking=getattr(ingredients, 'baking', []),
            nuts=getattr(ingredients, 'nuts', []),
            pantry=getattr(ingredients, 'pantry', [])
        )

    def format_list(self, shopping_list: ShoppingList, recipe_service) -> str:
        """
        Format shopping list into human-readable text.

        Args:
            shopping_list: ShoppingList to format
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
                    *[f"  • {item}" for item in sorted(items)]
                ])

        # Add pantry items note if any were used
        pantry_items = [
            item for item in shopping_list.pantry 
            if recipe_service.is_pantry_item(item)
        ]
        if pantry_items:
            formatted.extend([
                "\n🏠 Pantry Items to Check:",
                "(These basic ingredients are assumed to be in most kitchens)",
                *[f"  • {item}" for item in sorted(pantry_items)]
            ])

        return "\n".join(formatted)
