"""
Lambda handlers package for AWS Lambda functions.
"""
from .telegram import handler
from .weekly_plan import handler as weekly_plan_handler

__all__ = ["handler", "weekly_plan_handler"]
