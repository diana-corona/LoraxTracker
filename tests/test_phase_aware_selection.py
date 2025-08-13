"""Tests for phase-aware recipe selection functionality."""
import pytest
from datetime import date, timedelta
from unittest.mock import Mock, patch
from typing import List

from src.models.phase import FunctionalPhaseType, TraditionalPhaseType
from src.models.weekly_plan import PhaseGroup, WeeklyPlan, PhaseRecommendations
from src.services.week_analysis import (
    calculate_week_analysis,
    format_week_analysis,
    WeekAnalysis,
    PhaseDistribution
)
from src.services.recipe_selection_storage import (
    RecipeSelectionStorage,
    RecipeSelection,
    SelectionMode,
    PhaseRecipeSelection
)
from src.utils.telegram.keyboards import create_recipe_selection_keyboard

def create_test_phase_group(
    start_date: date,
    days: int,
    phase: FunctionalPhaseType
) -> PhaseGroup:
    """Helper to create test phase groups."""
    phase_recs = PhaseRecommendations(
        fasting_protocol="16/8",
        foods=["food1", "food2"],
        activities=["activity1", "activity2"]
    )
    return PhaseGroup(
        start_date=start_date,
        end_date=start_date + timedelta(days=days-1),
        traditional_phase=TraditionalPhaseType.FOLLICULAR,  # Simplified for testing
        functional_phase=phase,
        functional_phase_duration=days,
        functional_phase_start=start_date,
        functional_phase_end=start_date + timedelta(days=days-1),
        recommendations=phase_recs,
        next_phase_recommendations=None,  # Updated to None instead of empty list
        has_phase_transition=False,
        transition_message=None
    )

class TestWeekAnalysis:
    """Test suite for week analysis functionality."""
    
    def test_calculate_simple_week(self):
        """Test calculation with a single phase week."""
        start = date(2025, 1, 1)
        groups = [
            create_test_phase_group(start, 7, FunctionalPhaseType.POWER)
        ]
        
        analysis = calculate_week_analysis(groups)
        
        assert analysis.total_days == 7
        assert len(analysis.phase_distribution) == 1
        assert "power" in analysis.phase_distribution
        assert analysis.phase_distribution["power"].days == 7
        assert analysis.phase_distribution["power"].percentage == 1.0
        
    def test_calculate_mixed_week(self):
        """Test calculation with multiple phases in a week."""
        start = date(2025, 1, 1)
        groups = [
            create_test_phase_group(start, 2, FunctionalPhaseType.POWER),
            create_test_phase_group(start + timedelta(days=2), 5, FunctionalPhaseType.NURTURE)
        ]
        
        analysis = calculate_week_analysis(groups)
        
        assert analysis.total_days == 7
        assert len(analysis.phase_distribution) == 2
        assert analysis.phase_distribution["power"].days == 2
        assert analysis.phase_distribution["nurture"].days == 5
        assert abs(analysis.phase_distribution["power"].percentage - 0.29) < 0.01
        assert abs(analysis.phase_distribution["nurture"].percentage - 0.71) < 0.01

    def test_format_single_phase(self):
        """Test formatting for single phase week."""
        analysis = WeekAnalysis(
            total_days=7,
            phase_distribution={
                "power": PhaseDistribution(
                    days=7,
                    percentage=1.0,
                    recommended_recipes=1.0
                )
            },
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 7)
        )
        
        formatted = format_week_analysis(analysis)
        assert len(formatted) == 2  # Header + 1 phase
        assert formatted == [
            "📊 Week Analysis:",
            "- Power Phase ⚡: 7 days (100% of week)"
        ]
        
    def test_format_mixed_phases(self):
        """Test formatting for mixed phase week."""
        analysis = WeekAnalysis(
            total_days=7,
            phase_distribution={
                "power": PhaseDistribution(
                    days=2,
                    percentage=0.29,
                    recommended_recipes=0.29
                ),
                "nurture": PhaseDistribution(
                    days=5,
                    percentage=0.71,
                    recommended_recipes=0.71
                )
            },
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 7)
        )
        
        formatted = format_week_analysis(analysis)
        assert len(formatted) == 7  # Header + 2 phases + blank line + strategy + 2 recommendations
        assert formatted == [
            "📊 Week Analysis:",
            "- Nurture Phase 🌱: 5 days (71% of week)",
            "- Power Phase ⚡: 2 days (29% of week)",
            "",
            "🍽️ Recipe Distribution Strategy:",
            "- Select ~71% Nurture phase recipes 🌱",
            "- Select ~29% Power phase recipes ⚡"
        ]

