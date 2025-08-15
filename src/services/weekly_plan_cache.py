"""
Weekly plan caching service.

This module provides functionality for caching and retrieving weekly meal plans
to avoid regenerating plans multiple times within the same week.

Typical usage:
    # Check for cached plan
    cache = WeeklyPlanCache()
    cached_plan = cache.get_cached_plan(user_id)
    if cached_plan:
        return cached_plan
    
    # Cache new plan after generation
    cache.cache_plan(user_id, plan_data)
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import time
from aws_lambda_powertools import Logger

from src.utils.dynamo import get_dynamo, create_pk, create_weekly_plan_sk

logger = Logger()

class WeeklyPlanCacheError(Exception):
    """Base exception for weekly plan cache errors."""
    pass

class WeeklyPlanCache:
    """Service for caching weekly meal plans."""

    def __init__(self):
        """Initialize weekly plan cache service."""
        self.dynamo = get_dynamo()

    def _get_week_start(self, date: Optional[datetime] = None) -> str:
        """
        Get the Monday of the current week.

        Args:
            date: Optional datetime to calculate week start for.
                 Defaults to current date if not provided.

        Returns:
            ISO format date string for Monday of the week
        """
        if date is None:
            date = datetime.now()
        monday = date - timedelta(days=date.weekday())
        return monday.date().isoformat()

    def _calculate_ttl(self) -> int:
        """
        Calculate TTL for cached plans (7 days from now).

        Returns:
            Unix timestamp for TTL
        """
        return int(time.time() + (7 * 24 * 60 * 60))

    def get_cached_plan(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached weekly plan for user if it exists.

        Args:
            user_id: Telegram user ID

        Returns:
            Dict containing cached plan data if found and valid,
            None otherwise

        Raises:
            WeeklyPlanCacheError: If there is an error accessing the cache
        """
        try:
            week_start = self._get_week_start()
            cached_plan = self.dynamo.get_item({
                "PK": create_pk(user_id),
                "SK": create_weekly_plan_sk(week_start)
            })

            if cached_plan:
                # Check if plan is still valid
                ttl = cached_plan.get('ttl', 0)
                if ttl > time.time():
                    logger.info("Retrieved cached weekly plan", extra={
                        "user_id": user_id,
                        "week_start": week_start,
                        "cache_hit": True
                    })
                    return cached_plan.get('plan_data')

            logger.info("No valid cached plan found", extra={
                "user_id": user_id,
                "week_start": week_start,
                "cache_hit": False
            })
            return None

        except Exception as e:
            logger.error("Error retrieving cached plan", extra={
                "user_id": user_id,
                "error": str(e),
                "error_type": e.__class__.__name__
            })
            raise WeeklyPlanCacheError(f"Failed to retrieve cached plan: {str(e)}")

    def cache_plan(
        self,
        user_id: str,
        plan_data: Dict[str, Any]
    ) -> None:
        """
        Cache weekly plan data.

        Args:
            user_id: Telegram user ID
            plan_data: Weekly plan data to cache including:
                - plan_text: Formatted weekly plan text
                - shopping_list: Formatted shopping list
                - recipe_links: Formatted recipe links
                - selections: Recipe selections data

        Raises:
            WeeklyPlanCacheError: If there is an error caching the plan
        """
        try:
            week_start = self._get_week_start()
            
            self.dynamo.put_item({
                "PK": create_pk(user_id),
                "SK": create_weekly_plan_sk(week_start),
                "plan_data": plan_data,
                "cached_at": datetime.now().isoformat(),
                "ttl": self._calculate_ttl()
            })

            logger.info("Cached weekly plan", extra={
                "user_id": user_id,
                "week_start": week_start
            })

        except Exception as e:
            logger.error("Error caching plan", extra={
                "user_id": user_id,
                "error": str(e),
                "error_type": e.__class__.__name__
            })
            raise WeeklyPlanCacheError(f"Failed to cache plan: {str(e)}")
