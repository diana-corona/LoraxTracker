# Contributing Guidelines

## Code Organization

When adding new functionality to the codebase, follow these guidelines to maintain clean and maintainable code:

### 1. Module Structure

- Place code in the appropriate module based on its responsibility:
  - `src/handlers/` - Command and event handlers
  - `src/models/` - Data models and schemas
  - `src/services/` - Business logic and core functionality
  - `src/utils/` - Utility functions and helpers

### 2. Single Responsibility Principle

- Each module should have a single, well-defined purpose
- If a module grows too large or handles multiple concerns, split it into smaller modules
- Example: Telegram utilities are split into:
  - `formatters.py` - Message formatting only
  - `keyboards.py` - Keyboard creation only
  - `parsers.py` - Command parsing only
  - `validators.py` - Data validation only

### 3. New Feature Checklist

When adding a new feature:

1. **Identify the Responsibility**
   - What is the core purpose of this feature?
   - Which existing module category does it belong to?

2. **Choose Module Location**
   - Create a new module if it's a distinct responsibility
   - Add to existing module if it's closely related functionality
   - Consider creating a new package if it's a large feature with multiple components

3. **Code Structure**
   - Start with interfaces and models
   - Implement core logic in services
   - Add handlers for user interaction
   - Create utility functions only for reusable code

4. **Documentation**
   - Add docstrings to all new functions and classes
   - Update README.md if adding new commands or features
   - Include example usage where appropriate

### 4. Testing

- Create unit tests for new functionality
- Test files should mirror the structure of source files
- Example: `test_formatters.py` tests `formatters.py`

### 5. Code Guidelines

- Follow existing code style (use a linter)
- Keep functions focused and small
- Use descriptive names for functions and variables
- Add type hints to function parameters and returns
- Document complex logic with comments

### 6. Docstring Documentation

Python docstrings are documentation strings that appear right after the definition of a function, method, class, or module. We follow Google's docstring style:

```python
def process_user_data(user_id: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Process user data with given options.

    Args:
        user_id: The unique identifier of the user
        options: Optional dictionary of processing options where:
            - validate (bool): Whether to validate data
            - format (str): Output format ('json' or 'xml')

    Returns:
        Dict containing processed user data:
        {
            "user_id": str,
            "processed_at": datetime,
            "results": List[Dict]
        }

    Raises:
        ValidationError: If data validation fails
        UserNotFoundError: If user doesn't exist
    """
```

For classes:
```python
class UserService:
    """
    Service for managing user operations.

    This class handles all user-related operations including
    creation, updates, and data processing.

    Attributes:
        client: Database client instance
        cache_enabled: Whether caching is enabled
    """
```

For modules:
```python
"""
User management module.

This module provides functionality for managing users,
including registration, profile updates, and data processing.

Typical usage:
    service = UserService()
    user = service.create_user(name="John", email="john@example.com")
"""
```

Key docstring components:
1. First line: Brief, concise description
2. Detailed description (if needed)
3. Args: List all parameters with types and descriptions
4. Returns: What the function returns
5. Raises: Any exceptions that may be raised
6. Examples: Usage examples for complex functions

Benefits:
- Provides inline documentation accessible via help()
- Supports IDE tooltips and autocompletion
- Makes code self-documenting
- Helps maintain consistent documentation style

### 6. Logging Guidelines

- Use the aws_lambda_powertools Logger
- Log at appropriate levels:
  - ERROR - Errors that affect functionality
  - WARNING - Unexpected but handled cases
  - INFO - Normal operational events
  - DEBUG - Detailed information for debugging

- Include contextual information:
  ```python
  logger.info("Processing user request", extra={
      "user_id": user_id,
      "action": action,
      "parameters": params
  })
  ```

- Log command usage in handlers:
  ```python
  logger.info("Command executed", extra={
      "command": command,
      "user_id": user_id,
      "success": True,
      "duration_ms": duration
  })
  ```

- Log service operations:
  ```python
  logger.info("Service operation", extra={
      "operation": "create_user",
      "status": "success",
      "details": {"user_id": user_id}
  })
  ```

