"""
Help command handler for displaying available commands.
"""
from typing import Dict, Any
from aws_lambda_powertools import Logger
from src.utils.clients import get_telegram
from src.utils.telegram.command_definitions import get_help_message

logger = Logger()

def handle_help_command(user_id: str, chat_id: str) -> Dict[str, Any]:
    """
    Handle /help command by displaying available commands and their usage.
    
    Args:
        user_id: Telegram user ID requesting help
        chat_id: Chat where help was requested
        
    Returns:
        API Gateway Lambda proxy response
    """
    logger.info("Handling help command request", extra={
        "user_id": user_id,
        "chat_id": chat_id
    })
    
    try:
        # Get client lazily
        telegram = get_telegram()
        response = telegram.send_message(
            chat_id=chat_id,
            text=get_help_message()
        )
        
        logger.info("Help message sent successfully", extra={
            "user_id": user_id,
            "chat_id": chat_id,
            "status_code": response["statusCode"]
        })
        
        return response
        
    except Exception as e:
        logger.exception("Error sending help message", extra={
            "user_id": user_id,
            "chat_id": chat_id,
            "error_type": e.__class__.__name__
        })
        raise
