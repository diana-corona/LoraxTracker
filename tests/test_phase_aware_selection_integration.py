"""Integration tests for phase-aware recipe selection."""
import pytest
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch

from src.models.phase import FunctionalPhaseType
from src.models.weekly_plan import PhaseGroup, WeeklyPlan
from src.handlers.telegram.commands.weeklyplan import handle_weeklyplan_command, handle_recipe_callback
from src.services.recipe_selection_storage import RecipeSelectionStorage
from tests.test_phase_aware_selection import create_test_phase_group

@pytest.fixture
def mixed_phase_week():
    """Create a test week spanning power and nurture phases."""
    start = date(2025, 1, 1)
    power_group = create_test_phase_group(start, 2, FunctionalPhaseType.POWER)
    nurture_group = create_test_phase_group(start + timedelta(days=2), 5, FunctionalPhaseType.NURTURE)
    # Store both phase groups in immutable tuple to prevent list modification
    phase_groups = (power_group, nurture_group)
    print(f"Phase groups before test: {phase_groups}")
    return list(phase_groups)  # Return as list for compatibility

@pytest.fixture
def power_phase_group():
    """First phase group for analyzing cycle."""
    start = date(2025, 1, 1)
    return create_test_phase_group(start, 2, FunctionalPhaseType.POWER)

@pytest.fixture
def mock_telegram():
    """Mock Telegram client."""
    return Mock()

@pytest.fixture
def mock_recipe_service():
    """Mock recipe service with test data."""
    mock = Mock()
    
    # Set up test recipes
    power_recipes = [
        {
            "id": "power1",
            "title": "Power Recipe 1",
            "prep_time": 15,
            "phase": "power"
        },
        {
            "id": "power2",
            "title": "Power Recipe 2",
            "prep_time": 20,
            "phase": "power"
        }
    ]
    
    nurture_recipes = [
        {
            "id": "nurture1",
            "title": "Nurture Recipe 1",
            "prep_time": 25,
            "phase": "nurture"
        },
        {
            "id": "nurture2",
            "title": "Nurture Recipe 2",
            "prep_time": 30,
            "phase": "nurture"
        }
    ]
    
    # Configure mock methods
    mock.load_recipes_for_meal_planning = Mock()
    mock.get_recipes_by_meal_type.side_effect = lambda meal_type, phase, **kwargs: {
        "power": power_recipes,
        "nurture": nurture_recipes
    }.get(phase, [])
    mock.save_recipe_history = Mock()
    
    return mock

