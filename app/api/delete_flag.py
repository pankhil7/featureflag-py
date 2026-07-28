import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models import APIKey
from app.middleware.ratelimiter import rate_limit_crud
from app.store import flag_store

logger = logging.getLogger(__name__)

router = APIRouter()


@router.delete(
    "/flags/{key}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a flag",
    tags=["Flags"],
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
