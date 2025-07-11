"""
Lambda handler for generating and sending weekly reports.
"""
from typing import Dict, List
from datetime import date, datetime, timedelta
import json

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from src.utils.dynamo import DynamoDBClient, create_pk
from src.utils.telegram import TelegramClient
from src.models.event import CycleEvent
from src.models.user import User
from src.services.phase import get_current_phase, generate_phase_report
from src.services.cycle import calculate_next_cycle
from src.services.shopping import ShoppingListGenerator

logger = Logger()
tracer = Tracer()

dynamo = DynamoDBClient("TrackerTable")
telegram = TelegramClient()

@logger.inject_lambda_context
@tracer.capture_lambda_handler
async def handler(event: Dict, context: LambdaContext) -> Dict:
    """
    Handle weekly report generation and notifications.
    
    Args:
        event: EventBridge scheduled event
        context: Lambda context
        
    Returns:
        Response with notification status
    """
    try:
        # Get all users
        users = get_all_users()
        
        for user in users:
            try:
                await send_weekly_report(user)
            except Exception as e:
                logger.exception(f"Failed to send report for user {user.user_id}")
                continue
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Weekly reports sent to {len(users)} users'
            })
        }
        
    except Exception as e:
        logger.exception('Failed to process weekly reports')
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def get_all_users() -> List[User]:
    """
    Get all registered users from DynamoDB.
    
    Returns:
        List of User objects
    """
    # Query users by USER# prefix in PK
    users = dynamo.query_items(
        partition_key="PK",
        partition_value="USER#"
    )
    
    return [User(**user) for user in users]

def generate_shopping_list(items: Dict[str, List[str]]) -> str:
    """Generate formatted shopping list."""
    sections = ["🛒 Lista de Compras para la Próxima Semana"]
    
    emoji_map = {
        "proteinas": "🥩",
        "vegetales": "🥬",
        "frutas": "🍎",
        "grasas": "🥑",
        "carbohidratos": "🥖",
        "suplementos": "💊",
        "otros": "🧂"
    }
    
    for category, ingredients in items.items():
        if ingredients:
            emoji = emoji_map.get(category, "•")
            sections.append(f"\n{emoji} {category.title()}:")
            for item in ingredients:
                sections.append(f"  • {item}")
    
    return "\n".join(sections)

async def send_weekly_report(user: User) -> None:
    """
    Generate and send weekly report for a user.
    
    Args:
        user: User to generate report for
    """
    # Get user's events
    events = dynamo.query_items(
        partition_key="PK",
        partition_value=create_pk(user.user_id)
    )
    
    cycle_events = [
        CycleEvent(**event)
        for event in events
        if event["SK"].startswith("EVENT#")
    ]
    
    if not cycle_events:
        logger.warning(f"No events found for user {user.user_id}")
        return
    
    # Generate report sections
    sections = []
    
    # Current phase
    current_phase = get_current_phase(cycle_events)
    phase_report = generate_phase_report(current_phase, cycle_events)
    sections.append("📅 Estado Actual\n" + phase_report)
    
    # Next cycle prediction
    next_date, duration, warning = calculate_next_cycle(cycle_events)
    prediction = [
        "🔮 Próximo Ciclo",
        f"Fecha esperada: {next_date}",
        f"Duración promedio: {duration} días"
    ]
    if warning:
        prediction.append(f"⚠️ {warning}")
    sections.append("\n".join(prediction))
    
    # Recent symptoms
    recent_events = get_recent_events(cycle_events)
    if recent_events:
        symptoms = ["📋 Síntomas Recientes"]
        for event in recent_events:
            if event.pain_level or event.energy_level or event.notes:
                symptoms.append(f"\nFecha: {event.date}")
                if event.pain_level:
                    symptoms.append(f"Dolor: {'⭐' * event.pain_level}")
                if event.energy_level:
                    symptoms.append(f"Energía: {'⚡' * event.energy_level}")
                if event.notes:
                    symptoms.append(f"Notas: {event.notes}")
        sections.append("\n".join(symptoms))
    
    # Generate shopping list for next week
    shopping_items = ShoppingListGenerator.generate_weekly_list(current_phase)
    shopping_list = generate_shopping_list(shopping_items)
    sections.append(shopping_list)
    
    # Send report to private chat
    report = "\n\n".join(sections)
    await telegram.send_message(
        chat_id=user.chat_id_private,
        text=f"📊 Reporte Semanal\n\n{report}"
    )
    
    # Send to group chat if configured
    if user.chat_id_group:
        # For group chat, only send phase and prediction info
        group_sections = sections[:2]  # Current phase and prediction only
        group_report = "\n\n".join(group_sections)
        await telegram.send_message(
            chat_id=user.chat_id_group,
            text=f"📊 Reporte Semanal de {user.name or 'Usuario'}\n\n{group_report}"
        )

def get_recent_events(events: List[CycleEvent]) -> List[CycleEvent]:
    """Get events from the past week."""
    week_ago = date.today() - timedelta(days=7)
    return [e for e in events if e.date >= week_ago]
