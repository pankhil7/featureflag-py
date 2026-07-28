import redis as redis_lib
from app.config import settings

# Single shared Redis client — thread-safe, uses connection pool internally.
redis_client = redis_lib.from_url(settings.redis_url, decode_responses=True)
