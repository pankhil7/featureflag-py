"""Unit tests for the token bucket rate limiter logic."""

import pytest
from app.hash import compute_hash


# ---------------------------------------------------------------------------
# Token bucket logic — pure Python implementation mirroring the Lua script.
# Tests the algorithm in isolation without Redis.
# ---------------------------------------------------------------------------

def token_bucket(
    tokens: float,
    last_refill: float,
    now: float,
    capacity: float,
    refill_rate: float,
) -> tuple[bool, float, float]:
    """
    Pure Python implementation of the token bucket algorithm.
    Returns (allowed, new_tokens, new_last_refill).
    """
    elapsed = max(now - last_refill, 0)
    tokens = min(tokens + elapsed * refill_rate, capacity)

    if tokens < 1:
        return False, tokens, now

    return True, tokens - 1, now


def test_full_bucket_allows_request():
    allowed, tokens, _ = token_bucket(
        tokens=10, last_refill=0.0, now=0.0,
        capacity=10, refill_rate=1.0,
    )
    assert allowed is True
    assert tokens == 9


def test_empty_bucket_rejects_request():
    allowed, tokens, _ = token_bucket(
        tokens=0, last_refill=0.0, now=0.0,
        capacity=10, refill_rate=1.0,
    )
    assert allowed is False


def test_bucket_refills_over_time():
    # Start empty, wait 5 seconds at 2 tokens/sec → 10 tokens refilled → allow
    allowed, tokens, _ = token_bucket(
        tokens=0, last_refill=0.0, now=5.0,
        capacity=10, refill_rate=2.0,
    )
    assert allowed is True
    assert tokens == 9  # 10 refilled - 1 consumed


def test_bucket_caps_at_capacity():
    # Even if a lot of time passes, tokens can't exceed capacity
    allowed, tokens, _ = token_bucket(
        tokens=0, last_refill=0.0, now=1000.0,
        capacity=10, refill_rate=1.0,
    )
    assert allowed is True
    assert tokens == 9  # capped at 10, minus 1 consumed


def test_burst_then_exhaustion():
    """Burst of requests exhausts bucket, then refill allows more."""
    capacity = 5
    refill_rate = 1.0
    tokens = float(capacity)
    last_refill = 0.0
    now = 0.0

    # Consume all 5 tokens
    for _ in range(5):
        allowed, tokens, last_refill = token_bucket(tokens, last_refill, now, capacity, refill_rate)
        assert allowed is True

    # 6th request at same time — rejected
    allowed, tokens, last_refill = token_bucket(tokens, last_refill, now, capacity, refill_rate)
    assert allowed is False

    # Wait 1 second — 1 token refilled — allowed again
    now = 1.0
    allowed, tokens, last_refill = token_bucket(tokens, last_refill, now, capacity, refill_rate)
    assert allowed is True


def test_multiplier_gives_more_capacity():
    """10× multiplier effectively gives 10× the capacity."""
    base_capacity = 10
    multiplier = 10.0
    effective_capacity = base_capacity * multiplier  # 100

    tokens = effective_capacity
    last_refill = 0.0
    now = 0.0

    # Should be able to make 100 requests
    for _ in range(100):
        allowed, tokens, last_refill = token_bucket(
            tokens, last_refill, now, effective_capacity, 1.0 * multiplier
        )
        assert allowed is True

    # 101st should fail
    allowed, _, _ = token_bucket(tokens, last_refill, now, effective_capacity, 1.0 * multiplier)
    assert allowed is False
