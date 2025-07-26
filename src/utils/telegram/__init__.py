"""
Telegram utilities package.
"""
from .formatters import (
    format_error_message,
    format_phase_report,
    format_recommendations
)
from .keyboards import (
    create_inline_keyboard,
    create_rating_keyboard
)
from .parsers import (
    parse_command,
    parse_callback_data
)
from .validators import (
    validate_date,
    validate_date_range,
    generate_dates_in_range
)
from .client import TelegramClient

__all__ = [
    "TelegramClient",
    "format_error_message",
    "format_phase_report",
    "format_recommendations",
    "create_inline_keyboard",
    "create_rating_keyboard",
    "parse_command",
    "parse_callback_data",
    "validate_date",
    "validate_date_range",
    "generate_dates_in_range"
]
