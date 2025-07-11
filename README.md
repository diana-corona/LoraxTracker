# 🌙 Lorax Blood Moon Tracker

A serverless menstrual cycle tracker built with Python that provides personalized recommendations based on Dr. Mindy Pelz's approach to cycle syncing and fasting.

## Features

- 🔄 Cycle tracking and phase detection
- 📊 Personalized phase-based recommendations
- 🍽️ Customized fasting protocols
- 🥗 Weekly shopping lists and meal planning
- 💪 Activity guidance based on hormonal phases
- 📱 Telegram bot integration
- 👥 Optional partner sharing

## Key Components

- Three functional phases based on Dr. Mindy Pelz's approach:
  - **Power Phase** (Days 1-10 & 16-19)
  - **Manifestation Phase** (Days 11-15)
  - **Nurture Phase** (Day 20+)

## Tech Stack

- Python 3.11+
- AWS Lambda & DynamoDB
- Serverless Framework
- Telegram Bot API
- AWS EventBridge
- Pydantic for data validation

## Development

1. Clone the repository:
```bash
git clone https://github.com/yourusername/lorax-tracker.git
cd lorax-tracker
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
# Set up your AWS credentials
aws configure

# Set up Telegram bot token in AWS SSM
aws ssm put-parameter \
    --name "/lorax/telegram-token" \
    --type "SecureString" \
    --value "your-bot-token"
```

4. Run tests:
```bash
pytest
```

5. Deploy:
```bash
serverless deploy
```

## Bot Commands

- `/start` - Initialize the bot
- `/registrar YYYY-MM-DD` - Register a cycle event
- `/fase` - Get current phase information
- `/prediccion` - Get cycle predictions

## Architecture

- `src/models/` - Data models and validation
- `src/services/` - Core business logic
- `src/handlers/` - Lambda function handlers
- `src/utils/` - Utility functions and clients
- `tests/` - Test suite

## Project Structure

```
lorax-tracker/
├── src/
│   ├── models/
│   │   ├── event.py
│   │   ├── phase.py
│   │   ├── recommendation.py
│   │   └── user.py
│   ├── services/
│   │   ├── cycle.py
│   │   ├── phase.py
│   │   ├── recommendation.py
│   │   └── shopping.py
│   ├── handlers/
│   │   ├── fase.py
│   │   ├── lista_semanal.py
│   │   ├── prediccion.py
│   │   ├── registrar.py
│   │   └── telegram.py
│   └── utils/
│       ├── dynamo.py
│       └── telegram.py
├── tests/
│   ├── conftest.py
│   ├── test_cycle.py
│   └── test_shopping.py
├── requirements.txt
├── serverless.yml
└── README.md
```

