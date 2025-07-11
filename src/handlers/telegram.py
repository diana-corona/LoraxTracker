"""
Lambda handler for processing Telegram webhook requests.
"""
import json
from typing import Dict, Any, Optional
from datetime import datetime

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from src.utils.telegram import (
    TelegramClient,
    parse_command,
    validate_date,
    format_error_message,
    create_rating_keyboard
)
from src.utils.dynamo import DynamoDBClient, create_pk, create_event_sk
from src.models.event import CycleEvent
from src.services.cycle import calculate_next_cycle
from src.services.phase import get_current_phase, generate_phase_report
from src.services.recommendation import RecommendationEngine

logger = Logger()
tracer = Tracer()

dynamo = DynamoDBClient("TrackerTable")
telegram = TelegramClient()

@logger.inject_lambda_context
@tracer.capture_lambda_handler
async def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
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
        
        # Handle callback queries (button presses)
        if "callback_query" in body:
            return await handle_callback_query(body["callback_query"])
            
        # Handle text messages
        if "message" in body:
            return await handle_message(body["message"])
        
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Unsupported event type"})
        }
        
    except Exception as e:
        logger.exception("Error processing webhook")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

async def handle_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """Handle incoming text messages."""
    chat_id = str(message["chat"]["id"])
    user_id = str(message["from"]["id"])
    text = message.get("text", "")
    
    if not text:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "No text in message"})
        }
    
    command, args = parse_command(text)
    
    try:
        if command == "/start":
            return await handle_start_command(user_id, chat_id)
            
        elif command == "/registrar":
            if not args:
                return await telegram.send_message(
                    chat_id=chat_id,
                    text="Por favor proporciona una fecha en formato YYYY-MM-DD"
                )
            return await handle_register_event(user_id, chat_id, args[0])
            
        elif command == "/fase":
            return await handle_phase_command(user_id, chat_id)
            
        elif command == "/prediccion":
            return await handle_prediction_command(user_id, chat_id)
            
        else:
            return await telegram.send_message(
                chat_id=chat_id,
                text="Comando no reconocido. Usa /help para ver los comandos disponibles."
            )
            
    except Exception as e:
        logger.exception(f"Error handling command {command}")
        await telegram.send_message(
            chat_id=chat_id,
            text=format_error_message(e)
        )
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

async def handle_callback_query(callback_query: Dict[str, Any]) -> Dict[str, Any]:
    """Handle callback queries from inline keyboards."""
    try:
        chat_id = str(callback_query["message"]["chat"]["id"])
        user_id = str(callback_query["from"]["id"])
        data = json.loads(callback_query["data"])
        
        if data["action"] == "rate":
            return await handle_rating(
                user_id,
                chat_id,
                data["recommendation_id"],
                data["value"]
            )
            
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid callback action"})
        }
        
    except Exception as e:
        logger.exception("Error handling callback query")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

async def handle_start_command(user_id: str, chat_id: str) -> Dict[str, Any]:
    """Handle /start command."""
    welcome_text = (
        "¡Hola! Soy Lorax, tu asistente de ciclo menstrual. 🌙\n\n"
        "Puedes usar estos comandos:\n"
        "/registrar YYYY-MM-DD - Registrar un evento del ciclo\n"
        "/fase - Ver tu fase actual\n"
        "/prediccion - Ver predicción del próximo ciclo"
    )
    
    await telegram.send_message(
        chat_id=chat_id,
        text=welcome_text
    )
    
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Welcome message sent"})
    }

async def handle_register_event(
    user_id: str,
    chat_id: str,
    date_str: str
) -> Dict[str, Any]:
    """Handle /registrar command."""
    date_obj = validate_date(date_str)
    if not date_obj:
        await telegram.send_message(
            chat_id=chat_id,
            text="Fecha inválida. Usa el formato YYYY-MM-DD"
        )
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid date format"})
        }
    
    event = CycleEvent(
        user_id=user_id,
        date=date_obj.date(),
        state="menstruacion"  # Default to menstruation event
    )
    
    # Store in DynamoDB
    dynamo.put_item({
        "PK": create_pk(user_id),
        "SK": create_event_sk(date_str),
        **event.model_dump()
    })
    
    await telegram.send_message(
        chat_id=chat_id,
        text=f"✅ Evento registrado para {date_str}"
    )
    
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Event registered"})
    }

async def handle_phase_command(user_id: str, chat_id: str) -> Dict[str, Any]:
    """Handle /fase command."""
    # Get user's events
    events = dynamo.query_items(
        partition_key="PK",
        partition_value=create_pk(user_id)
    )
    
    if not events:
        await telegram.send_message(
            chat_id=chat_id,
            text="No hay eventos registrados. Usa /registrar para comenzar."
        )
        return {
            "statusCode": 404,
            "body": json.dumps({"error": "No events found"})
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
    await telegram.send_phase_report(chat_id, report)
    
    # Generate and send recommendations
    engine = RecommendationEngine(user_id)
    recommendation = engine.generate_recommendations(current_phase, cycle_events)
    
    await telegram.send_recommendation(
        chat_id,
        recommendation.recommendations
    )
    
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Phase report sent"})
    }

async def handle_prediction_command(user_id: str, chat_id: str) -> Dict[str, Any]:
    """Handle /prediccion command."""
    # Get user's events
    events = dynamo.query_items(
        partition_key="PK",
        partition_value=create_pk(user_id)
    )
    
    if not events:
        await telegram.send_message(
            chat_id=chat_id,
            text="No hay suficientes datos para hacer una predicción."
        )
        return {
            "statusCode": 404,
            "body": json.dumps({"error": "No events found"})
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
        f"🔮 Próximo ciclo esperado: {next_date}",
        f"📊 Duración promedio: {duration} días",
    ]
    
    if warning:
        message.append(f"⚠️ {warning}")
    
    await telegram.send_message(
        chat_id=chat_id,
        text="\n".join(message)
    )
    
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Prediction sent"})
    }

async def handle_rating(
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
        
        await telegram.send_message(
            chat_id=chat_id,
            text=f"¡Gracias por tu valoración! ({rating}⭐)"
        )
        
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Rating recorded"})
        }
        
    except Exception as e:
        logger.exception("Error recording rating")
        await telegram.send_message(
            chat_id=chat_id,
            text=format_error_message(e)
        )
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
