"""
FNV-1a 32-bit consistent hash used for rollout percentage bucketing.

Why FNV-1a:
- Deterministic — same inputs always produce the same bucket
- Fast — XOR + multiply per byte, no crypto overhead
- Good distribution — users spread evenly across 0–99 buckets
- No per-user DB record needed — pure computation
"""

FNV_OFFSET_BASIS: int = 0x811C9DC5
FNV_PRIME: int = 0x01000193
UINT32_MOD: int = 2**32


def compute_hash(*parts: str) -> int:
    """
    Compute FNV-1a 32-bit hash over the concatenation of all parts.

    Including api_key + user_id + flag_key in the hash ensures:
    - Different tenants (api keys) get independent rollout results
    - Different users get different buckets for the same flag
    - Different flags give the same user independent results
    """
    h = FNV_OFFSET_BASIS
    for part in parts:
        for byte in part.encode("utf-8"):
            h ^= byte                          # XOR first — "1a" variant
            h = (h * FNV_PRIME) % UINT32_MOD  # then multiply
    return h
