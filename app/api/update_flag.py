import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models.request.update_flag import UpdateFlagRequest
from app.models.response.update_flag import UpdateFlagResponse
from app.middleware.ratelimiter import rate_limit_crud
from app.store import flag_store

logger = logging.getLogger(__name__)

router = APIRouter()


@router.put(
    "/flags/{key}",
    response_model=UpdateFlagResponse,
    summary="Update a flag",
    tags=["Flags"],
)
def update_flag(
    key: str,
    req: UpdateFlagRequest,
    env: str = Query(..., description="Environment is required for update"),
    api_key: str = Depends(rate_limit_crud),
):
    flag = flag_store.update(key, env, req)
    if flag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found")
    logger.info("flag updated key=%s env=%s", key, env)
    return UpdateFlagResponse(**flag)
