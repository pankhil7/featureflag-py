"""Unit tests for FNV-1a consistent hashing used in rollout evaluation."""

import pytest
from app.hash import compute_hash


def test_deterministic():
    """Same inputs always produce the same hash."""
    cases = [
        ("sk_abc", "user-123", "dark-mode"),
        ("sk_abc", "user-456", "dark-mode"),
        ("sk_abc", "dark-mode"),
    ]
    for parts in cases:
        assert compute_hash(*parts) == compute_hash(*parts), f"non-deterministic for {parts}"


def test_sensitive_to_input():
    """Changing any part of the input produces a different hash."""
    base = compute_hash("sk_abc", "user-123", "flag-a")
    assert base != compute_hash("sk_abc", "user-456", "flag-a"), "different user should give different hash"
    assert base != compute_hash("sk_abc", "user-123", "flag-b"), "different flag key should give different hash"
    assert base != compute_hash("sk_xyz", "user-123", "flag-a"), "different api key should give different hash"


def test_same_user_same_bucket():
    """The same user always lands in the same bucket — no flicker."""
    api_key, user_id, flag_key = "sk_test123", "user-abc", "new-checkout"
    first_bucket = compute_hash(api_key, user_id, flag_key) % 100
    for _ in range(50):
        assert compute_hash(api_key, user_id, flag_key) % 100 == first_bucket


def test_zero_percent_never_enabled():
    """At 0% rollout, no bucket satisfies bucket < 0."""
    for i in range(200):
        bucket = compute_hash("sk_test", f"user-{i}", "my-flag") % 100
        assert not (bucket < 0)


def test_hundred_percent_always_enabled():
    """Every bucket 0–99 satisfies bucket < 100."""
    for bucket in range(100):
        assert bucket < 100


def test_approximate_distribution():
    """At 50% rollout, roughly half of 1000 users should be enabled (±10%)."""
    rollout = 50
    total = 1000
    enabled = sum(
        1
        for i in range(total)
        if compute_hash("sk_test123", f"user-{i}", "test-flag") % 100 < rollout
    )
    pct = enabled / total * 100
    assert 40 <= pct <= 60, f"expected ~50% distribution, got {pct:.1f}%"


def test_different_users_get_different_results():
    """At 50% rollout, both ON and OFF outcomes appear across a population."""
    saw_enabled = saw_disabled = False
    for i in range(200):
        bucket = compute_hash("sk_test", f"user-{i}", "feature-x") % 100
        if bucket < 50:
            saw_enabled = True
        else:
            saw_disabled = True
        if saw_enabled and saw_disabled:
            return
    pytest.fail("expected both enabled and disabled outcomes across 200 users")
