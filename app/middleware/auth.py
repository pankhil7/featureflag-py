from fastapi import Security, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.store import apikey_store
from app.models import APIKey

bearer_scheme = HTTPBearer()


def get_api_key(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> APIKey:
    """
    FastAPI dependency — validates the Bearer token against the database.
    Raises 401 if the token is missing or invalid.
    """
    token = credentials.credentials
    api_key = apikey_store.get_by_key(token)
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return api_key
