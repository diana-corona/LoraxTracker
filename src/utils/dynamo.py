"""
DynamoDB utility functions for data access.
"""
import os
from typing import Dict, List, Optional, Any
import boto3
from boto3.dynamodb.conditions import Key, Attr

# Singleton instance
_dynamo_instance = None

def get_dynamo():
    """Get or create singleton DynamoDB client instance."""
    global _dynamo_instance
    if _dynamo_instance is None:
        table_name = os.environ.get('DYNAMODB_TABLE', 'lorax-tracker-dev')
        _dynamo_instance = DynamoDBClient(table_name)
    return _dynamo_instance

class DynamoDBClient:
    """Client for interacting with DynamoDB table."""
    
    def __init__(self, table_name: str):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)
    
    def put_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Put a single item into the table.
        
        Args:
            item: Dictionary containing item attributes
            
        Returns:
            Response from DynamoDB
        """
        return self.table.put_item(Item=item)
    
    def get_item(self, key: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Get a single item from the table.
        
        Args:
            key: Dictionary containing partition key and sort key
            
        Returns:
            Item if found, None otherwise
        """
        response = self.table.get_item(Key=key)
        return response.get('Item')
    
    def query_items(
        self,
        partition_key: str,
        partition_value: str,
        sort_key_condition: Optional[Key] = None
    ) -> List[Dict[str, Any]]:
        """
        Query items using partition key and optional sort key condition.
        
        Args:
            partition_key: Name of partition key
            partition_value: Value of partition key
            sort_key_condition: Optional sort key condition
            
        Returns:
            List of matching items
        """
        key_condition = Key(partition_key).eq(partition_value)
        if sort_key_condition:
            key_condition = key_condition & sort_key_condition
        
        response = self.table.query(KeyConditionExpression=key_condition)
        return response.get('Items', [])
    
    def update_item(
        self,
        key: Dict[str, str],
        update_expression: str,
        expression_values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an item in the table.
        
        Args:
            key: Dictionary containing partition key and sort key
            update_expression: Update expression
            expression_values: Expression attribute values
            
        Returns:
            Response from DynamoDB
        """
        return self.table.update_item(
            Key=key,
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ReturnValues="ALL_NEW"
        )
    
    def delete_item(self, key: Dict[str, str]) -> Dict[str, Any]:
        """
        Delete an item from the table.
        
        Args:
            key: Dictionary containing partition key and sort key
            
        Returns:
            Response from DynamoDB
        """
        return self.table.delete_item(Key=key)

def create_pk(user_id: str) -> str:
    """Create partition key from user ID."""
    return f"USER#{user_id}"

def create_event_sk(date_str: str) -> str:
    """Create sort key for cycle events."""
    return f"EVENT#{date_str}"

def create_recommendation_sk(date_str: str) -> str:
    """Create sort key for recommendations."""
    return f"REC#{date_str}"

def create_recipe_history_sk(recipe_id: str, date_str: str) -> str:
    """
    Create sort key for recipe history entries.
    
    Used to track which recipes have been shown to users during meal planning
    to support recipe rotation and avoid repetition.

    Args:
        recipe_id: Recipe identifier (filename without extension)
        date_str: ISO format date string when recipe was shown

    Returns:
        Sort key in format "RECIPE#{recipe_id}#{date_str}"
    """
    return f"RECIPE#{recipe_id}#{date_str}"