@patch('src.services.weekly_plan.group_consecutive_phases')  # Mock this first
@patch('src.services.weekly_plan.get_daily_phases')  
@patch('src.services.weekly_plan.generate_weekly_plan')
@patch('src.services.cycle.analyze_cycle_phase')
@patch('src.services.cycle.date')
@patch('src.handlers.telegram.commands.weeklyplan.datetime')
@patch('src.services.weekly_plan.datetime')
@patch('src.handlers.telegram.commands.weeklyplan.RecipeService')  
@patch('src.handlers.telegram.commands.weeklyplan.get_telegram')
@patch('src.handlers.telegram.commands.weeklyplan.get_dynamo')
def test_phase_aware_selection_flow(
    mock_get_dynamo,
    mock_get_telegram,
    mock_recipe_service_class,
    mock_datetime_weekly_plan,
    mock_datetime_command,
    mock_date_cycle,
    mock_analyze_cycle,
    mock_generate_weekly_plan,
    mock_get_daily_phases,
    mock_group_consecutive_phases,
    mixed_phase_week,
    power_phase_group,
    mock_telegram,
    mock_recipe_service
):
    """Test the complete phase-aware recipe selection flow."""
    # Setup mocks
    mock_get_telegram.return_value = mock_telegram
    mock_recipe_service_class.return_value = mock_recipe_service
    mock_datetime_weekly_plan.now.return_value = datetime(2025, 1, 1)
    mock_datetime_command.now.return_value = datetime(2025, 1, 1)
    mock_date_cycle.today.return_value = date(2025, 1, 1)
    mock_analyze_cycle.return_value = power_phase_group  # Use dedicated phase group for analysis
    print(f"Phase groups before weekly plan: {mixed_phase_week}")
    

    # Set up generate_weekly_plan mock with the weekly plan result
    print(f"Creating weekly plan for dates: {date(2025, 1, 1)} to {date(2025, 1, 7)}")
    
    # Ensure phase_groups list has both items
    assert len(mixed_phase_week) == 2, "Weekly plan should have 2 phase groups"
    
    # Mock both phases and groups consistently
    mock_group_consecutive_phases.return_value = mixed_phase_week

    mock_get_daily_phases.return_value = {
        date(2025, 1, 1): mixed_phase_week[0],
        date(2025, 1, 2): mixed_phase_week[0],
        date(2025, 1, 3): mixed_phase_week[1],
        date(2025, 1, 4): mixed_phase_week[1],
        date(2025, 1, 5): mixed_phase_week[1],
        date(2025, 1, 6): mixed_phase_week[1],
        date(2025, 1, 7): mixed_phase_week[1]
    }

    mock_generate_weekly_plan.return_value = (
        WeeklyPlan(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 7),
            next_cycle_date=date(2025, 1, 28),
            avg_cycle_duration=28,
            warning=None,
            phase_groups=mixed_phase_week
        ),
        []
    )
    print(f"Mock generate_weekly_plan returning phase groups: {mixed_phase_week}")

    # Mock DynamoDB
    mock_dynamo = Mock()
    
    # Configure mock behavior
    def mock_get_item(key):
        if key.get('PK') == 'ALLOWED_USER#user123' and key.get('SK') == 'METADATA':
            return {
                "PK": "ALLOWED_USER#user123",
                "SK": "METADATA",
                "user_id": "user123",
                "type": "user",
                "status": "active"
            }
        return None
    
    # Configure mock behavior for events
    mock_dynamo.get_item = mock_get_item
    mock_dynamo.table = Mock(name='test-table')
    mock_dynamo.query_items.return_value = [
            {
                "PK": "USER#user123",
                "SK": "EVENT#2025-01",
                "user_id": "user123",
                "date": "2025-01-01", 
                "state": "menstruation",
                "event_date": "2025-01-01",
                "duration": 28,
                "symptoms": []
            }
    ]
    mock_get_dynamo.return_value = mock_dynamo
    
    # Clear any previous recipe selections
    RecipeSelectionStorage._selections = {}
    
    # 1. Initial command - should show week analysis and first recipe selection
    handle_weeklyplan_command("user123", "chat123")
    
    # Verify week analysis was included in the first message
    plan_message = mock_telegram.send_message.call_args_list[0]
    full_text = plan_message.kwargs['text']
    assert "Power Phase ⚡: 2 days (29%" in full_text
    assert "Nurture Phase 🌱: 5 days (71%" in full_text
    
    # Verify recipe selection was started with phase-aware keyboard
    recipe_selection_call = mock_telegram.send_message.call_args_list[1]  # Now the second call
    keyboard = recipe_selection_call.kwargs['reply_markup']
    assert keyboard is not None, "Recipe selection keyboard not found"
    # Print for debugging
    print("Recipe selection keyboard:", keyboard)
    # Skip the multi-phase button and empty row, check first recipe button
    assert keyboard["inline_keyboard"][2][0]["text"].lower().startswith("⚡"), "First recipe should be power phase"
    
    # 2. Test multi-phase selection toggle
    multi_select_callback = {
        "body": {
            "callback_query": {
                "from": {"id": "user123"},
                "message": {
                    "chat": {"id": "chat123"},
                    "message_id": "789"
                },
                "data": "multi_select_breakfast"
            }
        }
    }

    handle_recipe_callback(multi_select_callback)

    print("\nAll send_message calls after multi-select:")
    for i, call in enumerate(mock_telegram.send_message.call_args_list):
        print(f"Call {i}: {call}")

    # Initially called once for power phase in handle_weeklyplan_command
    # Then called for each phase in order (power, nurture, manifestation) in the multi-select callback
    assert mock_recipe_service.load_recipes_for_meal_planning.call_count == 4
    load_calls = mock_recipe_service.load_recipes_for_meal_planning.call_args_list
    
    print("Load recipe calls:")
    for i, call in enumerate(load_calls):
        print(f"Call {i}: {call}")
    
    # First call is from initial command
    assert load_calls[0][1]['phase'] == 'power'
    # Next calls are from multi-select in order
    assert load_calls[1][1]['phase'] == 'power'
    assert load_calls[2][1]['phase'] == 'nurture'
    assert load_calls[3][1]['phase'] == 'manifestation'
    
    # Verify recipe fetching was called for each phase
    assert mock_recipe_service.get_recipes_by_meal_type.call_count >= 2
    get_calls = mock_recipe_service.get_recipes_by_meal_type.call_args_list
    assert any(call[1].get('phase') == 'power' for call in get_calls)
    assert any(call[1].get('phase') == 'nurture' for call in get_calls)
    
    # Verify phase-specific recipes were shown in the keyboard
    multi_phase_call = mock_telegram.edit_message_text.call_args_list[0]  # First edit_message_text call
    print(f"Multi-phase call kwargs: {multi_phase_call.kwargs}")
    keyboard = multi_phase_call.kwargs['reply_markup']
    buttons = keyboard["inline_keyboard"]
    
    # Print button info for debugging
    print(f"Buttons in keyboard: {len(buttons)}")
    for i, row in enumerate(buttons):
        print(f"Row {i}: {row}")
    
    # Now verify button content
    button_texts = [row[0]["text"] for row in buttons if row]  # Skip empty rows
    print(f"Button texts: {button_texts}")
    assert any("Power Phase" in text for text in button_texts)
    assert any("Nurture Phase" in text for text in button_texts)
    
    # 3. Select a power phase recipe
    power_selection_callback = {
        "body": {
            "callback_query": {
                "from": {"id": "user123"},
                "message": {
                    "chat": {"id": "chat123"},
                    "message_id": "789"
                },
                "data": "recipe_breakfast_power1_power"
            }
        }
    }
    
    handle_recipe_callback(power_selection_callback)
    
    # Verify recipe was stored with phase
    selection = RecipeSelectionStorage.get_selection("user123")
    assert len(selection.breakfast) == 1
    assert selection.breakfast[0].recipe_id == "power1"
    assert selection.breakfast[0].phase == "power"

    # 4. Add a nurture phase recipe
    nurture_selection_callback = {
        "body": {
            "callback_query": {
                "from": {"id": "user123"},
                "message": {
                    "chat": {"id": "chat123"},
                    "message_id": "789"
                },
                "data": "recipe_breakfast_nurture1_nurture"
            }
        }
    }
    
    handle_recipe_callback(nurture_selection_callback)
    
    # Verify both recipes are stored
    selection = RecipeSelectionStorage.get_selection("user123")
    assert len(selection.breakfast) == 2
    recipes = {(s.recipe_id, s.phase) for s in selection.breakfast}
    assert recipes == {("power1", "power"), ("nurture1", "nurture")}
