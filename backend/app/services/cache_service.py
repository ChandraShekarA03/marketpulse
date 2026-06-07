import json
import redis
from functools import wraps
from typing import Callable, Any
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Redis client
try:
    redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    # Test connection
    redis_client.ping()
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Caching will be disabled.")
    redis_client = None

def cache_response(ttl_seconds: int = 300):
    """
    Decorator to cache function responses in Redis.
    The cache key is generated from the function name and its arguments.
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not redis_client:
                return func(*args, **kwargs)
            
            # Construct a unique cache key
            key_parts = [func.__name__]
            key_parts.extend([str(a) for a in args])
            key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
            cache_key = ":".join(key_parts)
            
            try:
                cached_data = redis_client.get(cache_key)
                if cached_data:
                    logger.debug(f"Cache hit for {cache_key}")
                    return json.loads(cached_data)
            except Exception as e:
                logger.error(f"Redis get error: {e}")
            
            # Execute the actual function
            result = func(*args, **kwargs)
            
            try:
                if result:
                    # Cache the result
                    redis_client.setex(
                        cache_key,
                        ttl_seconds,
                        json.dumps(result)
                    )
                    logger.debug(f"Cached {cache_key} for {ttl_seconds}s")
            except Exception as e:
                logger.error(f"Redis set error: {e}")
                
            return result
        return wrapper
    return decorator
