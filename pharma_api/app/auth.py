from fastapi import Depends, HTTPException, status, Header
from typing import Optional
from .config import settings

def require_api_key(authorization: Optional[str] = Header(None), x_api_key: Optional[str] = Header(None)):
    token = None
    # Prefer Bearer
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    elif x_api_key:
        token = x_api_key.strip()

    if not token or token != settings.API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")
    return True
