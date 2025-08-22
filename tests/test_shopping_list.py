"""
Tests for shopping list service.
"""
from dataclasses import dataclass
from typing import List
import pytest

from src.services.shopping_list import ShoppingListService, ShoppingList

@dataclass
class MockIngredients:
    """Mock ingredients for testing."""
    proteins: List[str]
    produce: List[str]
    dairy: List[str]
    condiments: List[str]
    baking: List[str]
    nuts: List[str]
    pantry: List[str]

class MockRecipeService:
    """Mock recipe service for testing."""
    def is_pantry_item(self, item: str) -> bool:
        return item in ['salt', 'pepper', 'oil']
        
    def extract_base_ingredient(self, ingredient: str) -> str:
        """Extract base ingredient from ingredient description for testing."""
        # For test purposes, we'll handle just the basic cases used in tests
        ingredient = ingredient.lower()
        if 'salt' in ingredient or 'pepper' in ingredient:
            return 'salt pepper' if 'and' in ingredient else ingredient
        # Return the ingredient as-is for other test cases
        return ingredient

@pytest.fixture
def shopping_service(recipe_service):
    """Create shopping list service instance."""
    return ShoppingListService(recipe_service)

@pytest.fixture
def recipe_service():
    """Create mock recipe service instance."""
    return MockRecipeService()

@pytest.fixture
def ingredients():
    """Create mock ingredients."""
    return MockIngredients(
        proteins=['chicken', 'eggs'],
        produce=['lettuce', 'tomato'],
        dairy=['milk', 'cheese'],
        condiments=['mayo'],
        baking=['flour'],
        nuts=['almonds'],
        pantry=['salt', 'pepper', 'vinegar']
    )

def test_generate_list(shopping_service, ingredients):
    """Test shopping list generation from ingredients."""
    result = shopping_service.generate_list(ingredients)
    
    assert isinstance(result, ShoppingList)
    assert result.proteins == ['chicken', 'eggs']
    assert result.produce == ['lettuce', 'tomato']
    assert result.dairy == ['milk', 'cheese']
    assert result.condiments == ['mayo']
    assert result.baking == ['flour']
    assert result.nuts == ['almonds']
    assert result.pantry == ['salt', 'pepper', 'vinegar']

def test_generate_list_empty_categories(shopping_service):
    """Test shopping list generation with empty categories."""
    empty_ingredients = MockIngredients(
        proteins=[], produce=[], dairy=[],
        condiments=[], baking=[], nuts=[], pantry=[]
    )
    
    result = shopping_service.generate_list(empty_ingredients)
    
    assert isinstance(result, ShoppingList)
    assert len(result.proteins) == 0
    assert len(result.produce) == 0
    assert len(result.dairy) == 0
    assert len(result.condiments) == 0
    assert len(result.baking) == 0
    assert len(result.nuts) == 0
    assert len(result.pantry) == 0

def test_format_list(shopping_service, recipe_service, ingredients):
    """Test shopping list formatting with all categories."""
    shopping_list = shopping_service.generate_list(ingredients)
    result = shopping_service.format_list(shopping_list, recipe_service)
    
    # Check that all categories are present
    assert "🛒 Shopping List" in result
    assert "🥩 Proteins:" in result
    assert "🥬 Produce:" in result
    assert "🥛 Dairy:" in result
    assert "🫙 Condiments:" in result
    assert "🥖 Baking:" in result
    assert "🥜 Nuts:" in result
    
    # Check that items are listed under categories
    assert "  • chicken" in result
    assert "  • eggs" in result
    assert "  • lettuce" in result
    assert "  • tomato" in result
    
    # Check pantry items section
    assert "🏠 Pantry Items to Check:" in result
    assert "(These basic ingredients are assumed to be in most kitchens)" in result
    assert "  • salt" in result
    assert "  • pepper" in result
    assert "  • vinegar" not in result  # Not a pantry item

def test_format_list_empty_categories(shopping_service, recipe_service):
    """Test shopping list formatting with empty categories."""
    empty_ingredients = MockIngredients(
        proteins=[], produce=[], dairy=[],
        condiments=[], baking=[], nuts=[], pantry=[]
    )
    shopping_list = shopping_service.generate_list(empty_ingredients)
    result = shopping_service.format_list(shopping_list, recipe_service)
    
    # Check that empty categories are not included
    assert "🛒 Shopping List" in result
    assert "Proteins:" not in result
    assert "Produce:" not in result
    assert "Dairy:" not in result
    assert "Condiments:" not in result
    assert "Baking:" not in result
    assert "Nuts:" not in result
    assert "Pantry Items to Check:" not in result
