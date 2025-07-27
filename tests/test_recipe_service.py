"""
Unit tests for recipe service.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from src.services.recipe import RecipeService
from src.models.recipe import Recipe, MealRecommendation, RecipeRecommendations
from src.models.phase import FunctionalPhaseType

class TestRecipeService:
    """Test suite for RecipeService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = RecipeService()

    def create_sample_recipe(self, title="Test Recipe", phase="power", tags=None, prep_time=15):
        """Create a sample recipe for testing."""
        if tags is None:
            tags = ["dinner"]
        
        return Recipe(
            title=title,
            phase=phase,
            prep_time=prep_time,
            tags=tags,
            ingredients=["1 cup test ingredient", "2 tbsp olive oil"],
            instructions=["Step 1", "Step 2"],
            notes="Test notes",
            url="https://example.com",
            file_path="/test/path.md"
        )

    def test_phase_folder_mapping(self):
        """Test that phase types map to correct folder names."""
        assert self.service.phase_folders[FunctionalPhaseType.POWER] == "power"
        assert self.service.phase_folders[FunctionalPhaseType.MANIFESTATION] == "manifestation"
        assert self.service.phase_folders[FunctionalPhaseType.NURTURE] == "nurture"

    @patch('os.path.exists')
    @patch('os.listdir')
    @patch.object(RecipeService, 'parser')
    def test_load_recipes_by_phase_success(self, mock_parser, mock_listdir, mock_exists):
        """Test successful recipe loading by phase."""
        # Setup mocks
        mock_exists.return_value = True
        mock_listdir.return_value = ['recipe1.md', 'recipe2.md', 'not_a_recipe.txt']
        
        # Create sample recipes
        recipe1 = self.create_sample_recipe("Recipe 1", "power")
        recipe2 = self.create_sample_recipe("Recipe 2", "power")
        
        mock_parser.parse_recipe_file.side_effect = [recipe1, recipe2, None]
        
        # Test
        recipes = self.service.load_recipes_by_phase(FunctionalPhaseType.POWER)
        
        # Assertions
        assert len(recipes) == 2
        assert recipes[0].title == "Recipe 1"
        assert recipes[1].title == "Recipe 2"
        
        # Verify caching
        cached_recipes = self.service.load_recipes_by_phase(FunctionalPhaseType.POWER)
        assert cached_recipes == recipes
        mock_parser.parse_recipe_file.assert_called_with('recipes/power/recipe2.md')

    @patch('os.path.exists')
    def test_load_recipes_missing_directory(self, mock_exists):
        """Test behavior when recipe directory doesn't exist."""
        mock_exists.return_value = False
        
        recipes = self.service.load_recipes_by_phase(FunctionalPhaseType.POWER)
        
        assert recipes == []

    @patch('os.path.exists')
    @patch('os.listdir')
    def test_load_recipes_directory_error(self, mock_listdir, mock_exists):
        """Test handling of directory scanning errors."""
        mock_exists.return_value = True
        mock_listdir.side_effect = OSError("Permission denied")
        
        recipes = self.service.load_recipes_by_phase(FunctionalPhaseType.POWER)
        
        assert recipes == []

    def test_balance_meal_types(self):
        """Test meal type balancing functionality."""
        # Create recipes with different meal types
        recipes = [
            self.create_sample_recipe("Breakfast Recipe", tags=["breakfast"]),
            self.create_sample_recipe("Lunch Recipe", tags=["lunch"]),
            self.create_sample_recipe("Dinner Recipe 1", tags=["dinner"]),
            self.create_sample_recipe("Dinner Recipe 2", tags=["dinner"]),
            self.create_sample_recipe("Snack Recipe", tags=["snack"]),
        ]
        
        meal_recs = self.service.balance_meal_types(recipes)
        
        # Should have recommendations for each meal type
        meal_types = {meal.meal_type for meal in meal_recs}
        assert "breakfast" in meal_types
        assert "lunch" in meal_types
        assert "dinner" in meal_types
        assert "snack" in meal_types
        
        # Each meal recommendation should have recipes
        for meal in meal_recs:
            assert len(meal.recipes) > 0
            assert meal.prep_time_total > 0

    def test_balance_meal_types_no_specific_tags(self):
        """Test meal balancing when recipes have no specific meal tags."""
        recipes = [
            self.create_sample_recipe("General Recipe 1", tags=["healthy"]),
            self.create_sample_recipe("General Recipe 2", tags=["quick"]),
        ]
        
        meal_recs = self.service.balance_meal_types(recipes)
        
        # Should create a general meal recommendation
        assert len(meal_recs) == 1
        assert meal_recs[0].meal_type == "general"
        assert len(meal_recs[0].recipes) == 2

    def test_generate_shopping_preview(self):
        """Test shopping list generation."""
        recipes = [
            Recipe(
                title="Recipe 1",
                phase="power",
                prep_time=15,
                tags=["dinner"],
                ingredients=["1 cup olive oil", "2 lbs salmon", "1 bunch kale"],
                instructions=["Step 1"],
                notes=None,
                url=None,
                file_path="/test1.md"
            ),
            Recipe(
                title="Recipe 2", 
                phase="power",
                prep_time=20,
                tags=["lunch"],
                ingredients=["2 tbsp olive oil", "1 avocado", "salt and pepper"],
                instructions=["Step 1"],
                notes=None,
                url=None,
                file_path="/test2.md"
            )
        ]
        
        shopping_list = self.service.generate_shopping_preview(recipes)
        
        assert len(shopping_list) > 0
        # Should extract main ingredients (olive oil appears in both recipes)
        ingredient_str = " ".join(shopping_list).lower()
        assert "olive oil" in ingredient_str or "oil" in ingredient_str

    def test_generate_shopping_preview_empty_recipes(self):
        """Test shopping list generation with empty recipe list."""
        shopping_list = self.service.generate_shopping_preview([])
        assert shopping_list == []

    @patch.object(RecipeService, 'load_recipes_by_phase')
    @patch.object(RecipeService, 'balance_meal_types')
    @patch.object(RecipeService, 'generate_shopping_preview')
    def test_get_recipe_recommendations_success(self, mock_shopping, mock_balance, mock_load):
        """Test successful recipe recommendation generation."""
        # Setup mocks
        sample_recipes = [self.create_sample_recipe()]
        mock_load.return_value = sample_recipes
        
        sample_meal = MealRecommendation(
            meal_type="dinner",
            recipes=sample_recipes,
            prep_time_total=15
        )
        mock_balance.return_value = [sample_meal]
        mock_shopping.return_value = ["olive oil", "salmon"]
        
        # Test
        result = self.service.get_recipe_recommendations(FunctionalPhaseType.POWER)
        
        # Assertions
        assert isinstance(result, RecipeRecommendations)
        assert result.phase == FunctionalPhaseType.POWER
        assert len(result.meals) == 1
        assert result.shopping_list_preview == ["olive oil", "salmon"]

    @patch.object(RecipeService, 'load_recipes_by_phase')
    def test_get_recipe_recommendations_no_recipes(self, mock_load):
        """Test recommendation generation when no recipes are found."""
        mock_load.return_value = []
        
        result = self.service.get_recipe_recommendations(FunctionalPhaseType.POWER)
        
        assert isinstance(result, RecipeRecommendations)
        assert result.phase == FunctionalPhaseType.POWER
        assert result.meals == []
        assert result.shopping_list_preview == []

    @patch.object(RecipeService, 'load_recipes_by_phase')
    def test_get_recipe_recommendations_error_handling(self, mock_load):
        """Test error handling in recipe recommendation generation."""
        mock_load.side_effect = Exception("Test error")
        
        result = self.service.get_recipe_recommendations(FunctionalPhaseType.POWER)
        
        # Should return empty recommendation instead of crashing
        assert isinstance(result, RecipeRecommendations)
        assert result.meals == []
        assert result.shopping_list_preview == []

    def test_select_diverse_recipes(self):
        """Test recipe diversity selection."""
        recipes = [
            Recipe(
                title="Salmon Recipe",
                phase="power",
                prep_time=10,
                tags=["dinner"],
                ingredients=["salmon", "olive oil", "lemon"],
                instructions=["Step 1"],
                notes=None,
                url=None,
                file_path="/salmon.md"
            ),
            Recipe(
                title="Chicken Recipe",
                phase="power", 
                prep_time=25,
                tags=["dinner"],
                ingredients=["chicken", "garlic", "herbs"],
                instructions=["Step 1"],
                notes=None,
                url=None,
                file_path="/chicken.md"
            ),
            Recipe(
                title="Another Salmon Recipe",
                phase="power",
                prep_time=15,
                tags=["dinner"],
                ingredients=["salmon", "butter", "vegetables"],
                instructions=["Step 1"],
                notes=None,
                url=None,
                file_path="/salmon2.md"
            )
        ]
        
        selected = self.service._select_diverse_recipes(recipes, max_recipes=2)
        
        assert len(selected) == 2
        # Should prefer diversity - salmon and chicken over two salmon recipes
        titles = [recipe.title for recipe in selected]
        assert "Salmon Recipe" in titles
        assert "Chicken Recipe" in titles

    def test_extract_main_ingredient(self):
        """Test main ingredient extraction from ingredient lines."""
        test_cases = [
            ("1 cup quinoa", "quinoa"),
            ("2 tablespoons olive oil", "olive oil"),
            ("1/2 pound salmon fillet", "salmon fillet"),
            ("Salt and pepper to taste", "salt pepper"),
            ("3 cups (750ml) water", "water"),
        ]
        
        for ingredient_line, expected in test_cases:
            result = self.service._extract_main_ingredient(ingredient_line)
            if expected:
                assert expected.lower() in result.lower(), f"Expected '{expected}' in '{result}' for input '{ingredient_line}'"

    def test_caching_behavior(self):
        """Test that recipe caching works correctly."""
        # Clear any existing cache
        self.service._recipe_cache.clear()
        
        with patch.object(self.service, 'parser') as mock_parser, \
             patch('os.path.exists', return_value=True), \
             patch('os.listdir', return_value=['test.md']):
            
            sample_recipe = self.create_sample_recipe()
            mock_parser.parse_recipe_file.return_value = sample_recipe
            
            # First call should parse
            recipes1 = self.service.load_recipes_by_phase(FunctionalPhaseType.POWER)
            
            # Second call should use cache
            recipes2 = self.service.load_recipes_by_phase(FunctionalPhaseType.POWER)
            
            # Should be the same recipes
            assert recipes1 == recipes2
            
            # Parser should only be called once
            mock_parser.parse_recipe_file.assert_called_once()
