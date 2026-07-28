from typing import Optional
from pydantic import BaseModel, Field


class UpdateFlagRequest(BaseModel):
    enabled: Optional[bool] = None
    rollout_percentage: Optional[int] = Field(None, ge=0, le=100)
