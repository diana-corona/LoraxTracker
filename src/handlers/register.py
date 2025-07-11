"""
Lambda handler for user registration and profile management.
"""
from typing import Dict, Optional
from datetime import datetime
import json

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import BaseModel, Field

from src.utils.dynamo import DynamoDBClient, create_pk
from src.utils.telegram import TelegramClient, format_error_message
from src.models.user import User

logger = Logger()
tracer = Tracer()

dynamo = DynamoDBClient("TrackerTable")
telegram = TelegramClient()

class RegistrationRequest(BaseModel):
    """User registration request model."""
    user_id: str
    chat_id_private: str
    chat_id_group: Optional[str] = None
    partner_id: Optional[str] = None
    user_type: str = Field(..., pattern="^(primary|partner)$")
    name: Optional[str] = None

@logger.inject_lambda_context
@tracer.capture_lambda_handler
async def handler(event: Dict, context: LambdaContext) -> Dict:
    """
    Handle user registration and profile updates.
    
    Args:
        event: API Gateway Lambda proxy event
        context: Lambda context
        
    Returns:
        API Gateway Lambda proxy response
    """
    try:
        request = RegistrationRequest(**json.loads(event['body']))
        response = await register_user(request)
        
        return {
            'statusCode': 200,
            'body': json.dumps(response)
        }
        
    except Exception as e:
        logger.exception('Failed to process registration')
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

async def register_user(request: RegistrationRequest) -> Dict:
    """
    Register or update a user profile.
    
    Args:
        request: Registration request
        
    Returns:
        Registration response with user details
    """
    # Check if user exists
    existing_user = dynamo.get_item({
        "PK": create_pk(request.user_id),
        "SK": "PROFILE"
    })
    
    # Create user object
    user = User(
        user_id=request.user_id,
        chat_id_private=request.chat_id_private,
        chat_id_group=request.chat_id_group,
        partner_id=request.partner_id,
        user_type=request.user_type,
        name=request.name,
        registration_date=datetime.now().isoformat()
    )
    
    # Store in DynamoDB
    dynamo.put_item({
        "PK": create_pk(user.user_id),
        "SK": "PROFILE",
        **user.model_dump()
    })
    
    # Send welcome message
    welcome_text = (
        f"Hello {user.name or 'User'}! 👋\n\n"
    )
    
    if existing_user:
        welcome_text += "Your profile has been successfully updated."
    else:
        welcome_text += (
            "Welcome to Lorax! 🌙\n\n"
            "I'm here to help you track and understand your menstrual cycle.\n\n"
            "You can use these commands:\n"
            "/register YYYY-MM-DD - Register a cycle event\n"
            "/phase - View your current phase\n"
            "/prediction - View next cycle prediction"
        )
    
    await telegram.send_message(
        chat_id=user.chat_id_private,
        text=welcome_text
    )
    
    if user.chat_id_group and not existing_user:
        # Send group welcome message
        await telegram.send_message(
            chat_id=user.chat_id_group,
            text=f"🎉 {user.name or 'New user'} has joined the group!"
        )
    
    return {
        "message": "User registered successfully",
        "user_id": user.user_id,
        "is_new": not existing_user
    }

async def link_partner(
    user_id: str,
    partner_id: str,
    chat_id: str
) -> Dict:
    """
    Link two users as partners.
    
    Args:
        user_id: Primary user ID
        partner_id: Partner user ID
        chat_id: Chat ID for notifications
        
    Returns:
        Response with linking status
    """
    # Get both users
    user = dynamo.get_item({
        "PK": create_pk(user_id),
        "SK": "PROFILE"
    })
    partner = dynamo.get_item({
        "PK": create_pk(partner_id),
        "SK": "PROFILE"
    })
    
    if not user or not partner:
        raise ValueError("Both users must be registered")
    
    # Update both users
    user_obj = User(**user)
    partner_obj = User(**partner)
    
    user_obj.partner_id = partner_id
    partner_obj.partner_id = user_id
    
    # Store updates
    dynamo.put_item({
        "PK": create_pk(user_id),
        "SK": "PROFILE",
        **user_obj.model_dump()
    })
    
    dynamo.put_item({
        "PK": create_pk(partner_id),
        "SK": "PROFILE",
        **partner_obj.model_dump()
    })
    
    # Send notifications
    await telegram.send_message(
        chat_id=user_obj.chat_id_private,
        text=f"You have been linked with {partner_obj.name or 'your partner'} 💕"
    )
    
    await telegram.send_message(
        chat_id=partner_obj.chat_id_private,
        text=f"You have been linked with {user_obj.name or 'your partner'} 💕"
    )
    
    return {
        "message": "Partners linked successfully",
        "user_id": user_id,
        "partner_id": partner_id
    }
