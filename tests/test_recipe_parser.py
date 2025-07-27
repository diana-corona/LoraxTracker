"""
Unit tests for recipe markdown parser.
"""
import pytest
import tempfile
import os
from pathlib import Path

from src.utils.recipe_parser import RecipeMarkdownParser
from src.models.recipe import Recipe


class TestRecipeMarkdownParser:
    """Test suite for RecipeMarkdownParser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = RecipeMarkdownParser()

    def test_parse_complete_recipe(self):
        """Test parsing a complete, well-formatted recipe."""
        recipe_content = """# Test Recipe

## Phase
[Leave blank - will be categorized later]

## Prep Time
25 minutes

## Tags
- dinner
- healthy

## Ingredients
- 1 cup quinoa
- 2 cups water
- 1 avocado, sliced
- Salt and pepper to taste

## Instructions
1. Rinse quinoa thoroughly
2. Boil water in pot
3. Add quinoa and cook for 15 minutes
4. Serve with avocado

## Notes
Great for meal prep!

## URL
https://example.com/recipe
"""
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(recipe_content)
            temp_path = f.name

        try:
            recipe = self.parser.parse_recipe_file(temp_path)
            
            assert recipe is not None
            assert recipe.title == "Test Recipe"
            assert recipe.prep_time == 25
            assert recipe.tags == ["dinner", "healthy"]
            assert len(recipe.ingredients) == 4
            assert "1 cup quinoa" in recipe.ingredients
            assert len(recipe.instructions) == 4
            assert "Rinse quinoa thoroughly" in recipe.instructions
            assert recipe.notes == "Great for meal prep!"
            assert recipe.url == "https://example.com/recipe"
            assert recipe.file_path == temp_path
            
        finally:
            os.unlink(temp_path)

    def test_parse_missing_file(self):
        """Test handling of missing recipe files."""
        with pytest.raises(FileNotFoundError):
            self.parser.parse_recipe_file("nonexistent_recipe.md")

    def test_parse_malformed_markdown(self):
        """Test handling of malformed markdown."""
        malformed_content = """This is not a proper recipe
Just some random text
No proper sections
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(malformed_content)
            temp_path = f.name

        try:
            recipe = self.parser.parse_recipe_file(temp_path)
            # Should return None for unparseable content
            assert recipe is None
            
        finally:
            os.unlink(temp_path)

    def test_extract_prep_time_various_formats(self):
        """Test prep time extraction with various formats."""
        test_cases = [
            ("30 minutes", 30),
            ("45 min", 45),
            ("1 hour", 60),
            ("1 hour 30 minutes", 90),
            ("2 hours", 120),
            ("15", 15),  # Just number
            ("No time format", 0),  # No parseable time
        ]
        
        for time_str, expected in test_cases:
            content = f"## Prep Time\n{time_str}\n"
            result = self.parser.extract_prep_time(content)
            assert result == expected, f"Failed for '{time_str}': expected {expected}, got {result}"

    def test_extract_tags_various_formats(self):
        """Test tag extraction with various formats."""
        # Bullet list format
        content1 = """## Tags
- breakfast
- healthy
- quick
"""
        tags1 = self.parser.extract_tags(content1)
        assert tags1 == ["breakfast", "healthy", "quick"]
        
        # Comma separated format
        content2 = """## Tags
dinner, healthy, vegetarian
"""
        tags2 = self.parser.extract_tags(content2)
        assert tags2 == ["dinner", "healthy", "vegetarian"]
        
        # Mixed format
        content3 = """## Tags
- lunch
- snack, healthy
"""
        tags3 = self.parser.extract_tags(content3)
        assert "lunch" in tags3
        assert "snack" in tags3
        assert "healthy" in tags3

    def test_extract_ingredients_with_subsections(self):
        """Test ingredient extraction with subsections."""
        content = """## Ingredients
For the marinade:
- 2 tablespoons olive oil
- 1 teaspoon salt

For the main dish:
- 1 lb chicken breast
- 2 cups rice
"""
        
        ingredients = self.parser.extract_ingredients(content)
        assert len(ingredients) == 4
        assert "2 tablespoons olive oil" in ingredients
        assert "1 lb chicken breast" in ingredients
        # Subsection headers should not be included
        assert "For the marinade:" not in ingredients

    def test_extract_instructions_numbered_list(self):
        """Test instruction extraction from numbered lists."""
        content = """## Instructions
1. Preheat oven to 350°F
2. Mix ingredients in bowl
3. Bake for 25 minutes
4. Let cool before serving
"""
        
        instructions = self.parser.extract_instructions(content)
        assert len(instructions) == 4
        assert "Preheat oven to 350°F" in instructions
        assert "Let cool before serving" in instructions
        # Numbers should be stripped
        assert "1. Preheat oven to 350°F" not in instructions

    def test_phase_determination_from_path(self):
        """Test phase determination from file path."""
        # Test power phase
        power_path = "recipes/power/test-recipe.md"
        phase = self.parser._determine_phase_from_path(power_path)
        assert phase == "power"
        
        # Test manifestation phase
        manifestation_path = "recipes/manifestation/test-recipe.md"
        phase = self.parser._determine_phase_from_path(manifestation_path)
        assert phase == "manifestation"
        
        # Test nurture phase
        nurture_path = "recipes/nurture/test-recipe.md"
        phase = self.parser._determine_phase_from_path(nurture_path)
        assert phase == "nurture"
        
        # Test unknown path
        unknown_path = "somewhere/else/test-recipe.md"
        phase = self.parser._determine_phase_from_path(unknown_path)
        assert phase is None

    def test_parse_real_recipe_file(self):
        """Test parsing with a real recipe file from the project."""
        # Test with the air fryer salmon recipe
        salmon_path = "recipes/power/air-fryer-salmon.md"
        
        if os.path.exists(salmon_path):
            recipe = self.parser.parse_recipe_file(salmon_path)
            
            assert recipe is not None
            assert recipe.title == "Air Fryer Salmon"
            assert recipe.phase == "power"
            assert recipe.prep_time == 15  # Should be 15 minutes
            assert "dinner" in recipe.tags
            assert len(recipe.ingredients) > 0
            assert len(recipe.instructions) > 0
            assert recipe.url is not None

    def test_extract_missing_sections(self):
        """Test handling of missing recipe sections."""
        minimal_content = """# Minimal Recipe

## Prep Time
10 minutes
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(minimal_content)
            temp_path = f.name

        try:
            recipe = self.parser.parse_recipe_file(temp_path)
            
            assert recipe is not None
            assert recipe.title == "Minimal Recipe"
            assert recipe.prep_time == 10
            assert recipe.tags == []  # Empty list for missing tags
            assert recipe.ingredients == []  # Empty list for missing ingredients
            assert recipe.instructions == []  # Empty list for missing instructions
            assert recipe.notes is None
            assert recipe.url is None
            
        finally:
            os.unlink(temp_path)

    def test_extract_notes_and_url(self):
        """Test extraction of optional notes and URL sections."""
        content = """# Test Recipe

## Notes
This is a great recipe for beginners.
Store leftovers in the fridge.

## URL
https://example.com/test-recipe
"""
        
        notes = self.parser._extract_notes(content)
        url = self.parser._extract_url(content)
        
        assert "This is a great recipe for beginners." in notes
        assert "Store leftovers in the fridge." in notes
        assert url == "https://example.com/test-recipe"

    def test_ignore_template_url(self):
        """Test that template URLs are ignored."""
        content = """## URL
hhttps://example.com/quinoa-power-bowl
"""
        
        url = self.parser._extract_url(content)
        assert url is None  # Template URL should be ignored
