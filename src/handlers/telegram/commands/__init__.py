"""
Telegram command handlers package.
"""
from .start import handle_start_command
from .register import handle_register_event
from .phase import handle_phase_command
from .prediction import handle_prediction_command
from .statistics import handle_statistics_command
from .weeklyplan import handle_weeklyplan_command
from .help import handle_help_command

__all__ = [
    "handle_start_command",
    "handle_register_event",
    "handle_phase_command",
    "handle_prediction_command",
    "handle_statistics_command",
    "handle_weeklyplan_command",
    "handle_help_command"
]
