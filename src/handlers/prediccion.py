"""
Lambda handler for cycle prediction requests.
"""
from typing import Dict, List, Optional, Tuple
from datetime import date, timedelta
import json

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import BaseModel, Field

from src.utils.dynamo import DynamoDBClient, create_pk
from src.models.event import CycleEvent
from src.services.cycle import calculate_next_cycle

logger = Logger()
tracer = Tracer()

dynamo = DynamoDBClient("TrackerTable")

class PredictionRequest(BaseModel):
    """Prediction request model."""
    user_id: str
    chat_id: str
    chat_type: str = Field(..., pattern="^(private|group)$")

class PredictionResponse(BaseModel):
    """Prediction response model."""
    next_cycle_date: date
    average_duration: int
    warning: Optional[str] = None

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: Dict, context: LambdaContext) -> Dict:
    """
    Handle cycle prediction requests.
    
    Args:
        event: API Gateway Lambda proxy event
        context: Lambda context
        
    Returns:
        API Gateway Lambda proxy response
    """
    try:
        request = PredictionRequest(**json.loads(event['body']))
        response = calculate_prediction(request)
        
        return {
            'statusCode': 200,
            'body': response.model_dump_json()
        }
        
    except Exception as e:
        logger.exception('Failed to process prediction')
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def calculate_prediction(request: PredictionRequest) -> PredictionResponse:
    """
    Calculate cycle prediction for a user.
    
    Args:
        request: Prediction request
        
    Returns:
        Prediction response with next cycle date and details
    """
    # Get user's events from DynamoDB
    events = dynamo.query_items(
        partition_key="PK",
        partition_value=create_pk(request.user_id)
    )
    
    if not events:
        raise ValueError("No events found for user")
    
    # Convert to CycleEvent objects
    cycle_events = [
        CycleEvent(**event)
        for event in events
        if event["SK"].startswith("EVENT#")
    ]
    
    # Calculate prediction
    next_date, duration, warning = calculate_next_cycle(cycle_events)
    
    return PredictionResponse(
        next_cycle_date=next_date,
        average_duration=duration,
        warning=warning
    )
