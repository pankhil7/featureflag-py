import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.create_flag import CreateFlagRequest, CreateFlagResponse
from app.middleware.ratelimiter import rate_limit_crud
from app.store import flag_store

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/flags",
    response_model=CreateFlagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a feature flag",
    tags=["Flags"],
)
def create_flag(
    req: CreateFlagRequest,
    api_key: str = Depends(rate_limit_crud),
):
    try:
        flag = flag_store.create(req)
    except Exception as exc:
        if "unique" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Flag already exists for this key+environment",
            )
        logger.error("flag create failed: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")
    logger.info("flag created key=%s env=%s", flag["key"], flag["environment"])
    return CreateFlagResponse(**flag)
