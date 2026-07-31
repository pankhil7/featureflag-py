from pydantic import BaseModel


class EvaluateResponse(BaseModel):
    enabled: bool
    reason: str
