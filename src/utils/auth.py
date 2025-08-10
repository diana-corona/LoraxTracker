"""
Authorization utilities for access control.
"""
import os
from typing import Optional, Dict, Any
from datetime import datetime
import botocore

from aws_lambda_powertools import Logger
from src.utils.dynamo import DynamoDBClient, get_dynamo

logger = Logger()

class DynamoDBAccessError(Exception):
    """Raised when there is an error accessing DynamoDB."""
    pass

class AuthorizationError(Exception):
    """Raised when there is an error during authorization."""
    pass

class Authorization:
    """Authorization utility class."""
    
    def __init__(self, dynamo_client=None, mock_result=None):
        """
        Initialize Authorization utility.
        
        Args:
            dynamo_client: Optional DynamoDB client. If not provided, will create one.
            mock_result: Optional mock result for testing.
        """
        self._dynamo = dynamo_client
        self._mock_result = mock_result
    
    @property
    def dynamo(self):
        """Get or create DynamoDB client lazily."""
        if self._dynamo is None:
            self._dynamo = DynamoDBClient(os.environ['TRACKER_TABLE_NAME'])
        return self._dynamo
    
    def set_mock_result(self, result: bool) -> None:
        """
        Set mock result for testing.
        
        Args:
            result: True to allow access, False to deny
        """
        self._mock_result = result

    def check_user_authorized(self, user_id: str) -> bool:
        """
        Check if a user is authorized to use the bot.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bool: True if user is authorized, False otherwise
            
        Raises:
            DynamoDBAccessError: If there is an error accessing DynamoDB
        """
        # Handle mock result first to prevent any DynamoDB interactions in test mode
        if self._mock_result is not None:
            logger.debug("Using mock result for authorization", extra={
                "user_id": user_id,
                "mock_result": self._mock_result
            })
            return self._mock_result

        try:
            # Ensure DynamoDB client is initialized
            if not self.dynamo:
                logger.error("DynamoDB client not initialized", extra={
                    "user_id": user_id,
                    "error": "Client not initialized",
                    "table": os.environ.get('TRACKER_TABLE_NAME')
                })
                raise DynamoDBAccessError("DynamoDB client not initialized")

            lookup_key = {
                "PK": f"ALLOWED_USER#{user_id}",
                "SK": "METADATA"
            }

            # Log the lookup attempt with more context
            logger.debug("Checking user authorization", extra={
                "user_id": user_id,
                "lookup_key": lookup_key,
                "table": self.dynamo.table.name,
                "operation": "get_item"
            })

            allowed_user = self.dynamo.get_item(lookup_key)

            # Handle case where allowed_user is None
            if not allowed_user:
                logger.debug("User not found in allow list", extra={
                    "user_id": user_id,
                    "table": self.dynamo.table.name
                })
                return False

            # Get the status and log the result
            status = allowed_user.get("status")
            is_authorized = status == "active"

            # Enhanced logging with more context
            logger.debug("Authorization check result", extra={
                "user_id": user_id,
                "user_found": True,
                "user_status": status,
                "is_authorized": is_authorized,
                "lookup_key": lookup_key,
                "table": self.dynamo.table.name,
                "user_data": {k: v for k, v in allowed_user.items() if k not in ["PK", "SK"]}
            })

            return is_authorized

        except botocore.exceptions.ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            error_msg = e.response.get('Error', {}).get('Message')
            
            logger.error("DynamoDB access error", extra={
                "user_id": user_id,
                "error_code": error_code,
                "error_message": error_msg,
                "operation": "get_item",
                "table": os.environ.get('TRACKER_TABLE_NAME'),
                "lookup_key": lookup_key if 'lookup_key' in locals() else None
            })
            
            if error_code == "AccessDeniedException":
                raise DynamoDBAccessError(f"Access denied to DynamoDB: {error_msg}")
            elif error_code == "ResourceNotFoundException":
                raise DynamoDBAccessError(f"DynamoDB table not found: {error_msg}")
            else:
                raise DynamoDBAccessError(f"DynamoDB error ({error_code}): {error_msg}")

        except Exception as e:
            logger.error("Unexpected error checking user authorization", extra={
                "user_id": user_id,
                "error_type": e.__class__.__name__,
                "error_message": str(e),
                "table": os.environ.get('TRACKER_TABLE_NAME')
            })
            raise DynamoDBAccessError(f"Unexpected error accessing DynamoDB: {str(e)}")
    
    def add_allowed_user(
        self,
        user_id: str,
        user_type: str,
        added_by: str
    ) -> None:
        """
        Add a user to the allow list.
        
        Args:
            user_id: Telegram user ID to allow
            user_type: Type of user (user|partner|group)
            added_by: Telegram user ID of admin adding this user
        """
        self.dynamo.put_item({
            "PK": f"ALLOWED_USER#{user_id}",
            "SK": "METADATA",
            "user_id": user_id,
            "type": user_type,
            "added_by": added_by,
            "added_at": datetime.now().isoformat(),
            "status": "active"
        })
    
    def remove_allowed_user(self, user_id: str) -> None:
        """
        Remove a user from the allow list by setting status to inactive.
        
        Args:
            user_id: Telegram user ID to remove
        """
        self.dynamo.update_item(
            key={
                "PK": f"ALLOWED_USER#{user_id}",
                "SK": "METADATA"
            },
            update_expression="SET #status = :status",
            expression_values={
                ":status": "inactive"
            }
        )
    
    def verify_partner_access(
        self,
        user_id: str,
        partner_id: str
    ) -> bool:
        """
        Verify that both user and partner are authorized.
        
        Args:
            user_id: Requesting user's Telegram ID
            partner_id: Partner's Telegram ID
            
        Returns:
            bool: True if both users are authorized
        """
        return (
            self.check_user_authorized(user_id) and
            self.check_user_authorized(partner_id)
        )
    
    def verify_group_access(self, group_id: str) -> bool:
        """
        Verify that a group is authorized.
        
        Args:
            group_id: Telegram group chat ID
            
        Returns:
            bool: True if group is authorized
        """
        allowed_group = self.dynamo.get_item({
            "PK": f"ALLOWED_USER#{group_id}",
            "SK": "METADATA"
        })
        
        return bool(
            allowed_group and
            allowed_group.get("type") == "group" and
            allowed_group.get("status") == "active"
        )
