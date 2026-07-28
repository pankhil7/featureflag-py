from datetime import datetime
from pydantic import BaseModel, Field


class CreateFlagRequest(BaseModel):
    key: str = Field(..., description="Unique flag identifier, e.g. 'new-checkout-flow'")
    enabled: bool = Field(..., description="Whether the flag is active")
    environment: str = Field(..., description="Target environment: dev, staging, prod")
    rollout_percentage: int = Field(100, ge=0, le=100, description="Percentage of traffic to enable (0–100)")


class CreateFlagResponse(BaseModel):
    id: str
    key: str
    enabled: bool
    environment: str
    rollout_percentage: int
    created_at: datetime
    updated_at: datetime

