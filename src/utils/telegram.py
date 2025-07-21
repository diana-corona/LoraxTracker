"""
Telegram bot utility functions for message handling.
"""
import os
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import json
import requests

class TelegramClient:
    """Client for interacting with Telegram Bot API."""
    
    def __init__(self):
        self.token = os.environ["TELEGRAM_BOT_TOKEN"]
        self.base_url = f"https://api.telegram.org/bot{self.token}"
    
    def send_message(
        self,
        chat_id: str,
        text: str,
        reply_markup: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a message to a specific chat.
        
        Args:
            chat_id: Telegram chat ID
            text: Message text
            reply_markup: Optional keyboard markup
            
        Returns:
            Response from Telegram API
        """
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
            
        response = requests.post(
            f"{self.base_url}/sendMessage",
            json=data
        )
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({"ok": True, "result": response.json()})
        }
    
    def send_phase_report(
        self,
        chat_id: str,
        phase_report: str
    ) -> Dict[str, Any]:
        """
        Send a formatted phase report.
        
        Args:
            chat_id: Telegram chat ID
            phase_report: Formatted phase report text
            
        Returns:
            Response from Telegram API
        """
        return self.send_message(
            chat_id=chat_id,
            text=f"<pre>{phase_report}</pre>"
        )
    
    def send_recommendation(
        self,
        chat_id: str,
        recommendations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Send formatted recommendations.
        
        Args:
            chat_id: Telegram chat ID
            recommendations: List of recommendation objects
            
        Returns:
            Response from Telegram API
        """
        message = ["🌙 Recomendaciones personalizadas:\n"]
        
        for rec in recommendations:
            priority_stars = "⭐" * rec["priority"]
            message.append(
                f"{priority_stars}\n"
                f"<b>{rec['category'].title()}</b>\n"
                f"{rec['description']}\n"
            )
        
        return self.send_message(
            chat_id=chat_id,
            text="\n".join(message)
        )
    
    def create_inline_keyboard(
        self,
        buttons: List[List[Dict[str, str]]]
    ) -> Dict[str, List[List[Dict[str, str]]]]:
        """
        Create an inline keyboard markup.
        
        Args:
            buttons: List of button rows with text and callback data
            
        Returns:
            Keyboard markup dictionary
        """
        return {
            "inline_keyboard": buttons
        }
    
    def parse_callback_data(self, callback_data: str) -> Dict[str, Any]:
        """
        Parse callback data from button presses.
        
        Args:
            callback_data: JSON string from callback query
            
        Returns:
            Parsed callback data
        """
        try:
            return json.loads(callback_data)
        except json.JSONDecodeError:
            return {"action": callback_data}

def format_error_message(error: Exception) -> str:
    """Format error message for user display."""
    return (
        "❌ Lo siento, ha ocurrido un error.\n"
        "Por favor intenta nuevamente más tarde."
    )

def create_rating_keyboard() -> Dict[str, List[List[Dict[str, str]]]]:
    """Create rating keyboard with 1-5 stars."""
    buttons = [[{
        "text": "⭐" * i,
        "callback_data": json.dumps({
            "action": "rate",
            "value": i
        })
    } for i in range(1, 6)]]
    
    return {
        "inline_keyboard": buttons
    }

def parse_command(text: str) -> tuple[str, List[str]]:
    """
    Parse command and arguments from message text.
    
    Args:
        text: Raw message text
        
    Returns:
        Tuple of (command, arguments)
    """
    parts = text.split()
    command = parts[0].lower()
    args = parts[1:] if len(parts) > 1 else []
    
    return command, args

def validate_date(date_str: str) -> Optional[datetime]:
    """
    Validate and parse date string.
    
    Args:
        date_str: Date string in YYYY-MM-DD format
        
    Returns:
        Datetime object if valid, None otherwise
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None

def validate_date_range(start_date: datetime, end_date: datetime) -> Tuple[bool, Optional[str]]:
    """
    Validate a date range meets constraints.
    
    Args:
        start_date: Start datetime
        end_date: End datetime
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if start_date > end_date:
        return False, "Start date must be before end date"
        
    date_diff = (end_date - start_date).days
    if date_diff > 31:
        return False, "Date range cannot exceed 31 days"
        
    return True, None

def generate_dates_in_range(start_date: datetime, end_date: datetime) -> List[datetime]:
    """
    Generate list of dates between start and end dates inclusive.
    
    Args:
        start_date: Start datetime
        end_date: End datetime
        
    Returns:
        List of datetime objects
    """
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    return dates
