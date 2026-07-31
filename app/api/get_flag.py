import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models.response.get_flag import GetFlagResponse
from app.middleware.ratelimiter import rate_limit_crud
from app.store import flag_store

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/flags/{key}",
    response_model=GetFlagResponse,
    summary="Get a flag by key",
    tags=["Flags"],
)
def get_flag(
    key: str,
    env: str = Query(..., description="Environment: dev, staging, prod"),
    api_key: str = Depends(rate_limit_crud),
):
    flag = flag_store.get_by_key(key, env)
    if flag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found")
    return GetFlagResponse(**flag)
