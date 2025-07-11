"""
Lambda handler for phase detection and analysis.
"""
from typing import Dict, List, Optional
from datetime import date
import json

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import BaseModel, Field

from src.utils.dynamo import DynamoDBClient, create_pk
from src.models.event import CycleEvent
from src.models.phase import Phase, TraditionalPhaseType, FunctionalPhaseType
from src.services.phase import get_current_phase, generate_phase_report
from src.services.recommendation import RecommendationEngine

logger = Logger()
tracer = Tracer()

dynamo = DynamoDBClient("TrackerTable")

class PhaseRequest(BaseModel):
    """Phase analysis request model."""
    user_id: str
    chat_id: str
    chat_type: str = Field(..., pattern="^(private|group)$")
    date: Optional[date] = None

class PhaseDetails(BaseModel):
    """Detailed phase information."""
    traditional_phase: str
    functional_phase: str
    start_date: date
    end_date: date
    duration: int
    dietary_style: str
    fasting_protocol: str
    food_recommendations: List[str]
    activity_recommendations: List[str]
    supplement_recommendations: Optional[List[str]] = None

class PhaseResponse(BaseModel):
    """Phase analysis response model."""
    phase: PhaseDetails
    report: str
    recommendations: List[Dict[str, any]]

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: Dict, context: LambdaContext) -> Dict:
    """
    Handle phase detection and analysis requests.
    
    Args:
        event: API Gateway Lambda proxy event
        context: Lambda context
        
    Returns:
        API Gateway Lambda proxy response
    """
    try:
        request = PhaseRequest(**json.loads(event['body']))
        response = analyze_phase(request)
        
        return {
            'statusCode': 200,
            'body': response.model_dump_json()
        }
        
    except Exception as e:
        logger.exception('Failed to analyze phase')
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def analyze_phase(request: PhaseRequest) -> PhaseResponse:
    """
    Analyze current phase and generate recommendations.
    
    Args:
        request: Phase analysis request
        
    Returns:
        Phase analysis response with phase details and recommendations
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
    
    # Get current phase
    current_phase = get_current_phase(cycle_events, request.date)
    
    # Generate phase report
    report = generate_phase_report(current_phase, cycle_events)
    
    # Generate recommendations
    engine = RecommendationEngine(request.user_id)
    recommendation = engine.generate_recommendations(current_phase, cycle_events)
    
    # Convert phase to response format
    phase_details = PhaseDetails(
        traditional_phase=current_phase.traditional_phase.value,
        functional_phase=current_phase.functional_phase.value,
        start_date=current_phase.start_date,
        end_date=current_phase.end_date,
        duration=current_phase.duration,
        dietary_style=current_phase.dietary_style,
        fasting_protocol=current_phase.fasting_protocol,
        food_recommendations=current_phase.food_recommendations,
        activity_recommendations=current_phase.activity_recommendations,
        supplement_recommendations=current_phase.supplement_recommendations
    )
    
    return PhaseResponse(
        phase=phase_details,
        report=report,
        recommendations=[
            {
                "category": rec.category,
                "priority": rec.priority,
                "description": rec.description
            }
            for rec in recommendation.recommendations
        ]
    )
