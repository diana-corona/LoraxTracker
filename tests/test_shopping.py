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
        typical_symptoms=["test symptom"],
        dietary_style="Ketobiótico",
        fasting_protocol="13-72 horas",
        food_recommendations=["test food"],
        activity_recommendations=["test activity"]
    )

def test_shopping_list_generation(power_phase: Phase):
    """Test basic shopping list generation."""
    shopping_list = ShoppingListGenerator.generate_weekly_list(power_phase)
    
    # Verify all categories are present
    assert "proteinas" in shopping_list
    assert "vegetales" in shopping_list
    assert "frutas" in shopping_list
    assert "grasas" in shopping_list
    assert "carbohidratos" in shopping_list
    assert "suplementos" in shopping_list
    assert "otros" in shopping_list
    
    # Verify specific Power phase items
    assert "aguacate" in shopping_list["grasas"]
    assert "brócoli" in shopping_list["vegetales"]
    assert "huevos" in shopping_list["proteinas"]
    assert "kimchi" in shopping_list["otros"]

def test_power_phase_ingredients():
    """Test Power phase specific ingredients."""
    items = ShoppingListGenerator._get_phase_ingredients(FunctionalPhaseType.POWER)
    
    # Verify ketogenic focus
    assert "aceite de coco" in items["grasas"]
    assert "pescado" in items["proteinas"]
    assert all(veg in items["vegetales"] for veg in ["brócoli", "col rizada", "espinaca"])
    assert "kéfir" in items["otros"]

def test_manifestation_phase_ingredients():
    """Test Manifestation phase specific ingredients."""
    items = ShoppingListGenerator._get_phase_ingredients(FunctionalPhaseType.MANIFESTATION)
    
    # Verify transition foods
    assert "remolacha" in items["vegetales"]
    assert "toronja" in items["frutas"]
    assert "almendras" in items["otros"]

def test_nurture_phase_ingredients():
    """Test Nurture phase specific ingredients."""
    items = ShoppingListGenerator._get_phase_ingredients(FunctionalPhaseType.NURTURE)
    
    # Verify complex carbs and comfort foods
    assert "quinoa" in items["carbohidratos"]
    assert "dátiles" in items["frutas"]
    assert "magnesio" in items["suplementos"]
    assert "jengibre" in items["otros"]
    assert "pavo" in items["proteinas"]

def test_weekly_list_combination():
    """Test shopping list combining multiple phases."""
    phase = Phase(
        traditional_phase=TraditionalPhaseType.LUTEAL,
        functional_phase=FunctionalPhaseType.NURTURE,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 5),
        duration=5,
        typical_symptoms=["test symptom"],
        dietary_style="Hormone Feasting",
        fasting_protocol="No ayuno",
        food_recommendations=["test food"],
        activity_recommendations=["test activity"]
    )
    
    shopping_list = ShoppingListGenerator.generate_weekly_list(phase)
    
    # Should include items from multiple phases due to week-long prediction
    assert any("aguacate" in item for item in shopping_list["grasas"])  # Power phase
    assert any("remolacha" in item for item in shopping_list["vegetales"])  # Manifestation
    assert any("quinoa" in item for item in shopping_list["carbohidratos"])  # Nurture

def test_shopping_list_formatting():
    """Test shopping list string formatting."""
    items = {
        "proteinas": ["huevos", "pescado"],
        "vegetales": ["brócoli"],
        "frutas": [],  # Empty category
        "otros": ["té"]
    }
    
    formatted = ShoppingListGenerator.generate_shopping_list(items)
    
    # Check formatting
    assert "🛒 Lista de Compras" in formatted
    assert "🥩 Proteinas:" in formatted
    assert "  • huevos" in formatted
    assert "🥬 Vegetales:" in formatted
    assert "Frutas" not in formatted  # Empty category should be omitted
    assert "🧂 Otros:" in formatted
