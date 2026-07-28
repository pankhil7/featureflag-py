from fastapi import Security, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings

bearer_scheme = HTTPBearer()


def get_api_key(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> str:
    """
    FastAPI dependency — validates the Bearer token against API_KEY env var.
    Returns the key string on success, raises 401 on failure.
    """
    if credentials.credentials != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return credentials.credentials
