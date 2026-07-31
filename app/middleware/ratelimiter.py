"""
Hand-rolled token bucket rate limiter backed by Redis.

Each API key has its own bucket per endpoint type (eval / crud).
State is stored in Redis — survives restarts and is consistent
across multiple backend instances.

The Lua script runs atomically: Redis executes it as a single command,
so there is no TOCTOU race between reading and decrementing the bucket.
"""

import time
from fastapi import Depends, HTTPException, status
from app.redis_client import redis_client
from app.middleware.auth import get_api_key
from app.config import settings

# ---------------------------------------------------------------------------
# Lua script — token bucket
# ---------------------------------------------------------------------------
# KEYS[1]  base Redis key  e.g. "ratelimit:<api_key>:eval"
# ARGV[1]  current timestamp (float seconds)
# ARGV[2]  capacity  (integer)
# ARGV[3]  refill_rate (tokens per second, float)
#
# Returns 1 if allowed, 0 if rate-limited.

_LUA_RATE_LIMIT = """
local tokens_key      = KEYS[1] .. ":tokens"
local last_refill_key = KEYS[1] .. ":last_refill"

local now         = tonumber(ARGV[1])
local capacity    = tonumber(ARGV[2])
local refill_rate = tonumber(ARGV[3])

local last_refill = tonumber(redis.call("GET", last_refill_key))
local tokens      = tonumber(redis.call("GET", tokens_key))

if last_refill == nil then last_refill = now end
if tokens      == nil then tokens      = capacity end

local elapsed = now - last_refill
if elapsed < 0 then elapsed = 0 end

tokens = tokens + elapsed * refill_rate
if tokens > capacity then tokens = capacity end

if tokens < 1 then
    redis.call("SET", tokens_key,      tokens)
    redis.call("SET", last_refill_key, now)
    return 0
end

tokens = tokens - 1
redis.call("SET", tokens_key,      tokens)
redis.call("SET", last_refill_key, now)
return 1
"""

_script = redis_client.register_script(_LUA_RATE_LIMIT)


def _check(api_key: str, bucket: str, multiplier: float) -> None:
    """Run the Lua script for the given bucket. Raises 429 if rate-limited."""
    redis_key = f"ratelimit:{api_key}:{bucket}"
    now = time.time()
    capacity = int(settings.rate_limit_capacity * multiplier)
    refill_rate = settings.rate_limit_refill_rate * multiplier

    result = _script(keys=[redis_key], args=[now, capacity, refill_rate])
    if result == 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )


# ---------------------------------------------------------------------------
# Factory — creates a FastAPI dependency for a given bucket and multiplier
# ---------------------------------------------------------------------------

def _make_rate_limiter(bucket: str, multiplier: float):
    def dependency(api_key: str = Depends(get_api_key)) -> str:
        _check(api_key, bucket, multiplier)
        return api_key
    return dependency


rate_limit_eval = _make_rate_limiter("eval", multiplier=1.0)
rate_limit_crud = _make_rate_limiter("crud", multiplier=10.0)
