import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models.response.evaluate import EvaluateResponse
from app.middleware.ratelimiter import rate_limit_eval
from app.store import flag_store
from app.hash import compute_hash

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/evaluate/{key}",
    response_model=EvaluateResponse,
    summary="Evaluate a feature flag for a caller",
    tags=["Evaluate"],
    description="""
Returns whether the flag is enabled for the given request.

**Rollout logic:**
1. Flag not found → 404
2. `enabled=false` → `{"enabled": false}`
3. `rollout_percentage=100` → `{"enabled": true}`
4. Partial rollout — consistent hash of `(api_key + user_id + flag_key) % 100 < rollout_percentage`

The same caller always gets the same result — no per-user DB records needed.
    """,
)
def evaluate_flag(
    key: str,
    env: str = Query(..., description="Environment to evaluate against"),
    user_id: Optional[str] = Query(None, description="Caller identifier for consistent bucketing"),
    api_key: str = Depends(rate_limit_eval),
):
    flag = flag_store.get_by_key(key, env)
    if flag is None:
        logger.warning("evaluate: flag not found key=%s env=%s", key, env)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found")

    if not flag["enabled"]:
        logger.debug("evaluate: flag disabled key=%s env=%s", key, env)
        return EvaluateResponse(enabled=False)

    if flag["rollout_percentage"] == 100:
        logger.debug("evaluate: full rollout key=%s env=%s", key, env)
        return EvaluateResponse(enabled=True)

    # Partial rollout — FNV-1a consistent hash.
    parts = [api_key, user_id, key] if user_id else [api_key, key]
    bucket = compute_hash(*parts) % 100
    enabled = bucket < flag["rollout_percentage"]

    logger.debug(
        "evaluate: partial rollout key=%s env=%s rollout=%d bucket=%d enabled=%s",
        key, env, flag["rollout_percentage"], bucket, enabled,
    )
    return EvaluateResponse(enabled=enabled)
