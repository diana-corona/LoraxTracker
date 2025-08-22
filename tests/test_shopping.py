"""
Tests for shopping list generation functionality.
"""
import pytest
from datetime import date

from src.models.phase import Phase, TraditionalPhaseType, FunctionalPhaseType
from src.services.shopping import ShoppingListGenerator

@pytest.fixture
def power_phase() -> Phase:
    """Create a Power phase for testing."""
    return Phase(
        traditional_phase=TraditionalPhaseType.MENSTRUATION,
        functional_phase=FunctionalPhaseType.POWER,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 5),
        duration=5,
        functional_phase_duration=8,
        functional_phase_start=date(2024, 1, 1),
        functional_phase_end=date(2024, 1, 8),
        typical_symptoms=["test symptom"],
        dietary_style="Ketobiotic",
        fasting_protocol="13-72 hours",
        food_recommendations=["test food"],
        activity_recommendations=["test activity"]
    )

def test_shopping_list_generation(power_phase: Phase):
    """Test basic shopping list generation."""
    shopping_list = ShoppingListGenerator.generate_weekly_list(power_phase)
    
    # Verify all categories are present
    assert "proteins" in shopping_list
    assert "vegetables" in shopping_list
    assert "fruits" in shopping_list
    assert "fats" in shopping_list
    assert "carbohydrates" in shopping_list
    assert "supplements" in shopping_list
    assert "others" in shopping_list
    
    # Verify specific Power phase items
    assert "avocado" in shopping_list["fats"]
    assert "broccoli" in shopping_list["vegetables"]
    assert "eggs" in shopping_list["proteins"]
    assert "kimchi" in shopping_list["others"]

def test_power_phase_ingredients():
    """Test Power phase specific ingredients."""
    items = ShoppingListGenerator._get_phase_ingredients(FunctionalPhaseType.POWER)
    
    # Verify ketogenic focus
    assert "coconut oil" in items["fats"]
    assert "fish" in items["proteins"]
    assert all(veg in items["vegetables"] for veg in ["broccoli", "kale", "spinach"])
    assert "kefir" in items["others"]

def test_manifestation_phase_ingredients():
    """Test Manifestation phase specific ingredients."""
    items = ShoppingListGenerator._get_phase_ingredients(FunctionalPhaseType.MANIFESTATION)
    
    # Verify transition foods
    assert "beetroot" in items["vegetables"]
    assert "grapefruit" in items["fruits"]
    assert "almonds" in items["others"]

def test_nurture_phase_ingredients():
    """Test Nurture phase specific ingredients."""
    items = ShoppingListGenerator._get_phase_ingredients(FunctionalPhaseType.NURTURE)
    
    # Verify complex carbs and comfort foods
    assert "quinoa" in items["carbohydrates"]
    assert "dates" in items["fruits"]
    assert "magnesium" in items["supplements"]
    assert "ginger" in items["others"]
    assert "turkey" in items["proteins"]

def test_weekly_list_combination():
    """Test shopping list combining multiple phases."""
    phase = Phase(
        traditional_phase=TraditionalPhaseType.LUTEAL,
        functional_phase=FunctionalPhaseType.NURTURE,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 5),
        duration=5,
        functional_phase_duration=10,
        functional_phase_start=date(2024, 1, 1),
        functional_phase_end=date(2024, 1, 10),
        typical_symptoms=["test symptom"],
        dietary_style="Hormone Feasting",
        fasting_protocol="No fasting",
        food_recommendations=["test food"],
        activity_recommendations=["test activity"]
    )
    
    shopping_list = ShoppingListGenerator.generate_weekly_list(phase)
    
    # Should include items from multiple phases due to week-long prediction
    assert any("avocado" in item for item in shopping_list["fats"])  # Power phase
    assert any("beetroot" in item for item in shopping_list["vegetables"])  # Manifestation
    assert any("quinoa" in item for item in shopping_list["carbohydrates"])  # Nurture

def test_shopping_list_formatting():
    """Test shopping list string formatting."""
    items = {
        "proteins": ["eggs", "fish"],
        "vegetables": ["broccoli"],
        "fruits": [],  # Empty category
        "others": ["tea"]
    }
    
    formatted = ShoppingListGenerator.generate_shopping_list(items)
    
    # Check formatting
    assert "🛒 Shopping List" in formatted
    assert "🥩 Proteins:" in formatted
    assert "  • eggs" in formatted
    assert "🥬 Vegetables:" in formatted
    assert "Fruits" not in formatted  # Empty category should be omitted
    assert "🧂 Others:" in formatted
