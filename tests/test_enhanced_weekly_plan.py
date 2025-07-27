"""
Unit tests for enhanced weekly plan with recipe integration.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date

from src.models.weekly_plan import PhaseRecommendations
from src.models.phase import FunctionalPhaseType
from src.models.recipe import Recipe, MealRecommendation, RecipeRecommendations
from src.services.weekly_plan import (
    create_phase_recommendations,
    format_recipe_suggestions,
    create_meal_plan_preview
)

class TestEnhancedWeeklyPlan:
    """Test suite for enhanced weekly plan functionality."""

    def create_sample_recipe(self, title="Test Recipe", prep_time=15, tags=None):
        """Create a sample recipe for testing."""
        if tags is None:
            tags = ["dinner"]
        
        return Recipe(
            title=title,
            phase="power",
            prep_time=prep_time,
            tags=tags,
            ingredients=["1 cup test ingredient", "2 tbsp olive oil"],
            instructions=["Step 1", "Step 2"],
            notes="Test notes",
            url="https://example.com",
            file_path="/test/path.md"
        )

    def test_enhanced_phase_recommendations_model(self):
        """Test that PhaseRecommendations model supports new recipe fields."""
        # Test backward compatibility - old format should work
        old_recommendations = PhaseRecommendations(
            fasting_protocol="16:8 intermittent fasting",
            foods=["avocado", "salmon", "eggs"],
            activities=["strength training", "HIIT"]
        )
        
        assert old_recommendations.fasting_protocol == "16:8 intermittent fasting"
        assert old_recommendations.foods == ["avocado", "salmon", "eggs"]
        assert old_recommendations.activities == ["strength training", "HIIT"]
        assert old_recommendations.supplements is None
        assert old_recommendations.recipe_suggestions is None
        assert old_recommendations.meal_plan_preview is None
        assert old_recommendations.shopping_preview is None

        # Test new format with recipe fields
        new_recommendations = PhaseRecommendations(
            fasting_protocol="16:8 intermittent fasting",
            foods=["avocado", "salmon", "eggs"],
            activities=["strength training", "HIIT"],
            supplements=["omega-3"],
            recipe_suggestions=[{"meal_type": "dinner", "recipes": []}],
            meal_plan_preview=["🍽️ Dinner: Air Fryer Salmon (15 min)"],
            shopping_preview=["olive oil", "salmon", "eggs"]
        )
        
        assert new_recommendations.recipe_suggestions is not None
        assert new_recommendations.meal_plan_preview is not None
        assert new_recommendations.shopping_preview is not None

    @patch('src.services.weekly_plan.RecipeService')
    def test_create_phase_recommendations_with_recipes(self, mock_recipe_service_class):
        """Test enhanced phase recommendations creation with recipes."""
        # Setup mock recipe service
        mock_service = Mock()
        mock_recipe_service_class.return_value = mock_service
        
        # Create sample recipe data
        sample_recipe = self.create_sample_recipe("Air Fryer Salmon", 15, ["dinner"])
        sample_meal = MealRecommendation(
            meal_type="dinner",
            recipes=[sample_recipe],
            prep_time_total=15
        )
        sample_recommendations = RecipeRecommendations(
            phase=FunctionalPhaseType.POWER,
            meals=[sample_meal],
            shopping_list_preview=["olive oil", "salmon"]
        )
        
        mock_service.get_recipe_recommendations.return_value = sample_recommendations
        
        # Test phase details
        phase_details = {
            'fasting_protocol': '16:8 intermittent fasting',
            'food_recommendations': ['avocado', 'salmon', 'eggs', 'kale', 'olive oil'],
            'activity_recommendations': ['strength training', 'HIIT', 'meditation']
        }
        
        # Test
        result = create_phase_recommendations(phase_details, FunctionalPhaseType.POWER)
        
        # Assertions
        assert isinstance(result, PhaseRecommendations)
        assert result.fasting_protocol == "16:8 intermittent fasting"
        assert result.foods == ["avocado", "salmon", "eggs"]  # Top 3
        assert result.activities == ["strength training", "HIIT", "meditation"]
        assert result.recipe_suggestions is not None
        assert result.meal_plan_preview is not None
        assert result.shopping_preview == ["olive oil", "salmon"]
        
        # Verify recipe service was called
        mock_service.get_recipe_recommendations.assert_called_once_with(FunctionalPhaseType.POWER)

    @patch('src.services.weekly_plan.RecipeService')
    def test_create_phase_recommendations_fallback(self, mock_recipe_service_class):
        """Test graceful fallback when recipe service fails."""
        # Setup mock to raise exception
        mock_service = Mock()
        mock_recipe_service_class.return_value = mock_service
        mock_service.get_recipe_recommendations.side_effect = Exception("Recipe service error")
        
        phase_details = {
            'fasting_protocol': '16:8 intermittent fasting',
            'food_recommendations': ['avocado', 'salmon', 'eggs'],
            'activity_recommendations': ['strength training', 'HIIT']
        }
        
        # Test
        result = create_phase_recommendations(phase_details, FunctionalPhaseType.POWER)
        
        # Should return basic recommendations without crashing
        assert isinstance(result, PhaseRecommendations)
        assert result.fasting_protocol == "16:8 intermittent fasting"
        assert result.foods == ["avocado", "salmon", "eggs"]
        assert result.activities == ["strength training", "HIIT"]
        # Recipe fields should be None due to fallback
        assert result.recipe_suggestions is None
        assert result.meal_plan_preview is None
        assert result.shopping_preview is None

    def test_format_recipe_suggestions(self):
        """Test recipe suggestion formatting for display."""
        # Create sample meal recommendations
        recipe1 = self.create_sample_recipe("Air Fryer Salmon", 15, ["dinner"])
        recipe2 = self.create_sample_recipe("Deviled Eggs", 10, ["snack"])
        
        meals = [
            MealRecommendation(
                meal_type="dinner",
                recipes=[recipe1],
                prep_time_total=15
            ),
            MealRecommendation(
                meal_type="snack", 
                recipes=[recipe2],
                prep_time_total=10
            )
        ]
        
        # Test
        suggestions = format_recipe_suggestions(meals)
        
        # Assertions
        assert len(suggestions) == 2
        
        dinner_suggestion = next(s for s in suggestions if s["meal_type"] == "dinner")
        assert dinner_suggestion["total_prep_time"] == 15
        assert len(dinner_suggestion["recipes"]) == 1
        assert dinner_suggestion["recipes"][0]["title"] == "Air Fryer Salmon"
        assert dinner_suggestion["recipes"][0]["prep_time"] == 15
        assert dinner_suggestion["recipes"][0]["tags"] == ["dinner"]
        assert dinner_suggestion["recipes"][0]["url"] == "https://example.com"

    def test_create_meal_plan_preview(self):
        """Test meal plan preview string generation."""
        # Create sample meal recommendations
        recipe1 = self.create_sample_recipe("Air Fryer Salmon", 15, ["dinner"])
        recipe2 = self.create_sample_recipe("Deviled Eggs", 10, ["snack"])
        recipe3 = self.create_sample_recipe("Fluffy Pancakes", 20, ["breakfast"])
        
        meals = [
            MealRecommendation(
                meal_type="dinner",
                recipes=[recipe1],
                prep_time_total=15
            ),
            MealRecommendation(
                meal_type="snack",
                recipes=[recipe2],
                prep_time_total=10
            ),
            MealRecommendation(
                meal_type="breakfast",
                recipes=[recipe3],
                prep_time_total=20
            )
        ]
        
        # Test
        preview = create_meal_plan_preview(meals)
        
        # Assertions
        assert len(preview) == 3
        
        # Check format: emoji + meal type + recipe name + prep time
        dinner_line = next(line for line in preview if "dinner" in line.lower())
        assert "🍽️" in dinner_line
        assert "Dinner: Air Fryer Salmon (15 min)" in dinner_line
        
        snack_line = next(line for line in preview if "snack" in line.lower())
        assert "🍿" in snack_line
        assert "Snack: Deviled Eggs (10 min)" in snack_line
        
        breakfast_line = next(line for line in preview if "breakfast" in line.lower())
        assert "🥞" in breakfast_line
        assert "Breakfast: Fluffy Pancakes (20 min)" in breakfast_line

    def test_create_meal_plan_preview_multiple_recipes(self):
        """Test meal plan preview with multiple recipes per meal type."""
        recipe1 = self.create_sample_recipe("Recipe 1", 15, ["dinner"])
        recipe2 = self.create_sample_recipe("Recipe 2", 20, ["dinner"])
        
        meals = [
            MealRecommendation(
                meal_type="dinner",
                recipes=[recipe1, recipe2],
                prep_time_total=35
            )
        ]
        
        # Test
        preview = create_meal_plan_preview(meals)
        
        # Should show both recipes with "or" between them
        assert len(preview) == 1
        dinner_line = preview[0]
        assert "🍽️" in dinner_line
        assert "Dinner:" in dinner_line
        assert "Recipe 1 (15 min)" in dinner_line
        assert "Recipe 2 (20 min)" in dinner_line
        assert " or " in dinner_line

    def test_create_meal_plan_preview_general_meal_type(self):
        """Test meal plan preview with general meal type."""
        recipe = self.create_sample_recipe("General Recipe", 15, ["healthy"])
        
        meals = [
            MealRecommendation(
                meal_type="general",
                recipes=[recipe],
                prep_time_total=15
            )
        ]
        
        # Test
        preview = create_meal_plan_preview(meals)
        
        # Should use general emoji
        assert len(preview) == 1
        line = preview[0]
        assert "🍴" in line  # General meal emoji
        assert "General: General Recipe (15 min)" in line

    def test_meal_plan_preview_empty_meals(self):
        """Test meal plan preview with empty meal list."""
        preview = create_meal_plan_preview([])
        assert preview == []

    def test_format_recipe_suggestions_empty_meals(self):
        """Test recipe suggestion formatting with empty meal list."""
        suggestions = format_recipe_suggestions([])
        assert suggestions == []

    def test_recipe_suggestions_multiple_recipes_per_meal(self):
        """Test formatting when meal has multiple recipe options."""
        recipe1 = self.create_sample_recipe("Option 1", 15, ["breakfast"])
        recipe2 = self.create_sample_recipe("Option 2", 20, ["breakfast"])
        
        meals = [
            MealRecommendation(
                meal_type="breakfast",
                recipes=[recipe1, recipe2],
                prep_time_total=35
            )
        ]
        
        suggestions = format_recipe_suggestions(meals)
        
        assert len(suggestions) == 1
        breakfast_suggestion = suggestions[0]
        assert breakfast_suggestion["meal_type"] == "breakfast"
        assert breakfast_suggestion["total_prep_time"] == 35
        assert len(breakfast_suggestion["recipes"]) == 2
        
        titles = [r["title"] for r in breakfast_suggestion["recipes"]]
        assert "Option 1" in titles
        assert "Option 2" in titles

    def test_backward_compatibility(self):
        """Test that enhanced system doesn't break existing functionality."""
        # Test that we can create PhaseRecommendations without recipe fields
        basic_rec = PhaseRecommendations(
            fasting_protocol="12:12",
            foods=["vegetables"],
            activities=["walking"]
        )
        
        assert basic_rec.fasting_protocol == "12:12"
        assert basic_rec.foods == ["vegetables"]
        assert basic_rec.activities == ["walking"]
        
        # New fields should default to None
        assert basic_rec.recipe_suggestions is None
        assert basic_rec.meal_plan_preview is None
        assert basic_rec.shopping_preview is None
