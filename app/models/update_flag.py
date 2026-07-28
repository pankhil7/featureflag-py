from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UpdateFlagRequest(BaseModel):
    enabled: Optional[bool] = None
    rollout_percentage: Optional[int] = Field(None, ge=0, le=100)


class UpdateFlagResponse(BaseModel):
    id: str
    key: str
    enabled: bool
    environment: str
    rollout_percentage: int
    created_at: datetime
    updated_at: datetime

