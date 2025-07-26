"""
Message formatting functions for Telegram bot.
"""
from typing import Dict, Any, List, TYPE_CHECKING
import json

if TYPE_CHECKING:
    from src.models.recommendation import RecommendationType
    RecommendationList = List[RecommendationType]

def format_error_message(error: Exception) -> str:
    """Format error message for user display."""
    return (
        "❌ Lo siento, ha ocurrido un error.\n"
        "Por favor intenta nuevamente más tarde."
    )

def format_phase_report(phase_report: str) -> str:
    """Format phase report message with code block."""
    return f"<pre>{phase_report}</pre>"

def format_recommendations(recommendations: "RecommendationList") -> str:
    """
    Format recommendations list into a message.
    
    Args:
        recommendations: List of RecommendationType objects containing priority, 
                       category, and description fields
        
    Returns:
        Formatted message string
    """
    message = ["🌙 Recomendaciones personalizadas:\n"]
    
    for rec in recommendations:
        priority_stars = "⭐" * rec.priority
        message.append(
            f"{priority_stars}\n"
            f"<b>{rec.category.title()}</b>\n"
            f"{rec.description}\n"
        )
    
    return "\n".join(message)
