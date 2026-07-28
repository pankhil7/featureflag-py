import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.models.response.get_flag import GetFlagResponse
from app.middleware.ratelimiter import rate_limit_crud
from app.store import flag_store

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/flags",
    response_model=list[GetFlagResponse],
    summary="List feature flags",
    tags=["Flags"],
)
def list_flags(
    env: Optional[str] = Query(None, description="Filter by environment"),
    api_key: str = Depends(rate_limit_crud),
):
    flags = flag_store.list_flags(env)
    logger.debug("flag list env=%s count=%d", env, len(flags))
    return [GetFlagResponse(**f) for f in flags]
