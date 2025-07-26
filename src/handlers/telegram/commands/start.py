"""
Telegram /start command handler.
"""
from typing import Dict, Any

from aws_lambda_powertools import Logger
from src.utils.telegram import TelegramClient

logger = Logger()
telegram = TelegramClient()

def handle_start_command(user_id: str, chat_id: str) -> Dict[str, Any]:
    """Handle /start command."""
    # Log new user interaction
    logger.info("New user started bot", extra={
        "user_id": user_id,
        "chat_id": chat_id,
        "command": "/start"
    })
    
    welcome_text = (
        "Hi! I'm Lorax, your menstrual cycle assistant. 🌙\n\n"
        "You can use these commands:\n"
        "/register YYYY-MM-DD - Register a cycle event\n"
        "/register YYYY-MM-DD to YYYY-MM-DD - Register events for a date range\n"
        "/phase - View your current phase\n"
        "/predict - View next cycle prediction\n"
        "/statistics - View your cycle statistics"
    )
    
    telegram.send_message(
        chat_id=chat_id,
        text=welcome_text
    )
    
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({"ok": True, "result": True}),
        "isBase64Encoded": False
    }
