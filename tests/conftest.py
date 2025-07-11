"""
Pytest configuration and shared fixtures.
"""
import pytest
from datetime import date, timedelta
from typing import List

from src.models.event import CycleEvent
from src.models.phase import PhaseType
from src.models.user import User
from src.models.recommendation import RecommendationType

@pytest.fixture
def sample_user() -> User:
    """Create a sample user for testing."""
    return User(
        user_id="123",
        chat_id_private="private123",
        chat_id_group="group123",
        user_type="principal",
        name="Test User",
        registration_date="2024-01-01T00:00:00"
    )

@pytest.fixture
def regular_cycle_events() -> List[CycleEvent]:
    """Create a list of regular cycle events."""
    return [
        CycleEvent(
            user_id="123",
            date=date(2024, 1, 1) + timedelta(days=i*28),
            state="menstruacion"
        )
        for i in range(5)
    ]

@pytest.fixture
def irregular_cycle_events() -> List[CycleEvent]:
    """Create a list of irregular cycle events."""
    return [
        CycleEvent(
            user_id="123",
            date=date(2024, 1, 1),
            state="menstruacion"
        ),
        CycleEvent(
            user_id="123",
            date=date(2024, 1, 25),  # 24 days
            state="menstruacion"
        ),
        CycleEvent(
            user_id="123",
            date=date(2024, 2, 25),  # 31 days
            state="menstruacion"
        ),
        CycleEvent(
            user_id="123",
            date=date(2024, 3, 22),  # 26 days
            state="menstruacion"
        )
    ]

@pytest.fixture
def phase_sequence_events() -> List[CycleEvent]:
    """Create a sequence of events covering different phases."""
    return [
        CycleEvent(
            user_id="123",
            date=date(2024, 1, 1),
            state=PhaseType.MENSTRUATION,
            pain_level=3,
            energy_level=2,
            notes="Started menstruation"
        ),
        CycleEvent(
            user_id="123",
            date=date(2024, 1, 5),
            state=PhaseType.FOLLICULAR,
            pain_level=1,
            energy_level=4,
            notes="Feeling more energetic"
        ),
        CycleEvent(
            user_id="123",
            date=date(2024, 1, 14),
            state=PhaseType.OVULATION,
            pain_level=1,
            energy_level=5,
            notes="Peak energy"
        ),
        CycleEvent(
            user_id="123",
            date=date(2024, 1, 17),
            state=PhaseType.LUTEAL,
            pain_level=2,
            energy_level=3,
            notes="Starting to feel tired"
        )
    ]

@pytest.fixture
def sample_recommendations() -> List[RecommendationType]:
    """Create sample recommendations for testing."""
    return [
        RecommendationType(
            category="ejercicio",
            priority=3,
            description="Gentle exercises like yoga or walking"
        ),
        RecommendationType(
            category="nutricion",
            priority=4,
            description="Focus on iron-rich foods"
        ),
        RecommendationType(
            category="descanso",
            priority=5,
            description="Ensure adequate rest and sleep"
        )
    ]

@pytest.fixture
def mock_dynamo_items() -> dict:
    """Create mock DynamoDB items for testing."""
    return {
        "PK": "USER#123",
        "SK": "EVENT#2024-01-01",
        "user_id": "123",
        "date": "2024-01-01",
        "state": "menstruacion",
        "pain_level": 3,
        "energy_level": 2,
        "notes": "Test event"
    }
