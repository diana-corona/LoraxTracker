"""
Service-level exceptions.

This module contains exceptions that can be raised by various services
in the application.
"""

class AuthorizationError(Exception):
    """Raised when a user is not authorized to perform an action."""
    pass

class StatisticsError(Exception):
    """Base exception for statistics calculation errors."""
    pass

class InvalidPeriodDurationError(StatisticsError):
    """Raised when a period duration is physiologically unreasonable."""
    pass
