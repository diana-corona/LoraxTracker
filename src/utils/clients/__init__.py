"""
Centralized client initialization module.

This module provides lazy-loaded shared clients for the application.
"""
import os
from aws_lambda_powertools import Logger
from src.utils.telegram import TelegramClient
from src.utils.dynamo import DynamoDBClient
from src.utils.auth import Authorization

logger = Logger()

# Initialize shared clients (lazy loading)
_dynamo = None
_telegram = None
_auth = None

def get_dynamo():
    """Get or create DynamoDB client."""
    global _dynamo
    if _dynamo is None:
        _dynamo = DynamoDBClient(os.environ['TRACKER_TABLE_NAME'])
    return _dynamo

def get_telegram():
    """Get or create Telegram client."""
    global _telegram
    if _telegram is None:
        _telegram = TelegramClient()
    return _telegram

def get_auth():
    """Get or create Authorization instance."""
    global _auth
    if _auth is None:
        _auth = Authorization(get_dynamo())
    return _auth

def get_clients():
    """Get all required clients."""
    return get_dynamo(), get_telegram()

def get_all_clients():
    """Get all clients including authorization."""
    return get_dynamo(), get_telegram(), get_auth()
