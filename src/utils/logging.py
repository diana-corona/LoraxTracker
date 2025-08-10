"""Shared logging configuration."""
import os
import json
from aws_lambda_powertools import Logger

logger = Logger(
    service="telegram_bot", 
    level=os.environ.get('LOG_LEVEL', 'INFO'),
    log_uncaught_exceptions=True,
    json_serializer=json.dumps,
    use_rfc3339=True
)

# Add base logging context
logger.structure_logs(append=True, base={
    "region": os.environ.get('AWS_REGION'),
    "function": os.environ.get('AWS_LAMBDA_FUNCTION_NAME'),
    "version": os.environ.get('AWS_LAMBDA_FUNCTION_VERSION')
})
