"""Exceptions for the statistics service."""

class StatisticsError(Exception):
    """Base exception for statistics calculation errors."""
    pass

class InvalidPeriodDurationError(StatisticsError):
    """Raised when a period duration is physiologically unreasonable."""
    pass
