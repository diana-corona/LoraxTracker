# 🐍 Lorax Blood Moon Tracker - Python Implementation Guide

## 📋 Project Overview

A menstrual cycle tracking system rebuilt using:
- Python 3.11+ with strict typing
- Serverless Framework for AWS deployment
- DynamoDB single-table design
- Telegram Bot API
- AWS EventBridge for scheduling

## 🛠️ Development Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install dependencies
pip install \
  aws-lambda-powertools \
  boto3 \
  python-telegram-bot \
  pydantic \
  mypy \
  pytest \
  pytest-asyncio \
  black \
  isort \
  pylint

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
├── src/
│   ├── models/             # Pydantic models for type safety
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── event.py
│   │   ├── phase.py
│   │   └── recommendation.py
│   ├── services/           # Business logic
│   │   ├── __init__.py
│   │   ├── cycle.py
│   │   ├── phase.py
│   │   └── recommendation.py
│   ├── handlers/           # Lambda handlers
│   │   ├── __init__.py
│   │   ├── telegram.py
│   │   ├── registrar.py
│   │   ├── prediccion.py
│   │   ├── fase.py
│   │   └── lista_semanal.py
│   └── utils/              # Shared utilities
│       ├── __init__.py
│       ├── dynamo.py
│       └── telegram.py
└── tests/                  # Test files
    ├── conftest.py
    ├── test_cycle.py
    └── test_phase.py
```

## 🔑 Key Type Definitions

```python
# src/models/user.py
from typing import Optional
from pydantic import BaseModel, Field

class User(BaseModel):
    user_id: str
    chat_id_private: str
    chat_id_group: Optional[str] = None
    partner_id: Optional[str] = None
    user_type: str = Field(..., pattern="^(principal|pareja)$")
    name: Optional[str] = None
    registration_date: str

# src/models/event.py
from datetime import date
from typing import Optional
from pydantic import BaseModel, Field

class CycleEvent(BaseModel):
    user_id: str
    date: date
    state: str = Field(..., pattern="^(menstruacion|folicular|ovulacion|lutea)$")
    pain_level: Optional[int] = Field(None, ge=0, le=5)
    energy_level: Optional[int] = Field(None, ge=0, le=5)
    notes: Optional[str] = None
```

## 🔄 Example Lambda Handler (Prediction)

```python
# src/handlers/prediccion.py
from typing import Dict, List, Optional, Tuple
from datetime import date, timedelta
import json

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import BaseModel, Field

logger = Logger()
tracer = Tracer()

class PredictionRequest(BaseModel):
    user_id: str
    chat_id: str
    chat_type: str = Field(..., pattern="^(private|group)$")

class PredictionResponse(BaseModel):
    next_cycle_date: date
    average_duration: int
    warning: Optional[str] = None

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: Dict, context: LambdaContext) -> Dict:
    try:
        request = PredictionRequest(**json.loads(event['body']))
        response = calculate_prediction(request)
        return {
            'statusCode': 200,
            'body': response.model_dump_json()
        }
    except Exception as e:
        logger.exception('Failed to process prediction')
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def calculate_prediction(request: PredictionRequest) -> PredictionResponse:
    # Implementation similar to Rust version but with Python type hints
    ...
```

## 🚀 Serverless Framework Configuration

```yaml
# serverless.yml
service: lorax-tracker

provider:
  name: aws
  runtime: python3.11
  region: us-west-2
  environment:
    POWERTOOLS_SERVICE_NAME: ${self:service}
    TELEGRAM_BOT_TOKEN: ${ssm:/lorax/telegram-token}
  iam:
    role:
      statements:
        - Effect: Allow
          Action:
            - dynamodb:*
          Resource: !GetAtt TrackerTable.Arn

plugins:
  - serverless-python-requirements

custom:
  pythonRequirements:
    layer:
      name: lorax-dependencies
      description: Python dependencies for Lorax Tracker
    noDeploy:
      - pytest
      - mypy
      - black
      - isort
      - pylint

functions:
  telegram:
    handler: src.handlers.telegram.handler
    events:
      - http:
          path: /webhook
          method: post
  
  prediccion:
    handler: src.handlers.prediccion.handler
    events:
      - http:
          path: /predict
          method: post

  lista_semanal:
    handler: src.handlers.lista_semanal.handler
    events:
      - schedule: 
          rate: cron(0 8 ? * SAT *)
          enabled: true

resources:
  Resources:
    TrackerTable:
      Type: AWS::DynamoDB::Table
      Properties:
        BillingMode: PAY_PER_REQUEST
        AttributeDefinitions:
          - AttributeName: PK
            AttributeType: S
          - AttributeName: SK
            AttributeType: S
        KeySchema:
          - AttributeName: PK
            KeyType: HASH
          - AttributeName: SK
            KeyType: RANGE
```

## 🧪 Testing Configuration

```ini
# mypy.ini
[mypy]
python_version = 3.11
strict = True
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
disallow_untyped_decorators = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
warn_unreachable = True

# pytest.ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

## ✅ Example Test

```python
# tests/test_cycle.py
import pytest
from datetime import date, timedelta
from src.models.event import CycleEvent
from src.services.cycle import calculate_next_cycle

def test_prediction_with_regular_cycles():
    events = [
        CycleEvent(
            user_id="123",
            date=date(2024, 1, 1) + timedelta(days=i*28),
            state="menstruacion"
        )
        for i in range(5)
    ]
    
    next_date, duration, warning = calculate_next_cycle(events)
    assert duration == 28
    assert warning is None
    assert next_date == date(2024, 4, 29)
```

## 📝 Development Guidelines

1. **Type Safety**
   - Use type hints everywhere
   - Run `mypy` before commits
   - Use Pydantic for data validation
   - Enable strict type checking

2. **Code Quality**
   - Use Black for formatting
   - Run pylint for static analysis
   - Use isort for import sorting
   - Follow PEP 8 guidelines

3. **Testing**
   - Write unit tests for all business logic
   - Use pytest fixtures for common setup
   - Mock AWS services in tests
   - Aim for high test coverage

4. **Logging & Monitoring**
   - Use AWS Lambda Powertools for structured logging
   - Add tracing for performance monitoring
   - Log all critical operations
   - Include correlation IDs

5. **Security**
   - Store secrets in AWS Parameter Store
   - Implement proper authentication
   - Validate all inputs
   - Use least-privilege IAM roles

## 🚀 Deployment Steps

1. Set up AWS credentials
2. Configure Telegram bot token in Parameter Store
3. Deploy with Serverless Framework:
   ```bash
   serverless deploy
   ```
4. Configure Telegram webhook with deployed API endpoint

## 💡 Key Differences from Rust Version

1. **Type Safety**
   - Python's type hints vs Rust's static typing
   - Runtime vs compile-time checks
   - Pydantic for validation
   - MyPy for static analysis

2. **Error Handling**
   - Python exceptions vs Rust's Result type
   - More explicit error handling required
   - Use custom exceptions for business logic

3. **Async Support**
   - Python's asyncio vs Rust's async/await
   - More explicit async handling
   - Different concurrency patterns

4. **Memory Management**
   - Python's GC vs Rust's ownership system
   - Different performance characteristics
   - Different resource management patterns

5. **Infrastructure**
   - Serverless Framework vs AWS SAM
   - Different deployment patterns
   - Different local development experience