class TestRecipeSelection:
    """Test suite for enhanced recipe selection storage."""
    
    def test_single_phase_selection(self):
        """Test basic single phase selection."""
        selection = RecipeSelection(mode=SelectionMode.SINGLE)
        selection.add_selection("breakfast", "recipe1")
        
        assert len(selection.breakfast) == 1
        assert selection.breakfast[0].recipe_id == "recipe1"
        assert selection.breakfast[0].phase is None
        
    def test_multi_phase_selection(self):
        """Test multi-phase selection mode."""
        selection = RecipeSelection(mode=SelectionMode.MULTI_PHASE)
        
        # Add selections for different phases
        selection.add_selection("breakfast", "recipe1", "power")
        selection.add_selection("breakfast", "recipe2", "nurture")
        
        assert len(selection.breakfast) == 2
        assert any(s.phase == "power" for s in selection.breakfast)
        assert any(s.phase == "nurture" for s in selection.breakfast)
        
    def test_multi_phase_requires_phase(self):
        """Test that multi-phase mode requires phase parameter."""
        selection = RecipeSelection(mode=SelectionMode.MULTI_PHASE)
        
        with pytest.raises(ValueError):
            selection.add_selection("breakfast", "recipe1")  # Missing phase

class TestPhaseAwareKeyboard:
    """Test suite for phase-aware recipe selection keyboard."""
    
    def test_single_phase_keyboard(self):
        """Test keyboard creation for single phase."""
        recipes = [
            {"id": "1", "title": "Recipe 1", "prep_time": 15, "phase": "power"},
            {"id": "2", "title": "Recipe 2", "prep_time": 20, "phase": "power"}
        ]
        
        keyboard = create_recipe_selection_keyboard(recipes, "breakfast")
        buttons = keyboard["inline_keyboard"]
        
        assert len(buttons) == 4  # 2 recipes + spacer + skip
        # Check recipe buttons
        assert buttons[0][0]["text"] == "⚡ Recipe 1 (15 min)"
        assert buttons[0][0]["callback_data"] == "recipe_breakfast_1"
        assert buttons[1][0]["text"] == "⚡ Recipe 2 (20 min)"
        assert buttons[1][0]["callback_data"] == "recipe_breakfast_2"
        # Check spacer and skip button
        assert buttons[2] == []  # Empty spacer row
        assert buttons[3][0]["text"] == "Skip this meal 🚫"
        assert buttons[3][0]["callback_data"] == "recipe_breakfast_skip"
        
    def test_multi_phase_keyboard(self):
        """Test keyboard creation for multiple phases."""
        recipes = [
            {"id": "1", "title": "Recipe 1", "prep_time": 15, "phase": "power"},
            {"id": "2", "title": "Recipe 2", "prep_time": 20, "phase": "nurture"}
        ]
        
        analysis = {
            "power": PhaseDistribution(days=2, percentage=0.29, recommended_recipes=0.29),
            "nurture": PhaseDistribution(days=5, percentage=0.71, recommended_recipes=0.71)
        }
        
        keyboard = create_recipe_selection_keyboard(
            recipes,
            "breakfast",
            show_multi_option=True,
            week_analysis=analysis
        )
        buttons = keyboard["inline_keyboard"]
        
        # Expected button order:
        # 0. Multi-select option
        # 1. Spacer
        # 2. Nurture phase header (larger percentage)
        # 3. Nurture recipe
        # 4. Power phase header (smaller percentage)
        # 5. Power recipe
        # 6. Spacer
        # 7. Skip option
        
        assert len(buttons) == 8
        
        # Check multi-select option
        multi_select_text = buttons[0][0]["text"]
        assert "multiple phases" in multi_select_text
        assert "Power ⚡: 29%" in multi_select_text
        assert "Nurture 🌱: 71%" in multi_select_text
        assert buttons[0][0]["callback_data"] == "multi_select_breakfast"
        
        # Check phase groups
        assert buttons[1] == []  # Spacer
        
        # Nurture phase section (comes first due to higher percentage)
        assert "Nurture Phase Recipes" in buttons[2][0]["text"]
        assert "🌱" in buttons[2][0]["text"]
        assert buttons[3][0]["callback_data"] == "recipe_breakfast_2_nurture"
        
        # Power phase section
        assert "Power Phase Recipes" in buttons[4][0]["text"]
        assert "⚡" in buttons[4][0]["text"]
        assert buttons[5][0]["callback_data"] == "recipe_breakfast_1_power"
        
        # Check skip button
        assert buttons[6] == []  # Spacer
        assert buttons[7][0]["text"] == "Skip this meal 🚫"
        assert buttons[7][0]["callback_data"] == "recipe_breakfast_skip"
