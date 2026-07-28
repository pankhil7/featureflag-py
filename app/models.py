from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# API Key
# ---------------------------------------------------------------------------

class APIKey(BaseModel):
    id: str
    key: str
    name: str
    capacity: int
    refill_rate: float
    created_at: datetime


# ---------------------------------------------------------------------------
# Flag schemas
# ---------------------------------------------------------------------------

class FlagBase(BaseModel):
    key: str = Field(..., description="Unique flag identifier, e.g. 'new-checkout-flow'")
    enabled: bool = Field(..., description="Whether the flag is active")
    environment: str = Field(..., description="Target environment: dev, staging, prod")
    rollout_percentage: int = Field(100, ge=0, le=100, description="Percentage of traffic to enable (0–100)")


class CreateFlagRequest(FlagBase):
    pass


class UpdateFlagRequest(BaseModel):
    enabled: Optional[bool] = None
    rollout_percentage: Optional[int] = Field(None, ge=0, le=100)


class FlagResponse(FlagBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Evaluate
# ---------------------------------------------------------------------------

class EvaluateResponse(BaseModel):
    enabled: bool
