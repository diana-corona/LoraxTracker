"""
Lambda handler for generating user statistics.
"""
from typing import Dict, List, Optional
from datetime import datetime
import json

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from src.utils.dynamo import DynamoDBClient, create_pk
from src.utils.auth import Authorization
from src.models.event import CycleEvent
from src.services.statistics import calculate_cycle_statistics, calculate_phase_statistics

logger = Logger()
tracer = Tracer()

import os

# Initialize shared clients (lazy loading)
_dynamo = None
_auth = None

def get_dynamo():
    """Get or create DynamoDB client."""
    global _dynamo
    if _dynamo is None:
        _dynamo = DynamoDBClient(f"TrackerTable-{os.environ.get('STAGE', 'dev')}")
    return _dynamo

def get_auth():
    """Get or create Authorization instance."""
    global _auth
    if _auth is None:
        _auth = Authorization()
    return _auth

def get_user_events(user_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[CycleEvent]:
    """Get user events filtered by date range."""
    dynamo = get_dynamo()
    events = dynamo.query_items(
        partition_key="PK",
        partition_value=create_pk(user_id)
    )
    
    cycle_events = []
    for event in events:
        if event["SK"].startswith("EVENT#"):
            cycle_event = CycleEvent(**event)
            
            # Apply date filters if provided
            if start_date and cycle_event.date < datetime.strptime(start_date, "%Y-%m-%d").date():
                continue
            if end_date and cycle_event.date > datetime.strptime(end_date, "%Y-%m-%d").date():
                continue
                
            cycle_events.append(cycle_event)
    
    return cycle_events

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: Dict, context: LambdaContext) -> Dict:
    """
    Handle statistics generation request.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    try:
        # Parse query parameters
        query_params = event.get("queryStringParameters", {}) or {}
        user_id = query_params.get("user_id")
        start_date = query_params.get("start_date")
        end_date = query_params.get("end_date")
        
        if not user_id:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "user_id is required"
                })
            }
        
        # Get auth instance and verify user is authorized
        auth = get_auth()
        if not auth.check_user_authorized(user_id):
            return {
                "statusCode": 403,
                "body": json.dumps({
                    "error": "User not authorized"
                })
            }
        
        # Get user events
        events = get_user_events(user_id, start_date, end_date)
        
        if not events:
            return {
                "statusCode": 404,
                "body": json.dumps({
                    "error": "No events found for user"
                })
            }
        
        # Calculate statistics
        cycle_stats = calculate_cycle_statistics(events)
        phase_stats = calculate_phase_statistics(events)
        
        # Prepare response
        response = {
            "user_id": user_id,
            "period_analyzed": {
                "start_date": str(min(e.date for e in events)),
                "end_date": str(max(e.date for e in events))
            },
            "cycle_statistics": cycle_stats,
            "phase_statistics": phase_stats
        }
        
        return {
            "statusCode": 200,
            "body": json.dumps(response)
        }
        
    except Exception as e:
        logger.exception("Error generating statistics")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e)
            })
        }
