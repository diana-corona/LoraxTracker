"""
Tests for recipe selection service functionality.
"""
from typing import List
from src.models.recipe import Recipe, MealRecommendation
from src.services.recipe_selection import (
    RecipeSelectionService,
    MealSelection,
    ShoppingList
)

def test_format_recipe_options():
    """Test formatting recipe options with embedded URLs."""
    recipes = [
        Recipe(
            title="Almond Blueberry Muffins",
            phase=None,
            prep_time=35,
            tags=["breakfast", "snack"],
            ingredients=["3 cups almond flour", "6 large eggs", "1½ cups blueberries"],
            instructions=["Preheat oven", "Mix ingredients"],
            notes=None,
            url="https://example.com/muffins",
            file_path="recipes/power/almond-blueberry-muffins.md"
        ),
        Recipe(
            title="Budget Vegetable Frittata",
            phase=None,
            prep_time=35,
            tags=["breakfast"],
            ingredients=["8 eggs", "spinach", "mushrooms"],
            instructions=["Preheat oven", "Whisk eggs"],
            notes=None,
            url="https://example.com/frittata",
            file_path="recipes/power/budget-vegetable-frittata.md"
        )
    ]
    
    recommendations = [
        MealRecommendation(
            meal_type="breakfast",
            recipes=recipes,
            prep_time_total=70
        )
    ]
    
    formatted = RecipeSelectionService.format_recipe_options(recommendations)
    
    assert "Please select your preferred recipes:" in formatted
    assert "🥞 Breakfast (choose 1):" in formatted
    assert "[Almond Blueberry Muffins](https://example.com/muffins)" in formatted
    assert "[Budget Vegetable Frittata](https://example.com/frittata)" in formatted
    assert "(35 min)" in formatted

def test_generate_shopping_list():
    """Test generating shopping list with categorized ingredients."""
    recipe = Recipe(
        title="Almond Blueberry Muffins",
        phase=None,
        prep_time=35,
        tags=["breakfast", "snack"],
        ingredients=[
            "3 cups almond flour",
            "1 tablespoon xanthan gum",
            "1 teaspoon salt",  # Basic ingredient
            "6 large eggs",
            "1½ cups blueberries",
            "2 teaspoons vanilla extract"  # Basic ingredient
        ],
        instructions=["Preheat oven", "Mix ingredients"],
        notes=None,
        url="https://example.com/muffins",
        file_path="recipes/power/almond-blueberry-muffins.md"
    )
    
    selection = MealSelection(meal_type="breakfast", recipe=recipe)
    shopping_list = RecipeSelectionService.generate_shopping_list([selection])
    
    # Check categories
    assert "almond flour" in shopping_list.categories["pantry"]
    assert "xanthan gum" in shopping_list.categories["pantry"]
    assert "eggs" in shopping_list.categories["proteins"]
    assert "blueberries" in shopping_list.categories["fruits"]
    
    # Check basic ingredients
    assert "salt" in shopping_list.basic_ingredients
    assert "vanilla extract" in shopping_list.basic_ingredients

def test_format_shopping_list():
    """Test formatting shopping list with categories and icons."""
    categories = {
        "proteins": {"eggs", "chicken breast"},
        "fruits": {"blueberries", "banana"},
        "pantry": {"almond flour", "xanthan gum"},
        "vegetables": set(),  # Empty category should be excluded
        "others": {"honey"}
    }
    basic_needed = {"salt", "vanilla extract"}
    
    shopping_list = ShoppingList(categories=categories, basic_ingredients=basic_needed)
    formatted = RecipeSelectionService.format_shopping_list(shopping_list)
    
    assert "🛒 Shopping List" in formatted
    assert "🥩 Proteins:" in formatted
    assert "  • eggs" in formatted
    assert "🍎 Fruits:" in formatted
    assert "  • blueberries" in formatted
    assert "🥫 Pantry:" in formatted
    assert "  • almond flour" in formatted
    assert "vegetables" not in formatted  # Empty category excluded
    assert "📝 Basic Ingredients to Check:" in formatted
    assert "  • salt" in formatted
