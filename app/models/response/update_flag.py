from datetime import datetime
from pydantic import BaseModel


class UpdateFlagResponse(BaseModel):
    id: str
    key: str
    enabled: bool
    environment: str
    rollout_percentage: int
    created_at: datetime
    updated_at: datetime
