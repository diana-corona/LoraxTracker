"""Shared logging configuration."""
import os
import sys
import json
import traceback
from aws_lambda_powertools import Logger

def format_exception(exc_info):
    """Format exception info into a single line."""
    if exc_info is True:  # When exc_info=True is passed to logger.exception
        exc_info = sys.exc_info()
    
    if exc_info and isinstance(exc_info, tuple) and len(exc_info) == 3:
        try:
            # Get the full traceback as a string
            trace = ''.join(traceback.format_exception(*exc_info))
            # Replace newlines with ' | ' for single-line output
            return trace.replace('\n', ' | ').strip()
        except Exception as e:
            return f"Error formatting exception: {str(e)}"
    return None

class SingleLineLogger(Logger):
    """Custom logger that formats exceptions in a single line."""
    
    def exception(self, message, *args, **kwargs):
        """Override to format exception in a single line."""
        exc_info = kwargs.pop('exc_info', True)
        extra = kwargs.pop('extra', {})
        extra['exception'] = format_exception(exc_info)
        kwargs['exc_info'] = False  # Prevent default multi-line formatting
        kwargs['extra'] = extra
        super().exception(message, *args, **kwargs)

logger = SingleLineLogger(
    service="telegram_bot", 
    level=os.environ.get('LOG_LEVEL', 'INFO'),
    log_uncaught_exceptions=True,
    json_serializer=json.dumps,
    use_rfc3339=True
)

# Add base logging context with custom exception handling
logger.structure_logs(append=True, base={
    "region": os.environ.get('AWS_REGION'),
    "function": os.environ.get('AWS_LAMBDA_FUNCTION_NAME'),
    "version": os.environ.get('AWS_LAMBDA_FUNCTION_VERSION')
})

def log_exception(logger, message, exc_info=None, **kwargs):
    """Helper function to log exceptions in a single line."""
    extra = kwargs.pop('extra', {})
    extra['exception'] = format_exception(exc_info if exc_info else sys.exc_info())
    logger.error(message, extra=extra, **kwargs)
