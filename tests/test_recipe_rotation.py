"""
Tests for recipe rotation functionality.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import time

from src.services.recipe import RecipeService
from src.models.recipe import Recipe, RecipeHistory
from src.utils.dynamo import create_pk, create_recipe_history_sk

@pytest.fixture
def mock_dynamo():
    """Create mock DynamoDB client."""
    with patch('src.services.recipe.get_dynamo') as mock_get_dynamo:
        # Create a mock DynamoDB client with all required methods
        mock_client = Mock()
        mock_client.put_item = Mock(return_value={})
        mock_client.query_items = Mock(return_value=[])
        
        # Make get_dynamo return our mock client
        mock_get_dynamo.return_value = mock_client
        
        yield mock_client

@pytest.fixture
def recipe_service(mock_dynamo):
    """Create RecipeService with mocked dependencies."""
    return RecipeService()

@pytest.fixture
def sample_recipes():
    """Create sample recipes for testing."""
    def create_recipe(title, meal_type):
        return Recipe(
            title=title,
            phase="power",
            prep_time=30,
            tags=[meal_type],
            ingredients=["ingredient 1", "ingredient 2"],
            instructions=["step 1", "step 2"],
            notes=None,
            url=None,
            file_path=f"/recipes/power/{title.lower().replace(' ', '-')}.md"
        )
    
    return {
        # Breakfast recipes - must be tagged correctly for rotation tests
        "oatmeal": create_recipe("Oatmeal", "breakfast"),
        "smoothie": create_recipe("Smoothie", "breakfast"),
        "eggs": create_recipe("Eggs Benedict", "breakfast"),  # This must be a breakfast recipe
        # Lunch recipes
        "salad": create_recipe("Salad", "lunch"),
        "soup": create_recipe("Soup", "lunch"),
        "sandwich": create_recipe("Sandwich", "lunch"),
        # Dinner recipes
        "pasta": create_recipe("Pasta", "dinner"),
        "chicken": create_recipe("Chicken", "dinner"),
        "fish": create_recipe("Fish", "dinner"),
        # Snack recipes
        "nuts": create_recipe("Mixed Nuts", "snack"),
        "fruit": create_recipe("Fresh Fruit", "snack"),
        "yogurt": create_recipe("Greek Yogurt", "snack")
    }

def test_save_recipe_history(recipe_service, mock_dynamo):
    """Test saving recipe history entries."""
    # Setup
    user_id = "123"
    recipe_id = "oatmeal"
    meal_type = "breakfast"
    phase = "power"
    
    # Execute
    recipe_service.save_recipe_history(user_id, recipe_id, meal_type, phase)
    
    # Verify
    mock_dynamo.put_item.assert_called_once()
    item = mock_dynamo.put_item.call_args[0][0]
    
    assert item['PK'] == create_pk(user_id)
    assert item['SK'].startswith(f"RECIPE#{recipe_id}")
    assert item['meal_type'] == meal_type
    assert item['phase'] == phase
    assert 'ttl' in item
    
    # Verify TTL is ~30 days in future
    now = time.time()
    assert abs(item['ttl'] - (now + 30 * 24 * 60 * 60)) < 60  # Allow 1 minute variance

def test_get_recipe_history(recipe_service, mock_dynamo):
    """Test retrieving recipe history."""
    # Setup
    user_id = "123"
    mock_items = [
            {
                'PK': create_pk(user_id),
                'SK': f"RECIPE#oatmeal#2025-07-01T10:00:00",
                'meal_type': 'breakfast',
                'phase': 'power'
            },
            {
                'PK': create_pk(user_id),
                'SK': f"RECIPE#salad#2025-07-01T12:00:00",
                'meal_type': 'lunch',
                'phase': 'power'
            }
        ]
    mock_dynamo.query_items.return_value = mock_items
    
    # Execute
    history = recipe_service.get_recipe_history(user_id)
    
    # Verify
    assert len(history) == 2
    assert 'oatmeal' in history
    assert 'salad' in history
    mock_dynamo.query_items.assert_called_once()

def test_recipe_rotation(recipe_service, mock_dynamo, sample_recipes):
    """Test that recipes are rotated based on history."""
    # Setup
    user_id = "123"
    phase = "power"
    
    # Mock recent recipe history
    mock_dynamo.query_items.return_value = [
            {
                'PK': create_pk(user_id),
                'SK': f"RECIPE#oatmeal#2025-07-01T10:00:00",
                'meal_type': 'breakfast',
                'phase': 'power'
            },
            {
                'PK': create_pk(user_id),
                'SK': f"RECIPE#smoothie#2025-07-01T10:00:00",
                'meal_type': 'breakfast',
                'phase': 'power'
            }
        ]
    
    # Mock recipe files
    with patch('pathlib.Path.glob') as mock_glob, \
         patch.object(recipe_service.parser, 'parse_recipe_file') as mock_parse:
        
        # Setup mock files with proper string conversion
        def create_mock_file(name):
            mock_file = Mock()
            mock_file.name = f"{name}.md"
            mock_file.stem = name
            mock_file.__str__ = Mock(return_value=f"/recipes/power/{name}.md")
            return mock_file

        mock_files = [
            create_mock_file('oatmeal'),
            create_mock_file('smoothie'),
            create_mock_file('eggs')
        ]
        mock_glob.return_value = mock_files
        
        # Setup mock parsing
        def mock_parse_recipe(path):
            stem = str(path).split('/')[-1].replace('.md', '')
            return sample_recipes.get(stem)
        mock_parse.side_effect = mock_parse_recipe
        
        # Execute
        recipe_service.load_recipes_for_meal_planning(phase=phase, user_id=user_id)
        breakfast_recipes = recipe_service.get_recipes_by_meal_type('breakfast', phase=phase)
        
        # Verify
        recipe_ids = {r['id'] for r in breakfast_recipes}
        # Should not include recently shown recipes
        assert 'oatmeal' not in recipe_ids
        assert 'smoothie' not in recipe_ids
        # Should include fresh recipe
        assert 'eggs' in recipe_ids

def test_fallback_to_recent_recipes(recipe_service, mock_dynamo, sample_recipes):
    """Test fallback to recent recipes if not enough fresh ones available."""
    # Setup
    user_id = "123"
    phase = "power"
    
    # Mock that ALL breakfast recipes were recently shown
    mock_dynamo.query_items.return_value = [
        {
            'PK': create_pk(user_id),
            'SK': f"RECIPE#{recipe_id}#2025-07-01T10:00:00",
            'meal_type': 'breakfast',
            'phase': 'power'
        }
        for recipe_id in ['oatmeal', 'smoothie', 'eggs']
    ]
    
    # Mock recipe files
    with patch('pathlib.Path.glob') as mock_glob, \
         patch.object(recipe_service.parser, 'parse_recipe_file') as mock_parse:
        
        # Setup mock files with proper string conversion
        def create_mock_file(name):
            mock_file = Mock()
            mock_file.name = f"{name}.md"
            mock_file.stem = name
            mock_file.__str__ = Mock(return_value=f"/recipes/power/{name}.md")
            return mock_file

        mock_files = [
            create_mock_file('oatmeal'),
            create_mock_file('smoothie'),
            create_mock_file('eggs')
        ]
        mock_glob.return_value = mock_files
        
        # Setup mock parsing
        def mock_parse_recipe(path):
            stem = str(path).split('/')[-1].replace('.md', '')
            return sample_recipes.get(stem)
        mock_parse.side_effect = mock_parse_recipe
        
        # Execute
        recipe_service.load_recipes_for_meal_planning(phase=phase, user_id=user_id)
        breakfast_recipes = recipe_service.get_recipes_by_meal_type('breakfast', phase=phase)
        
        # Verify
        # Should still return recipes even though all were recently shown
        assert len(breakfast_recipes) > 0
        recipe_ids = {r['id'] for r in breakfast_recipes}
        # Should use some of the recent recipes
        assert len(recipe_ids.intersection({'oatmeal', 'smoothie', 'eggs'})) > 0

def test_load_recipes_without_history(recipe_service, mock_dynamo, sample_recipes):
    """Test loading recipes when no history exists."""
    # Setup
    user_id = "123"
    phase = "power"
    
    # Mock empty recipe history
    mock_dynamo.query_items.return_value = []
    
    # Mock recipe files
    with patch('pathlib.Path.glob') as mock_glob, \
         patch.object(recipe_service.parser, 'parse_recipe_file') as mock_parse:
        
        # Setup mock files with proper string conversion
        def create_mock_file(name):
            mock_file = Mock()
            mock_file.name = f"{name}.md"
            mock_file.stem = name
            mock_file.__str__ = Mock(return_value=f"/recipes/power/{name}.md")
            return mock_file

        mock_files = [
            create_mock_file('oatmeal'),
            create_mock_file('smoothie'),
            create_mock_file('eggs')
        ]
        mock_glob.return_value = mock_files
        
        # Setup mock parsing
        def mock_parse_recipe(path):
            stem = str(path).split('/')[-1].replace('.md', '')
            return sample_recipes.get(stem)
        mock_parse.side_effect = mock_parse_recipe
        
        # Execute
        recipe_service.load_recipes_for_meal_planning(phase=phase, user_id=user_id)
        breakfast_recipes = recipe_service.get_recipes_by_meal_type('breakfast', phase=phase)
        
        # Verify
        assert len(breakfast_recipes) > 0
        # All recipes should be available since there's no history
        recipe_ids = {r['id'] for r in breakfast_recipes}
        assert recipe_ids.issubset({'oatmeal', 'smoothie', 'eggs'})

def test_history_error_handling(recipe_service, mock_dynamo):
    """Test graceful handling of history retrieval errors."""
    # Setup
    user_id = "123"
    phase = "power"
    
    # Mock DynamoDB query failure
    mock_dynamo.query_items.side_effect = Exception("DynamoDB error")
    
    # Mock recipe files
    with patch('pathlib.Path.glob') as mock_glob, \
         patch.object(recipe_service.parser, 'parse_recipe_file') as mock_parse:
        
        # Setup mock file with proper string conversion
        def create_mock_file(name):
            mock_file = Mock()
            mock_file.name = f"{name}.md"
            mock_file.stem = name
            mock_file.__str__ = Mock(return_value=f"/recipes/power/{name}.md")
            return mock_file

        mock_files = [create_mock_file('recipe')]
        mock_glob.return_value = mock_files

        # Setup mock recipe
        mock_parse.return_value = Recipe(
            title="Test Recipe",
            phase="power",
            prep_time=30,
            tags=["breakfast"],
            ingredients=["ingredient"],
            instructions=["step"],
            notes=None,
            url=None,
            file_path="/test/recipe.md"
        )
        
        # Execute - should not raise exception
        recipe_service.load_recipes_for_meal_planning(phase=phase, user_id=user_id)
        
        # Verify recipes still loaded despite history error
        breakfast_recipes = recipe_service.get_recipes_by_meal_type('breakfast', phase=phase)
        assert len(breakfast_recipes) > 0
