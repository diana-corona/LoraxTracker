"""
Recipe markdown parser utility.

This module provides functionality to parse recipe markdown files from the recipes
folder and convert them into Recipe objects for use in meal planning.
"""
import os
import re
from pathlib import Path
from typing import List, Optional

try:
    from aws_lambda_powertools import Logger
    logger = Logger()
except ImportError:
    # Fallback for local testing without aws_lambda_powertools
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

from src.models.recipe import Recipe

class RecipeMarkdownParser:
    """Parse recipe markdown files into Recipe objects."""
    
    def __init__(self, recipes_base_path: str = "recipes"):
        """
        Initialize parser with base recipes path.
        
        Args:
            recipes_base_path: Base path to recipes folder
        """
        self.recipes_base_path = recipes_base_path
    
    def parse_recipe_file(self, file_path: str) -> Optional[Recipe]:
        """
        Parse single markdown recipe file.
        
        Args:
            file_path: Path to markdown recipe file
            
        Returns:
            Recipe object if parsing successful, None otherwise
            
        Raises:
            FileNotFoundError: If recipe file doesn't exist
        """
        if not os.path.exists(file_path):
            logger.error(f"Recipe file not found: {file_path}")
            raise FileNotFoundError(f"Recipe file not found: {file_path}")
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract title from first line (should be # Title)
            title = self._extract_title(content)
            if not title:
                logger.warning(f"Could not extract title from {file_path}")
                return None
            
            # Extract all components
            prep_time = self.extract_prep_time(content)
            tags = self.extract_tags(content)
            ingredients = self.extract_ingredients(content)
            instructions = self.extract_instructions(content)
            notes = self._extract_notes(content)
            url = self._extract_url(content)
            
            # Determine phase from file path
            phase = self._determine_phase_from_path(file_path)
            
            return Recipe(
                title=title,
                phase=phase,
                prep_time=prep_time,
                tags=tags,
                ingredients=ingredients,
                instructions=instructions,
                notes=notes,
                url=url,
                file_path=file_path
            )
            
        except Exception as e:
            logger.error(f"Error parsing recipe file {file_path}: {str(e)}")
            return None
    
    def extract_prep_time(self, content: str) -> int:
        """
        Extract prep time from markdown content.
        
        Args:
            content: Markdown file content
            
        Returns:
            Prep time in minutes, defaults to 0 if not found
        """
        # Look for "## Prep Time" section
        prep_time_pattern = r'##\s*Prep\s+Time\s*\n([^\n]+)'
        match = re.search(prep_time_pattern, content, re.IGNORECASE)
        
        if not match:
            return 0
        
        time_str = match.group(1).strip()
        
        # Parse various time formats
        # Handle formats like: "30 minutes", "1 hour", "1 hour 30 minutes", "45 min"
        minutes = 0
        
        # Extract hours
        hour_match = re.search(r'(\d+)\s*(?:hour|hr)s?', time_str, re.IGNORECASE)
        if hour_match:
            minutes += int(hour_match.group(1)) * 60
        
        # Extract minutes
        minute_match = re.search(r'(\d+)\s*(?:minute|min)s?', time_str, re.IGNORECASE)
        if minute_match:
            minutes += int(minute_match.group(1))
        
        # If no time units found, assume the number is minutes
        if minutes == 0:
            number_match = re.search(r'(\d+)', time_str)
            if number_match:
                minutes = int(number_match.group(1))
        
        return minutes
    
    def extract_tags(self, content: str) -> List[str]:
        """
        Extract meal tags from markdown content.
        
        Args:
            content: Markdown file content
            
        Returns:
            List of cleaned tag strings
        """
        # Look for "## Tags" section
        tags_pattern = r'##\s*Tags\s*\n((?:.*\n)*?)(?=##|\Z)'
        match = re.search(tags_pattern, content, re.IGNORECASE)
        
        if not match:
            return []
        
        tags_section = match.group(1).strip()
        tags = []
        
        # Extract tags from bulleted list or comma-separated
        lines = tags_section.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove bullet points and dashes
            line = re.sub(r'^[-*+]\s*', '', line)
            
            # Split by comma if multiple tags on one line
            if ',' in line:
                line_tags = [tag.strip().lower() for tag in line.split(',')]
                tags.extend([tag for tag in line_tags if tag])
            else:
                clean_tag = line.lower()
                if clean_tag:
                    tags.append(clean_tag)
        
        return tags
    
    def extract_ingredients(self, content: str) -> List[str]:
        """
        Extract ingredients list from markdown content.
        
        Args:
            content: Markdown file content
            
        Returns:
            List of ingredient strings with amounts
        """
        # Look for "## Ingredients" section
        ingredients_pattern = r'##\s*Ingredients\s*\n((?:.*\n)*?)(?=##|\Z)'
        match = re.search(ingredients_pattern, content, re.IGNORECASE)
        
        if not match:
            return []
        
        ingredients_section = match.group(1).strip()
        ingredients = []
        
        lines = ingredients_section.split('\n')
        current_subsection = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this is a subsection header (like "For the marinade:")
            if line.endswith(':') and not line.startswith('-') and not line.startswith('*'):
                current_subsection = line
                continue
            
            # Remove bullet points and dashes
            clean_line = re.sub(r'^[-*+]\s*', '', line)
            if clean_line:
                ingredients.append(clean_line)
        
        return ingredients
    
    def extract_instructions(self, content: str) -> List[str]:
        """
        Extract cooking instructions from markdown content.
        
        Args:
            content: Markdown file content
            
        Returns:
            List of instruction strings
        """
        # Look for "## Instructions" section
        instructions_pattern = r'##\s*Instructions\s*\n((?:.*\n)*?)(?=##|\Z)'
        match = re.search(instructions_pattern, content, re.IGNORECASE)
        
        if not match:
            return []
        
        instructions_section = match.group(1).strip()
        instructions = []
        
        lines = instructions_section.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove numbered list markers
            clean_line = re.sub(r'^\d+\.\s*', '', line)
            if clean_line:
                instructions.append(clean_line)
        
        return instructions
    
    def _extract_title(self, content: str) -> Optional[str]:
        """Extract recipe title from first line."""
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
        return None
    
    def _extract_notes(self, content: str) -> Optional[str]:
        """Extract notes section if present."""
        notes_pattern = r'##\s*Notes\s*\n((?:.*\n)*?)(?=##|\Z)'
        match = re.search(notes_pattern, content, re.IGNORECASE)
        
        if match:
            notes_content = match.group(1).strip()
            if notes_content:
                return notes_content
        return None
    
    def _extract_url(self, content: str) -> Optional[str]:
        """Extract URL section if present."""
        url_pattern = r'##\s*URL\s*\n([^\n]+)'
        match = re.search(url_pattern, content, re.IGNORECASE)
        
        if match:
            url = match.group(1).strip()
            if url and url != 'hhttps://example.com/quinoa-power-bowl':  # Skip template URL
                return url
        return None
    
    def _determine_phase_from_path(self, file_path: str) -> Optional[str]:
        """Determine phase from file path."""
        path_obj = Path(file_path)
        
        # Look for phase folder names in path
        if 'power' in path_obj.parts:
            return 'power'
        elif 'manifestation' in path_obj.parts:
            return 'manifestation'
        elif 'nurture' in path_obj.parts:
            return 'nurture'
        
        return None
