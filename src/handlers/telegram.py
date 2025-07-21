"""
Lambda handler for processing Telegram webhook requests.
"""
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from src.utils.telegram import (
    TelegramClient,
    parse_command,
    validate_date,
    validate_date_range,
    generate_dates_in_range,
    format_error_message,
    create_rating_keyboard
)
from src.utils.dynamo import DynamoDBClient, create_pk, create_event_sk
from src.utils.middleware import require_auth
from src.utils.auth import Authorization, AuthorizationError
from src.models.event import CycleEvent
from src.services.cycle import calculate_next_cycle
from src.services.phase import get_current_phase, generate_phase_report
from src.services.recommendation import RecommendationEngine

logger = Logger()
tracer = Tracer()

import os

dynamo = DynamoDBClient(os.environ['TRACKER_TABLE_NAME'])
telegram = TelegramClient()
auth = Authorization()

def is_admin(user_id: str) -> bool:
    """
    Check if user is an admin.
    
    Args:
        user_id: Telegram user ID to check
        
    Returns:
        bool: True if user is an admin
    """
    admin_ids = os.environ.get("ADMIN_USER_IDS", "").split(",")
    return user_id in admin_ids

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Handle incoming Telegram webhook requests.
    
    Args:
        event: API Gateway Lambda proxy event
        context: Lambda context
        
    Returns:
        API Gateway Lambda proxy response
    """
    try:
        body = json.loads(event["body"])
        
        # Extract user ID and command if present
        user_id = None
        command = None
        
        if "message" in body:
            user_id = str(body["message"]["from"]["id"])
            text = body["message"].get("text", "")
            if text.startswith('/'):
                command = text.split()[0]
        
        # Check for admin commands before authorization
        if command in ["/allow", "/revoke"] and user_id in os.environ.get("ADMIN_USER_IDS", "").split(","):
            logger.info(f"Admin command access: {command} by user {user_id}")
            return handle_message(body["message"])
        
        # For non-admin commands, apply authorization check
        if not auth.check_user_authorized(user_id):
            logger.warning(f"Unauthorized access attempt from user {user_id}")
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": True, "result": True})
            }
        
        # Handle callback queries (button presses)
        if "callback_query" in body:
            return handle_callback_query(body["callback_query"])
            
        # Handle text messages
        if "message" in body:
            return handle_message(body["message"])
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({"ok": True, "result": True}),
            "isBase64Encoded": False
        }
        
    except Exception as e:
        logger.exception("Error processing webhook")
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({"ok": False, "error_code": 500, "description": str(e)})
        }

def handle_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """Handle incoming text messages."""
    chat_id = str(message["chat"]["id"])
    user_id = str(message["from"]["id"])
    text = message.get("text", "")
    
    if not text:
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "ok": False,
                    "error_code": 400,
                    "description": "No text in message"
                })
            }
    
    command, args = parse_command(text)
    
    try:
        # Admin commands
        if command == "/allow" and is_admin(user_id):
            if not args or len(args) != 2 or args[1] not in ["user", "partner", "group"]:
                return telegram.send_message(
                    chat_id=chat_id,
                    text=(
                        "Usage: /allow <user_id> <type>\n"
                        "Types: user, partner, group\n\n"
                        "Examples:\n"
                        "/allow 123456 user\n"
                        "/allow 789012 partner\n"
                        "/allow -100123456789 group"
                    )
                )
            target_id, user_type = args
            auth.add_allowed_user(target_id, user_type, user_id)
            return telegram.send_message(
                chat_id=chat_id,
                text=f"✅ Added {target_id} as {user_type}"
            )
            
        elif command == "/revoke" and is_admin(user_id):
            if not args:
                return telegram.send_message(
                    chat_id=chat_id,
                    text=(
                        "Usage: /revoke <user_id>\n\n"
                        "Example:\n"
                        "/revoke 123456"
                    )
                )
            target_id = args[0]
            auth.remove_allowed_user(target_id)
            return telegram.send_message(
                chat_id=chat_id,
                text=f"✅ Removed {target_id} from allow list"
            )
            
        # Regular commands
        if command == "/start":
            return handle_start_command(user_id, chat_id)
            
        elif command == "/register":
            if not args:
                return telegram.send_message(
                    chat_id=chat_id,
                    text="Please provide a date in YYYY-MM-DD format"
                )
            return handle_register_event(user_id, chat_id, args[0], args)
            
        elif command == "/phase":
            return handle_phase_command(user_id, chat_id)
            
        elif command == "/predict":
            return handle_prediction_command(user_id, chat_id)
            
        else:
            return telegram.send_message(
                chat_id=chat_id,
                text="Unrecognized command. Use /help to see available commands."
            )
            
    except Exception as e:
        logger.exception(f"Error handling command {command}")
        telegram.send_message(
            chat_id=chat_id,
            text=format_error_message(e)
        )
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "ok": False,
                "error_code": 500,
                "description": str(e)
            }),
            "isBase64Encoded": False
        }

def handle_callback_query(callback_query: Dict[str, Any]) -> Dict[str, Any]:
    """Handle callback queries from inline keyboards."""
    try:
        chat_id = str(callback_query["message"]["chat"]["id"])
        user_id = str(callback_query["from"]["id"])
        data = json.loads(callback_query["data"])
        
        if data["action"] == "rate":
            return handle_rating(
                user_id,
                chat_id,
                data["recommendation_id"],
                data["value"]
            )
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "ok": False,
                "error_code": 400,
                "description": "Invalid callback action"
            }),
            "isBase64Encoded": False
        }
        
    except Exception as e:
        logger.exception("Error handling callback query")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

def handle_start_command(user_id: str, chat_id: str) -> Dict[str, Any]:
    """Handle /start command."""
    welcome_text = (
        "Hi! I'm Lorax, your menstrual cycle assistant. 🌙\n\n"
        "You can use these commands:\n"
        "/register YYYY-MM-DD - Register a cycle event\n"
        "/register YYYY-MM-DD to YYYY-MM-DD - Register events for a date range\n"
        "/phase - View your current phase\n"
        "/predict - View next cycle prediction"
    )
    
    telegram.send_message(
        chat_id=chat_id,
        text=welcome_text
    )
    
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({"ok": True, "result": True}),
        "isBase64Encoded": False
    }

def handle_register_event(
    user_id: str,
    chat_id: str,
    date_str: str,
    args: List[str] = []
) -> Dict[str, Any]:
    """Handle /register command with optional date range."""
    if len(args) >= 3 and args[1].lower() == "to":
        # Handle date range
        end_date_str = args[2]
        
        start_date = validate_date(date_str)
        end_date = validate_date(end_date_str)
        
        if not start_date or not end_date:
            telegram.send_message(
                chat_id=chat_id,
                text="Invalid date format. Use: /register YYYY-MM-DD to YYYY-MM-DD"
            )
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "ok": False,
                    "error_code": 400,
                    "description": "Invalid date format"
                }),
                "isBase64Encoded": False
            }
            
        is_valid, error_msg = validate_date_range(start_date, end_date)
        if not is_valid:
            telegram.send_message(
                chat_id=chat_id,
                text=f"Invalid date range: {error_msg}"
            )
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "ok": False,
                    "error_code": 400,
                    "description": error_msg
                }),
                "isBase64Encoded": False
            }
            
        # Generate and store events for each date in range
        dates = generate_dates_in_range(start_date, end_date)
        for date_obj in dates:
            event = CycleEvent(
                user_id=user_id,
                date=date_obj.date(),
                state="menstruation"  # Default to menstruation event
            )
            
            # Convert date to ISO string format for DynamoDB storage
            event_data = event.model_dump()
            event_data['date'] = event_data['date'].isoformat()
            
            # Store in DynamoDB
            dynamo.put_item({
                "PK": create_pk(user_id),
                "SK": create_event_sk(date_obj.strftime("%Y-%m-%d")),
                **event_data
            })
        
        telegram.send_message(
            chat_id=chat_id,
            text=f"✅ Events registered for range {date_str} to {end_date_str}"
        )
        
    else:
        # Handle single date
        date_obj = validate_date(date_str)
        if not date_obj:
            telegram.send_message(
                chat_id=chat_id,
                text="Invalid date. Use YYYY-MM-DD format"
            )
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "ok": False,
                    "error_code": 400,
                    "description": "Invalid date format"
                }),
                "isBase64Encoded": False
            }
        
        event = CycleEvent(
            user_id=user_id,
            date=date_obj.date(),
            state="menstruation"  # Default to menstruation event
        )
        
        # Convert date to ISO string format for DynamoDB storage
        event_data = event.model_dump()
        event_data['date'] = event_data['date'].isoformat()
        
        # Store in DynamoDB
        dynamo.put_item({
            "PK": create_pk(user_id),
            "SK": create_event_sk(date_str),
            **event_data
        })
        
        telegram.send_message(
            chat_id=chat_id,
            text=f"✅ Event registered for {date_str}"
        )
    
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "ok": True,
            "result": {"message": "Event registered"}
        }),
        "isBase64Encoded": False
    }

def handle_phase_command(user_id: str, chat_id: str) -> Dict[str, Any]:
    """Handle /fase command."""
    # Get user's events
    events = dynamo.query_items(
        partition_key="PK",
        partition_value=create_pk(user_id)
    )
    
    if not events:
        telegram.send_message(
            chat_id=chat_id,
            text="No events registered. Use /register to start."
        )
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "ok": False,
                "error_code": 404,
                "description": "No events found"
            }),
            "isBase64Encoded": False
        }
    
    # Convert to CycleEvent objects
    cycle_events = [
        CycleEvent(**event)
        for event in events
        if event["SK"].startswith("EVENT#")
    ]
    
    # Get current phase
    current_phase = get_current_phase(cycle_events)
    
    # Generate and send report
    report = generate_phase_report(current_phase, cycle_events)
    telegram.send_phase_report(chat_id, report)
    
    # Generate and send recommendations
    engine = RecommendationEngine(user_id)
    recommendation = engine.generate_recommendations(current_phase, cycle_events)
    
    telegram.send_recommendation(
        chat_id,
        recommendation.recommendations
    )
    
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "ok": True,
            "result": {"message": "Phase report sent"}
        }),
        "isBase64Encoded": False
    }

def handle_prediction_command(user_id: str, chat_id: str) -> Dict[str, Any]:
    """Handle /prediccion command."""
    # Get user's events
    events = dynamo.query_items(
        partition_key="PK",
        partition_value=create_pk(user_id)
    )
    
    if not events:
        telegram.send_message(
            chat_id=chat_id,
            text="Not enough data to make a prediction."
        )
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "ok": False,
                "error_code": 404,
                "description": "No events found"
            }),
            "isBase64Encoded": False
        }
    
    # Convert to CycleEvent objects
    cycle_events = [
        CycleEvent(**event)
        for event in events
        if event["SK"].startswith("EVENT#")
    ]
    
    # Calculate prediction
    next_date, duration, warning = calculate_next_cycle(cycle_events)
    
    message = [
        f"🔮 Next expected cycle: {next_date}",
        f"📊 Average duration: {duration} days",
    ]
    
    if warning:
        message.append(f"⚠️ {warning}")
    
    telegram.send_message(
        chat_id=chat_id,
        text="\n".join(message)
    )
    
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "ok": True,
            "result": {"message": "Prediction sent"}
        }),
        "isBase64Encoded": False
    }

def handle_rating(
    user_id: str,
    chat_id: str,
    recommendation_id: str,
    rating: int
) -> Dict[str, Any]:
    """Handle recommendation rating callback."""
    try:
        # Update recommendation in DynamoDB
        dynamo.update_item(
            key={
                "PK": create_pk(user_id),
                "SK": f"REC#{recommendation_id}"
            },
            update_expression="SET effectiveness_rating = :r",
            expression_values={":r": rating}
        )
        
        telegram.send_message(
            chat_id=chat_id,
            text=f"Thanks for your rating! ({rating}⭐)"
        )
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "ok": True,
                "result": {"message": "Rating recorded"}
            }),
            "isBase64Encoded": False
        }
        
    except Exception as e:
        logger.exception("Error recording rating")
        telegram.send_message(
            chat_id=chat_id,
            text=format_error_message(e)
        )
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "ok": False,
                "error_code": 500,
                "description": str(e)
            }),
            "isBase64Encoded": False
        }
