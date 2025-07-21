"""
Lambda handler for generating and sending weekly reports.
"""
from typing import Dict, List
import json

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from src.utils.dynamo import DynamoDBClient, create_pk
from src.utils.telegram import TelegramClient
from src.utils.auth import Authorization
from src.models.event import CycleEvent
from src.models.user import User
from src.services.phase import get_current_phase, generate_phase_report

logger = Logger()
tracer = Tracer()

import os

dynamo = DynamoDBClient(f"TrackerTable-{os.environ.get('STAGE', 'dev')}")
telegram = TelegramClient()
auth = Authorization()

def get_active_users() -> List[User]:
    """Get all active users from DynamoDB."""
    # Scan for all users (in production, should use GSI or pagination)
    response = dynamo.table.scan()
    items = response.get("Items", [])
    
    users = []
    for item in items:
        if item.get("SK") == "PROFILE":
            # Convert DynamoDB item to User object
            try:
                user = User(**item)
                # Only include authorized users
                if auth.check_user_authorized(user.user_id):
                    users.append(user)
            except Exception as e:
                logger.warning(f"Failed to parse user data: {e}")
                continue
    
    return users

async def send_user_report(user: User) -> None:
    """Generate and send weekly report for a user."""
    try:
        # Get user's events
        events = dynamo.query_items(
            partition_key="PK",
            partition_value=create_pk(user.user_id)
        )
        
        # Convert to CycleEvent objects
        cycle_events = [
            CycleEvent(**event)
            for event in events
            if event["SK"].startswith("EVENT#")
        ]
        
        if not cycle_events:
            logger.info(f"No events found for user {user.user_id}")
            return
            
        # Get current phase
        current_phase = get_current_phase(cycle_events)
        
        # Generate report
        report = generate_phase_report(current_phase, cycle_events)
        
        # Add weekly summary header
        weekly_report = [
            "📅 Weekly Cycle Summary",
            "------------------------",
            *report
        ]
        
        # Send to private chat
        await telegram.send_message(
            chat_id=user.chat_id_private,
            text="\n".join(weekly_report)
        )
        
        # Send to group if configured
        if user.chat_id_group and auth.verify_group_access(user.chat_id_group):
            await telegram.send_message(
                chat_id=user.chat_id_group,
                text="\n".join(weekly_report)
            )
            
    except Exception as e:
        logger.exception(f"Error sending report for user {user.user_id}")

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: Dict, context: LambdaContext) -> Dict:
    """
    Handle weekly report generation.
    
    Args:
        event: CloudWatch scheduled event
        context: Lambda context
        
    Returns:
        Lambda response
    """
    try:
        # Get all active users
        users = get_active_users()
        logger.info(f"Found {len(users)} active users")
        
        # Send reports
        import asyncio
        asyncio.run(asyncio.gather(*[
            send_user_report(user)
            for user in users
        ]))
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Weekly reports sent",
                "user_count": len(users)
            })
        }
        
    except Exception as e:
        logger.exception("Error generating weekly reports")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e)
            })
        }
