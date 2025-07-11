# 🐍 Lorax Blood Moon Tracker - Implementation Guide

## 📋 Project Overview

A menstrual cycle tracking system built using:
- Python 3.11+ with strict typing
- Serverless Framework for AWS deployment
- DynamoDB single-table design
- Telegram Bot API for user interaction
- AWS EventBridge for weekly reports
- Dr. Mindy Pelz's functional phase approach

## 🛠️ Development Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Install Serverless Framework
npm install -g serverless
npm install --save-dev serverless-python-requirements
```

## 📁 Project Structure

```
lorax-tracker/
├── serverless.yml           # Serverless Framework configuration
├── requirements.txt         # Python dependencies
├── mypy.ini                # Type checking configuration
├── pytest.ini              # Test configuration
├── TODO.md                 # Pending tasks and improvements
├── src/
│   ├── models/             # Pydantic models
│   │   ├── __init__.py
│   │   ├── user.py        # User profiles
│   │   ├── event.py       # Cycle events
│   │   ├── phase.py       # Traditional and functional phases
│   │   └── recommendation.py  # Personalized recommendations
│   ├── services/          
│   │   ├── __init__.py
│   │   ├── cycle.py       # Cycle calculations
│   │   ├── phase.py       # Phase detection
│   │   ├── recommendation.py  # Recommendation engine
│   │   └── shopping.py    # Shopping list generation
│   ├── handlers/          
│   │   ├── __init__.py
│   │   ├── telegram.py    # Main bot handler
│   │   ├── registrar.py   # User registration
│   │   ├── prediccion.py  # Cycle predictions
│   │   ├── fase.py       # Phase analysis
│   │   └── lista_semanal.py  # Weekly reports
│   └── utils/             
│       ├── __init__.py
│       ├── dynamo.py      # DynamoDB client
│       └── telegram.py    # Telegram bot utilities
└── tests/                 
    ├── conftest.py        # Test fixtures
    ├── test_cycle.py      # Cycle tests
    └── test_shopping.py   # Shopping list tests
```

## 🔄 Core Components

### Phase Model
```python
from enum import Enum
from datetime import date
from typing import Optional
from pydantic import BaseModel

class TraditionalPhaseType(str, Enum):
    MENSTRUATION = "menstruacion"
    FOLLICULAR = "folicular"
    OVULATION = "ovulacion"
    LUTEAL = "lutea"

class FunctionalPhaseType(str, Enum):
    POWER = "power"           # Days 1-10 & 16-19
    MANIFESTATION = "manifestation"  # Days 11-15
    NURTURE = "nurture"       # Day 20+

class Phase(BaseModel):
    traditional_phase: TraditionalPhaseType
    functional_phase: FunctionalPhaseType
    start_date: date
    end_date: date
    duration: int
    dietary_style: str
    fasting_protocol: str
    food_recommendations: List[str]
    activity_recommendations: List[str]
    supplement_recommendations: Optional[List[str]] = None
```

### Telegram Bot Commands
```python
@logger.inject_lambda_context
@tracer.capture_lambda_handler
async def handler(event: Dict, context: LambdaContext) -> Dict:
    """
    Handle Telegram webhook requests:
    - /start - Initialize bot
    - /registrar YYYY-MM-DD - Register cycle event
    - /fase - Get current phase info
    - /prediccion - Get cycle predictions
    """
```

### Weekly Reports
```python
async def send_weekly_report(user: User) -> None:
    """
    Generate and send weekly report including:
    - Current phase status
    - Next cycle prediction
    - Recent symptoms
    - Shopping list for next week
    """
```

## 🚀 Deployment

1. Configure environment:
```bash
# AWS credentials
aws configure

# Telegram bot token
aws ssm put-parameter \
    --name "/lorax/telegram-token" \
    --type "SecureString" \
    --value "your-bot-token"
```

2. Deploy:
```bash
serverless deploy
```

3. Configure Telegram webhook:
```bash
curl -X POST https://api.telegram.org/bot$TOKEN/setWebhook \
     -H "Content-Type: application/json" \
     -d '{"url": "your-api-endpoint/webhook"}'
```

## 📝 Development Guidelines

1. **Type Safety**
   - Use type hints everywhere
   - Run mypy before commits
   - Use Pydantic models
   - Enable strict typing

2. **Testing**
   - Write unit tests
   - Use fixtures
   - Test edge cases
   - Mock external services

3. **Code Quality**
   - Follow PEP 8
   - Use Black formatter
   - Document all functions
   - Handle errors properly

## ⏭️ Next Steps

See `TODO.md` for:
- Bot documentation and user guide
- Testing and deployment tasks
- Translation requirements
- Feature improvements
- Infrastructure setup

## 🔒 Security Notes

- Store secrets in AWS Parameter Store
- Use proper IAM roles
- Validate all inputs
- Implement rate limiting
- Handle user data carefully
- Follow AWS security best practices
