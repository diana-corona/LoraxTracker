"""
Lambda handler for generating and sending weekly reports.
"""
from typing import Dict, List
import json
import asyncio
import os

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from src.utils.clients import get_all_clients
from src.models.event import CycleEvent
from src.models.user import User
from src.services.weekly_plan import generate_weekly_plan, format_weekly_plan
from src.handlers.telegram.exceptions import NoEventsError, WeeklyPlanError

logger = Logger()
tracer = Tracer()

# Initialize clients at module level
dynamo, telegram, auth = get_all_clients()

def get_table_name() -> str:
    """Get DynamoDB table name with stage suffix."""
    service = os.environ.get('POWERTOOLS_SERVICE_NAME', 'lorax-tracker')
    stage = os.environ.get('STAGE', 'dev')
    return f"{service}-{stage}-TrackerTable"

def get_active_users() -> List[User]:
    """Get all active users from DynamoDB."""
    users = []
    try:
        logger.debug(f"Scanning table: {get_table_name()}")
        # Scan for all users (in production, should use GSI or pagination)
        response = dynamo.table.scan()
        items = response.get("Items", [])
        
        logger.info(f"Found {len(items)} total items in DynamoDB")
        profile_items = [item for item in items if item.get("SK") == "PROFILE"]
        logger.info(f"Found {len(profile_items)} user profiles")
        
        for item in profile_items:
            try:
                user = User(**item)
                logger.debug(f"Processing user {user.user_id}")
                
                # Only include authorized users
                if auth.check_user_authorized(user.user_id):
                    users.append(user)
                    logger.info(f"Added authorized user {user.user_id}")
                else:
                    logger.warning(f"User {user.user_id} not authorized")
            except Exception as e:
                logger.warning(
                    "Failed to parse user data",
                    extra={
                        "error": str(e),
                        "item": item,
                        "error_type": e.__class__.__name__
                    }
                )
                continue
        
        logger.info(f"Found {len(users)} active authorized users")
        return users
        
    except Exception as e:
        logger.exception("Error getting active users", extra={"error": str(e)})
        raise

async def send_user_report(user: User) -> None:
    """Generate and send weekly report for a user."""
    try:
        logger.info(f"Generating report for user {user.user_id}")
        
        # Get user's events
        events = dynamo.query_items(
            partition_key="PK",
            partition_value=f"USER#{user.user_id}"  # Using create_pk functionality directly
        )
        
        logger.info(f"Found {len(events)} total events for user {user.user_id}")
        
        # Convert to CycleEvent objects with error tracking
        cycle_events = []
        for event in events:
            try:
                if event["SK"].startswith("EVENT#"):
                    cycle_events.append(CycleEvent(**event))
            except Exception as e:
                logger.warning(
                    "Failed to parse cycle event",
                    extra={
                        "user_id": user.user_id,
                        "event": event,
                        "error": str(e),
                        "error_type": e.__class__.__name__
                    }
                )
                continue
        
        logger.info(f"Processed {len(cycle_events)} cycle events for user {user.user_id}")
        
        if not cycle_events:
            logger.warning(
                f"No valid cycle events found for user {user.user_id}",
                extra={"total_events": len(events)}
            )
            await telegram.send_message(
                chat_id=user.chat_id_private,
                text="⚠️ No cycle events found. Please register some events first using the /registrar command."
            )
            return
            
        # Generate and format weekly plan
        try:
            weekly_plan = generate_weekly_plan(cycle_events, user_id=user.user_id)
            formatted_plan = format_weekly_plan(weekly_plan)
            
            logger.info(
                f"Generated weekly plan for user {user.user_id}",
                extra={
                    "plan_start": weekly_plan.start_date.isoformat(),
                    "plan_end": weekly_plan.end_date.isoformat(),
                    "phase_groups": len(weekly_plan.phase_groups)
                }
            )
            
            # Send to private chat
            await telegram.send_message(
                chat_id=user.chat_id_private,
                text="\n".join(formatted_plan)
            )
            
            # Send to group if configured
            if user.chat_id_group:
                if auth.verify_group_access(user.chat_id_group):
                    logger.info(f"Sending to group chat {user.chat_id_group}")
                    await telegram.send_message(
                        chat_id=user.chat_id_group,
                        text="\n".join(formatted_plan)
                    )
                else:
                    logger.warning(
                        f"Group access not verified for {user.chat_id_group}",
                        extra={"user_id": user.user_id}
                    )
            
        except Exception as e:
            logger.exception(
                "Failed to generate/send weekly plan",
                extra={
                    "user_id": user.user_id,
                    "error_type": e.__class__.__name__,
                    "cycle_events": len(cycle_events)
                }
            )
            # Notify user of error
            await telegram.send_message(
                chat_id=user.chat_id_private,
                text="⚠️ Sorry, there was an error generating your weekly plan. Please try again later."
            )
            
    except Exception as e:
        logger.exception(
            f"Error in send_user_report",
            extra={
                "user_id": user.user_id,
                "error_type": e.__class__.__name__
            }
        )
        try:
            await telegram.send_message(
                chat_id=user.chat_id_private,
                text="⚠️ Sorry, there was an error generating your weekly plan. Please try again later."
            )
        except:
            logger.exception("Failed to send error message to user")

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
