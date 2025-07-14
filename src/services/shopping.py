"""
Service module for generating shopping lists based on predicted phases.
"""
from typing import List, Dict, Set
from datetime import date, timedelta

from src.models.phase import Phase, FunctionalPhaseType
from src.services.phase import get_current_phase, predict_next_phase

class ShoppingListGenerator:
    """Generator for phase-appropriate shopping lists."""
    
    @staticmethod
    def generate_weekly_list(current_phase: Phase) -> Dict[str, List[str]]:
        """
        Generate a categorized shopping list for the upcoming week.
        
        Args:
            current_phase: Current phase to base predictions on
            
        Returns:
            Dictionary of categorized shopping items
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
        """Get recommended ingredients for a specific phase."""
        base_ingredients = {
            "proteins": set(),
            "vegetables": set(),
            "fruits": set(),
            "fats": set(),
            "carbohydrates": set(),
            "supplements": set(),
            "others": set()
        }
        
        if phase_type == FunctionalPhaseType.POWER:
            base_ingredients.update({
                "fats": {
                    "avocado",
                    "olive oil",
                    "coconut oil",
                    "ghee (clarified butter)",
                    "mixed nuts"
                },
                "proteins": {
                    "fish",
                    "eggs",
                    "tofu",
                    "organic chicken"
                },
                "vegetables": {
                    "broccoli",
                    "brussels sprouts",
                    "curly cabbage",
                    "kale",
                    "bok choy",
                    "garlic",
                    "onion",
                    "leek",
                    "dandelion root",
                    "artichoke",
                    "spinach",
                    "sprouts"
                },
                "others": {
                    "kimchi",
                    "sauerkraut",
                    "yogurt",
                    "kefir"
                },
                "fruits": {
                    "blueberries",
                    "strawberries"
                }
            })
            
        elif phase_type == FunctionalPhaseType.MANIFESTATION:
            base_ingredients.update({
                "vegetables": {
                    "beetroot",
                    "carrot",
                    "turnip",
                    "fennel",
                    "cauliflower",
                    "kale",
                    "broccoli",
                    "fermented pickles",
                    "parsley",
                    "red onion",
                    "radishes"
                },
                "fruits": {
                    "grapefruit",
                    "pineapple",
                    "mango",
                    "papaya",
                    "mixed berries"
                },
                "others": {
                    "dark chocolate",
                    "olives",
                    "red wine (optional)",
                    "almonds",
                    "cashews",
                    "brazil nuts"
                }
            })
            
        else:  # NURTURE
            base_ingredients.update({
                "carbohydrates": {
                    "sweet potato",
                    "cassava",
                    "red potato",
                    "butternut squash",
                    "beetroot",
                    "yam",
                    "oats",
                    "brown rice",
                    "quinoa",
                    "lentils"
                },
                "fruits": {
                    "banana",
                    "dates",
                    "figs",
                    "apples"
                },
                "others": {
                    "sunflower seeds",
                    "dark chocolate",
                    "chickpeas",
                    "chamomile",
                    "ginger",
                    "fennel"
                },
                "proteins": {
                    "chicken for broth",
                    "turkey",
                    "mixed legumes"
                },
                "supplements": {
                    "magnesium",
                    "vitamin B6",
                    "omega-3"
                }
            })
        
        return base_ingredients

    @staticmethod
    def generate_shopping_list(items: dict[str, list[str]]) -> str:
        """
        Format a categorized shopping list for display.
        
        Args:
            items: Dictionary of categorized items
            
        Returns:
            Formatted shopping list string
        """
        formatted_list = ["🛒 Shopping List"]
        
        # Category icons
        icons = {
            "proteins": "🥩",
            "vegetables": "🥬",
            "fruits": "🍎",
            "fats": "🥑",
            "carbohydrates": "🌾",
            "supplements": "💊",
            "others": "🧂"
        }
        
        # Add non-empty categories
        for category, items_list in items.items():
            if items_list:  # Only include categories with items
                formatted_list.extend([
                    "",
                    f"{icons.get(category, '•')} {category.title()}:",
                    *[f"  • {item}" for item in sorted(items_list)]
                ])
        
        return "\n".join(formatted_list)
