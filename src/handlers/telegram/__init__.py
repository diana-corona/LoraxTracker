"""
Telegram bot handler package.
"""
from .handler import handler
from .admin import handle_allow_command, handle_revoke_command, is_admin
from .commands import (
    handle_start_command,
    handle_register_event,
    handle_phase_command,
    handle_prediction_command,
    handle_statistics_command
)
from .callbacks import handle_callback_query

__all__ = [
    "handler",
    "handle_allow_command",
    "handle_revoke_command",
    "is_admin",
    "handle_start_command",
    "handle_register_event",
    "handle_phase_command",
    "handle_prediction_command",
    "handle_statistics_command",
    "handle_callback_query"
]
