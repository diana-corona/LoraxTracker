"""
Authorization utilities for access control.
"""
import os
from typing import Optional
from datetime import datetime

from src.utils.dynamo import DynamoDBClient

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
        """
        # Handle mock result first to prevent any DynamoDB interactions in test mode
        if self._mock_result is not None:
            return self._mock_result

        try:
            # Only try to use DynamoDB if we have a client
            if not self.dynamo:
                return False

            allowed_user = self.dynamo.get_item({
                "PK": f"ALLOWED_USER#{user_id}",
                "SK": "METADATA"
            })
            return bool(allowed_user and allowed_user.get("status") == "active")
        except Exception:
            return False
    
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
