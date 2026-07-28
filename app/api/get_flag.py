import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models import APIKey, FlagResponse
from app.middleware.ratelimiter import rate_limit_crud
from app.store import flag_store

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/flags/{key}",
    response_model=FlagResponse,
    summary="Get a flag by key",
    tags=["Flags"],
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
