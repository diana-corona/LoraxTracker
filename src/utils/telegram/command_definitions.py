"""
Centralized command definitions for Telegram bot.

This module provides a single source of truth for all bot commands,
their descriptions, and formatting for different contexts.

Typical usage:
    from src.utils.telegram.command_definitions import get_help_message, get_start_message
    help_text = get_help_message()
    start_text = get_start_message(is_private_chat=True)
"""
from typing import Dict, List, NamedTuple
from dataclasses import dataclass

@dataclass
class Command:
    """
    Represents a Telegram bot command with its description.
    
    Attributes:
        name: Command name without leading slash
        description: User-friendly description of what the command does
        format: Optional format specification (e.g., "YYYY-MM-DD")
    """
    name: str
    description: str
    format: str = ""

class CommandCategory(NamedTuple):
    """
    Group of related commands with a category title.
    
    Attributes:
        emoji: Category emoji for visual distinction
        title: Category name (e.g., "Basic Commands")
        commands: List of Command objects in this category
    """
    emoji: str
    title: str
    commands: List[Command]

# Define all bot commands by category
COMMAND_CATEGORIES = [
    CommandCategory(
        emoji="🚀",
        title="Basic Commands",
        commands=[
            Command("start", "Start interacting with the bot"),
            Command("help", "Show this help message"),
            Command(
                "register", 
                "Register an event",
                format="YYYY-MM-DD"
            )
        ]
    ),
    CommandCategory(
        emoji="📊",
        title="Information Commands",
        commands=[
            Command("phase", "Get your current cycle phase"),
            Command("predict", "Get predictions for your next cycle"),
            Command("statistics", "View your cycle statistics"),
            Command(
                "history", 
                "View period history (last 6 months or N periods)",
                format="[N]"
            )
        ]
    ),
    CommandCategory(
        emoji="📅",
        title="Planning Commands",
        commands=[
            Command(
                "weeklyplan",
                "Get personalized weekly recommendations and meal planning"
            )
        ]
    )
]

def format_register_command() -> str:
    """Get formatted register command examples."""
    return (
        "/register YYYY-MM-DD - Register a cycle event\n"
        "/register YYYY-MM-DD to YYYY-MM-DD - Register events for a date range"
    )

def get_help_message() -> str:
    """
    Generate the help message showing all available commands.
    
    Returns:
        Formatted help message string with categories and commands.
    """
    sections = ["Available commands:\n"]
    
    for category in COMMAND_CATEGORIES:
        # Add category header
        sections.append(f"\n{category.emoji} {category.title}:")
        
        # Add each command in category
        for cmd in category.commands:
            command_text = f"/{cmd.name}"
            if cmd.format:
                command_text += f" {cmd.format}"
            command_text += f" - {cmd.description}"
            sections.append(command_text)
    
    return "\n".join(sections)

def get_start_message(is_private_chat: bool = True) -> str:
    """
    Generate the start message appropriate for chat type.
    
    Args:
        is_private_chat: Whether this is a private chat (vs group)
        
    Returns:
        Appropriate welcome message with or without command list
    """
    if not is_private_chat:
        return "Hi! I'm Lorax, your weekly planner assistant. 🌙"
    
    sections = [
        "Hi! I'm Lorax, your menstrual cycle assistant. 🌙\n",
        "You can use these commands:\n"
    ]
    
    for category in COMMAND_CATEGORIES:
        # Add category header
        sections.append(f"\n{category.emoji} {category.title}:")
        
        # Add commands for category
        for cmd in category.commands:
            if cmd.name == "register":
                # Special handling for register command to show both formats
                sections.append(format_register_command())
            else:
                command_text = f"/{cmd.name}"
                if cmd.format:
                    command_text += f" {cmd.format}"
                command_text += f" - {cmd.description}"
                sections.append(command_text)
    
    return "\n".join(sections)