- Add error context:
  ```python
  try:
      process_data()
  except Exception as e:
      logger.exception(
          "Error processing data",
          extra={
              "error_type": e.__class__.__name__,
              "data_id": data_id
          }
      )
  ```

### 7. Security Guidelines

- **Centralized Authorization**: All authorization is handled by the main webhook handler (`src/handlers/telegram/handler.py`):
  ```python
  # Authorization is centralized in the handler for ALL interactions
  # including both regular messages and callback queries (button clicks)
  if not auth.check_user_authorized(user_id):
      logger.warning("Unauthorized access attempt")
      return silent_success_response()
  ```
  - Do NOT add authorization checks in individual command handlers
  - Do NOT use the @require_auth decorator (it's redundant)
  - All user interactions (messages, buttons, etc.) are authorized at entry
  - This prevents security holes and unauthorized access attempts

- Never reveal bot existence to unauthorized users:
  ```python
  # Don't do this:
  if not auth.check_user_authorized(user_id):
      telegram.send_message(
          chat_id=chat_id,
          text="You are not authorized"  # Don't send any message
      )

  # Do this instead:
  if not auth.check_user_authorized(user_id):
      logger.warning("Unauthorized access attempt", extra={
          "user_id": user_id
      })
      return {
          "statusCode": 200,
          "headers": {"Content-Type": "application/json"},
          "body": json.dumps({"ok": True})  # Silent response
      }
  ```

- Log security events appropriately:
  - Unauthorized access attempts (WARNING level)
  - Authentication failures (WARNING level)
  - Successful authorizations (INFO level)
  - Token/session management (INFO level)

- Handle authorization failures silently:
  - No error messages to unauthorized users
  - No indication of bot existence
  - Return standard Telegram API success response
  - Internal logging only for monitoring

### 8. Error Handling Guidelines

- Use specific exception types:
  ```python
  class ValidationError(Exception):
      """Raised when input validation fails."""
      pass
  
  class ResourceNotFoundError(Exception):
      """Raised when a requested resource is not found."""
      pass
  ```

- Structure error handling consistently:
  ```python
  def process_user_data(user_id: str) -> Dict[str, Any]:
      try:
          user = get_user(user_id)
          if not user:
              raise ResourceNotFoundError(f"User {user_id} not found")
          
          processed_data = process_data(user)
          if not processed_data:
              raise ValidationError("Failed to process user data")
              
          return processed_data
          
      except ResourceNotFoundError as e:
          logger.warning(str(e), extra={"user_id": user_id})
          raise
          
      except ValidationError as e:
          logger.error("Data processing failed", extra={
              "user_id": user_id,
              "error": str(e)
          })
          raise
          
      except Exception as e:
          logger.exception("Unexpected error", extra={
              "user_id": user_id,
              "error_type": e.__class__.__name__
          })
          raise
  ```

- Return meaningful error responses:
  ```python
  def handle_error(e: Exception) -> Dict[str, Any]:
      if isinstance(e, ResourceNotFoundError):
          return {
              "statusCode": 404,
              "body": {"error": str(e)}
          }
      if isinstance(e, ValidationError):
          return {
              "statusCode": 400,
              "body": {"error": str(e)}
          }
      return {
          "statusCode": 500,
          "body": {"error": "Internal server error"}
      }
  ```

### 8. Package Organization

For larger features that require multiple files:

```
src/
└── feature_name/
    ├── __init__.py     # Package exports
    ├── models.py       # Data models
    ├── handlers.py     # Request handlers
    ├── services.py     # Business logic
    └── utils/          # Feature-specific utilities
        ├── __init__.py
        └── helpers.py
```

### 9. Import Organization

- Group imports by type:
  ```python
  # Standard library
  import json
  from typing import Dict, Any
  
  # Third-party
  import requests
  
  # Local
  from src.utils.formatters import format_message
  ```

### 10. Breaking Changes

When making breaking changes:

1. Document the changes in CHANGELOG.md
2. Update all affected tests
3. Consider backward compatibility
4. Update documentation

### 11. Review Checklist

Before submitting code:

- [ ] Code follows single responsibility principle
- [ ] Documentation is complete
- [ ] Tests are written and passing
- [ ] Code is properly formatted
- [ ] No unused imports or variables
- [ ] Error handling is in place
- [ ] Logging is added where appropriate

## Complete Example

Adding a new notification feature:

```python
# src/notifications/exceptions.py
class NotificationError(Exception):
    """Base exception for notification errors."""
    pass

class DeliveryError(NotificationError):
    """Raised when notification delivery fails."""
    pass

# src/notifications/models.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Notification:
    """Model representing a notification."""
    user_id: str
    message: str
    priority: str = "normal"
    sent_at: Optional[datetime] = None
    status: str = "pending"

# src/notifications/formatters.py
from typing import Dict, Any
from .models import Notification

def format_notification(notification: Notification) -> str:
    """
    Format notification message with standard template.
    
    Args:
        notification: Notification object to format
        
    Returns:
        Formatted message string with appropriate emoji
    """
    priority_emoji = {
        "high": "🔴",
        "normal": "📢",
        "low": "📝"
    }
    emoji = priority_emoji.get(notification.priority, "📢")
    return f"{emoji} {notification.message}"

# src/notifications/services.py
from typing import Dict, Any
from aws_lambda_powertools import Logger
from .models import Notification
from .exceptions import DeliveryError

logger = Logger()

class NotificationService:
    """Core notification functionality."""
    
    def __init__(self, client: NotificationClient):
        """
        Initialize notification service.
        
        Args:
            client: Client for sending notifications
        """
        self.client = client
    
    def send_notification(self, notification: Notification) -> bool:
        """
        Send notification to user.
        
        Args:
            notification: Notification object to send
            
        Returns:
            bool: True if sent successfully
            
        Raises:
            DeliveryError: If notification fails to send
        """
        try:
            formatted = format_notification(notification)
            success = self.client.send(notification.user_id, formatted)
            
            if not success:
                raise DeliveryError(f"Failed to deliver notification to {notification.user_id}")
                
            notification.status = "sent"
            notification.sent_at = datetime.utcnow()
            
            logger.info(
                "Notification sent successfully",
                extra={
                    "user_id": notification.user_id,
                    "priority": notification.priority,
                    "status": notification.status
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Error sending notification",
                extra={
                    "user_id": notification.user_id,
                    "error": str(e),
                    "error_type": e.__class__.__name__
                }
            )
            raise DeliveryError(f"Notification delivery failed: {str(e)}") from e

# src/notifications/handlers.py
from typing import Dict, Any
from aws_lambda_powertools import Logger
from .models import Notification
from .services import NotificationService
from .exceptions import NotificationError

logger = Logger()

def handle_notification(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle sending a notification request.
    
    Args:
        event: Lambda event containing notification details
        
    Returns:
        API Gateway response
    """
    try:
        # Extract and validate parameters
        body = event.get("body", {})
        user_id = body.get("user_id")
        message = body.get("message")
        priority = body.get("priority", "normal")
        
        if not all([user_id, message]):
            return {
                "statusCode": 400,
                "body": {"error": "Missing required fields"}
            }
            
        # Create notification object
        notification = Notification(
            user_id=user_id,
            message=message,
            priority=priority
        )
        
        # Send notification
        service = NotificationService()
        service.send_notification(notification)
        
        logger.info(
            "Notification request handled",
            extra={
                "user_id": user_id,
                "priority": priority,
                "status": "success"
            }
        )
        
        return {
            "statusCode": 200,
            "body": {
                "message": "Notification sent successfully",
                "notification_id": str(notification.id)
            }
        }
        
    except NotificationError as e:
        logger.warning(
            "Notification failed",
            extra={
                "error": str(e),
                "user_id": user_id if 'user_id' in locals() else None
            }
        )
        return {
            "statusCode": 400,
            "body": {"error": str(e)}
        }
        
    except Exception as e:
        logger.exception("Unexpected error handling notification")
        return {
            "statusCode": 500,
            "body": {"error": "Internal server error"}
        }
```

This example demonstrates:
- Clear separation of concerns
- Proper error handling with custom exceptions
- Consistent logging with context
- Type hints and documentation
- Data validation
- Clean code organization

Following these guidelines helps maintain code quality and makes the codebase easier to understand and modify in the future.
