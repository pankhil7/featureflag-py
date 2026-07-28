"""
Flag CRUD and evaluation endpoints.

Middleware chain per route:
  CRUD      → Auth (get_api_key) → RateLimit (crud, 10×)
  /evaluate → Auth (get_api_key) → RateLimit (eval, 1×)
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models import APIKey, CreateFlagRequest, UpdateFlagRequest, FlagResponse, EvaluateResponse
from app.middleware.ratelimiter import rate_limit_crud, rate_limit_eval
from app.store import flag_store
from app.hash import compute_hash

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.post(
    "/flags",
    response_model=FlagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a feature flag",
)
def create_flag(
    req: CreateFlagRequest,
    api_key: APIKey = Depends(rate_limit_crud),
):
    try:
        flag = flag_store.create(req)
    except Exception as exc:
        # Unique constraint violation — key+env already exists.
        if "unique" in str(exc).lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Flag already exists for this key+environment")
        logger.error("flag create failed: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")
    logger.info("flag created key=%s env=%s", flag.key, flag.environment)
    return flag


@router.get(
    "/flags",
    response_model=list[FlagResponse],
    summary="List feature flags",
)
def list_flags(
    env: Optional[str] = Query(None, description="Filter by environment"),
    api_key: APIKey = Depends(rate_limit_crud),
):
    flags = flag_store.list_flags(env)
    logger.debug("flag list env=%s count=%d", env, len(flags))
    return flags


@router.get(
    "/flags/{key}",
    response_model=FlagResponse,
    summary="Get a flag by key",
)
def get_flag(
    key: str,
    env: Optional[str] = Query(None, description="Filter by environment"),
    api_key: APIKey = Depends(rate_limit_crud),
):
    flag = flag_store.get_by_key(key, env)
    if flag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found")
    return flag


@router.put(
    "/flags/{key}",
    response_model=FlagResponse,
    summary="Update a flag",
)
def update_flag(
    key: str,
    req: UpdateFlagRequest,
    env: str = Query(..., description="Environment is required for update"),
    api_key: APIKey = Depends(rate_limit_crud),
):
    flag = flag_store.update(key, env, req)
    if flag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found")
    logger.info("flag updated key=%s env=%s", key, env)
    return flag


@router.delete(
    "/flags/{key}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a flag",
)
def delete_flag(
    key: str,
    env: str = Query(..., description="Environment is required for delete"),
    api_key: APIKey = Depends(rate_limit_crud),
):
    deleted = flag_store.delete(key, env)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found")
    logger.info("flag deleted key=%s env=%s", key, env)


# ---------------------------------------------------------------------------
# Evaluate
# ---------------------------------------------------------------------------

@router.get(
    "/evaluate/{key}",
    response_model=EvaluateResponse,
    summary="Evaluate a feature flag for a caller",
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
    api_key: APIKey = Depends(rate_limit_eval),
):
    flag = flag_store.get_by_key(key, env)
    if flag is None:
        logger.warning("evaluate: flag not found key=%s env=%s", key, env)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found")

    if not flag.enabled:
        logger.debug("evaluate: flag disabled key=%s env=%s", key, env)
        return EvaluateResponse(enabled=False)

    if flag.rollout_percentage == 100:
        logger.debug("evaluate: full rollout key=%s env=%s", key, env)
        return EvaluateResponse(enabled=True)

    # Partial rollout — FNV-1a consistent hash.
    parts = [api_key.key, user_id, key] if user_id else [api_key.key, key]
    bucket = compute_hash(*parts) % 100
    enabled = bucket < flag.rollout_percentage

    logger.debug(
        "evaluate: partial rollout key=%s env=%s rollout=%d bucket=%d enabled=%s",
        key, env, flag.rollout_percentage, bucket, enabled,
    )
    return EvaluateResponse(enabled=enabled)
