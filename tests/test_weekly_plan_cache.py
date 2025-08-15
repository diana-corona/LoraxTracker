"""
Tests for weekly plan caching service.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import time

from src.services.weekly_plan_cache import WeeklyPlanCache, WeeklyPlanCacheError

@pytest.fixture
def cache():
    """Create WeeklyPlanCache instance with mocked DynamoDB."""
    with patch('src.services.weekly_plan_cache.get_dynamo') as mock_get_dynamo:
        mock_dynamo = Mock()
        mock_get_dynamo.return_value = mock_dynamo
        yield WeeklyPlanCache(), mock_dynamo

def test_get_week_start(cache):
    """Test _get_week_start returns correct Monday date."""
    cache_service, _ = cache
    
    # Test for a Wednesday
    test_date = datetime(2025, 12, 10)  # A Wednesday
    week_start = cache_service._get_week_start(test_date)
    assert week_start == "2025-12-08"  # Should be Monday
    
    # Test for a Sunday
    test_date = datetime(2025, 12, 14)  # A Sunday
    week_start = cache_service._get_week_start(test_date)
    assert week_start == "2025-12-08"  # Should still be previous Monday
    
    # Test for a Monday
    test_date = datetime(2025, 12, 8)  # A Monday
    week_start = cache_service._get_week_start(test_date)
    assert week_start == "2025-12-08"  # Should be same day

def test_calculate_ttl(cache):
    """Test TTL calculation is 7 days in future."""
    cache_service, _ = cache
    current_time = time.time()
    ttl = cache_service._calculate_ttl()
    
    # TTL should be ~7 days in future (allow 1 second tolerance)
    expected_ttl = current_time + (7 * 24 * 60 * 60)
    assert abs(ttl - expected_ttl) <= 1

def test_get_cached_plan_hit(cache):
    """Test retrieving valid cached plan."""
    cache_service, mock_dynamo = cache
    
    # Setup mock
    mock_plan = {
        'plan_data': {'test': 'data'},
        'ttl': int(time.time()) + 3600  # Valid for 1 more hour
    }
    mock_dynamo.get_item.return_value = mock_plan
    
    # Test
    result = cache_service.get_cached_plan("123456")
    assert result == {'test': 'data'}
    assert mock_dynamo.get_item.called

def test_get_cached_plan_expired(cache):
    """Test retrieving expired cached plan returns None."""
    cache_service, mock_dynamo = cache
    
    # Setup mock with expired TTL
    mock_plan = {
        'plan_data': {'test': 'data'},
        'ttl': int(time.time()) - 3600  # Expired 1 hour ago
    }
    mock_dynamo.get_item.return_value = mock_plan
    
    # Test
    result = cache_service.get_cached_plan("123456")
    assert result is None
    assert mock_dynamo.get_item.called

def test_get_cached_plan_miss(cache):
    """Test behavior when no cached plan exists."""
    cache_service, mock_dynamo = cache
    
    # Setup mock
    mock_dynamo.get_item.return_value = None
    
    # Test
    result = cache_service.get_cached_plan("123456")
    assert result is None
    assert mock_dynamo.get_item.called

def test_get_cached_plan_error(cache):
    """Test error handling when retrieving cached plan."""
    cache_service, mock_dynamo = cache
    
    # Setup mock to raise exception
    mock_dynamo.get_item.side_effect = Exception("DynamoDB error")
    
    # Test
    with pytest.raises(WeeklyPlanCacheError) as exc:
        cache_service.get_cached_plan("123456")
    assert "Failed to retrieve cached plan" in str(exc.value)

def test_cache_plan_success(cache):
    """Test successfully caching a plan."""
    cache_service, mock_dynamo = cache
    
    plan_data = {
        'plan_text': 'Test plan',
        'shopping_list': 'Test list',
        'recipe_links': 'Test links'
    }
    
    # Test
    cache_service.cache_plan("123456", plan_data)
    
    # Verify
    assert mock_dynamo.put_item.called
    call_args = mock_dynamo.put_item.call_args[0][0]
    assert call_args['plan_data'] == plan_data
    assert 'ttl' in call_args
    assert 'cached_at' in call_args

def test_cache_plan_error(cache):
    """Test error handling when caching plan."""
    cache_service, mock_dynamo = cache
    
    # Setup mock to raise exception
    mock_dynamo.put_item.side_effect = Exception("DynamoDB error")
    
    # Test
    with pytest.raises(WeeklyPlanCacheError) as exc:
        cache_service.cache_plan("123456", {'test': 'data'})
    assert "Failed to cache plan" in str(exc.value)
