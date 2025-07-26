"""
Service module for generating shopping lists based on predicted phases.

This module provides functionality to generate personalized shopping lists
based on the user's current cycle phase and predictions for upcoming phases.

Typical usage:
    >>> phase = get_current_phase(events)
    >>> generator = ShoppingListGenerator()
    >>> items = generator.generate_weekly_list(phase)
    >>> formatted_list = generator.generate_shopping_list(items)
    >>> print(formatted_list)
"""
from typing import List, Dict, Set, Optional
from datetime import date, timedelta

from src.models.phase import Phase, FunctionalPhaseType
from src.services.phase import get_current_phase, predict_next_phase
from src.services.constants import PHASE_INGREDIENTS, SHOPPING_ICONS

class ShoppingListGenerator:
    """Generator for phase-appropriate shopping lists."""
    
    @staticmethod
    def generate_weekly_list(current_phase: Phase) -> Dict[str, List[str]]:
        """
        Generate a categorized shopping list for the upcoming week.
        
        Args:
            current_phase: Current phase to base predictions on
            
        Returns:
            Dictionary mapping categories to sorted lists of ingredients:
            {
                "proteins": ["eggs", "fish", ...],
                "vegetables": ["broccoli", "kale", ...],
                ...
            }
            
        Example:
            >>> phase = get_current_phase(events)
            >>> items = ShoppingListGenerator.generate_weekly_list(phase)
            >>> print(f"Proteins needed: {', '.join(items['proteins'])}")
        """
        # Get phases for the next week
        phases = [current_phase]
        next_phase = current_phase
        for _ in range(6):  # Look ahead 6 more days
            next_phase = predict_next_phase(next_phase)
            phases.append(next_phase)
        
        # Collect unique ingredients needed for all phases
        ingredients: Dict[str, Set[str]] = {
            "proteins": set(),
            "vegetables": set(),
            "fruits": set(),
            "fats": set(),
            "carbohydrates": set(),
            "supplements": set(),
            "others": set()
        }
        
        for phase in phases:
            items = ShoppingListGenerator._get_phase_ingredients(phase.functional_phase)
            for category, items_set in items.items():
                ingredients[category].update(items_set)
        
        # Convert sets to sorted lists
        return {
            category: sorted(items)
            for category, items in ingredients.items()
        }
    
    @staticmethod
    def _get_phase_ingredients(phase_type: FunctionalPhaseType) -> Dict[str, Set[str]]:
        """
        Get recommended ingredients for a specific phase.
        
        Args:
            phase_type: Functional phase type to get ingredients for
            
        Returns:
            Dictionary mapping categories to sets of ingredients
            
        Example:
            >>> ingredients = ShoppingListGenerator._get_phase_ingredients(FunctionalPhaseType.POWER)
            >>> print(f"Recommended fats: {', '.join(ingredients['fats'])}")
        """
        base_ingredients = {
            "proteins": set(),
            "vegetables": set(),
            "fruits": set(),
            "fats": set(),
            "carbohydrates": set(),
            "supplements": set(),
            "others": set()
        }
        
        if phase_type in PHASE_INGREDIENTS:
            base_ingredients.update(PHASE_INGREDIENTS[phase_type])
            
        return base_ingredients

    @staticmethod
    def generate_shopping_list(items: Dict[str, List[str]]) -> str:
        """
        Format a categorized shopping list for display.
        
        Args:
            items: Dictionary of categorized items
            
        Returns:
            Formatted shopping list string with emoji categories
            
        Example:
            >>> items = {"fruits": ["apple", "banana"], "vegetables": ["kale", "spinach"]}
            >>> print(ShoppingListGenerator.generate_shopping_list(items))
            🛒 Shopping List
            
            🍎 Fruits:
              • apple
              • banana
            
            🥬 Vegetables:
              • kale
              • spinach
        """
        formatted_list = ["🛒 Shopping List"]
        
        # Add non-empty categories with icons from constants
        for category, items_list in items.items():
            if items_list:  # Only include categories with items
                formatted_list.extend([
                    "",
                    f"{SHOPPING_ICONS.get(category, '•')} {category.title()}:",
                    *[f"  • {item}" for item in sorted(items_list)]
                ])
        
        return "\n".join(formatted_list)
