"""
Telegram API client implementation.
"""
import os
from typing import Dict, Any, Optional, List
import json
import requests

from .formatters import format_phase_report, format_recommendations

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
        if response.status_code == 429:
            # Let the error propagate so Lambda returns non-200 status
            # This allows Telegram's retry mechanism to work
            response.raise_for_status()
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
            text=format_phase_report(phase_report)
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
            Response from Telegram API with status code and message details
        """
        return self.send_message(
            chat_id=chat_id,
            text=format_recommendations(recommendations)
        )
