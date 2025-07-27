"""
Help command handler for displaying available commands.
"""
from typing import Dict, Any
from src.utils.telegram import TelegramClient

telegram = TelegramClient()

HELP_MESSAGE = """
Available commands:

🚀 Basic Commands:
/start - Start interacting with the bot
/help - Show this help message
/register - Register an event (Format: YYYY-MM-DD)

📊 Information Commands:
/phase - Get your current cycle phase
/predict - Get predictions for your next cycle
/statistics - View your cycle statistics

📅 Planning Commands:
/weeklyplan - Get personalized weekly recommendations
"""

def handle_help_command(user_id: str, chat_id: str) -> Dict[str, Any]:
    """
    Handle /help command by displaying available commands and their usage.
    
    Args:
        user_id: Telegram user ID requesting help
        chat_id: Chat where help was requested
        
    Returns:
        API Gateway Lambda proxy response
    """
    return telegram.send_message(
        chat_id=chat_id,
        text=HELP_MESSAGE,
        parse_mode="HTML"
    )
