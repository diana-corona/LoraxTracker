"""
Date validation utilities for Telegram bot.
"""
from typing import Optional, List, Tuple
from datetime import datetime, timedelta

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
