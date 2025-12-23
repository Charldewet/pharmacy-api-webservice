from fastapi import Depends, HTTPException, status, Header
from typing import Optional
from .config import settings
import jwt
from jwt import PyJWTError


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


def get_current_user_id(authorization: Optional[str] = Header(None)) -> int:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Missing Authorization header. Please include 'Authorization: Bearer <token>' header in your request."
        )
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        sub = payload.get("sub")
        if sub is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        return int(sub)
    except PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_user_id_or_api_key(
    authorization: Optional[str] = Header(None), 
    x_api_key: Optional[str] = Header(None)
) -> Optional[int]:
    """
    Accepts either API key or JWT token.
    Returns user_id if JWT token is provided, None if API key is provided.
    Raises HTTPException if neither is valid.
    """
    # Check for API key first
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    elif x_api_key:
        token = x_api_key.strip()
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication. Provide either 'Authorization: Bearer <token>' or 'X-API-Key: <key>' header."
        )
    
    # Check if it's an API key
    if token == settings.API_KEY:
        return None  # API key provided, no user_id needed
    
    # Otherwise, try to decode as JWT
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        sub = payload.get("sub")
        if sub is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        return int(sub)
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication. Provide either a valid JWT token or API key."
        )


def require_admin_or_api_key(
    authorization: Optional[str] = Header(None), 
    x_api_key: Optional[str] = Header(None)
) -> Optional[int]:
    """
    Accepts either API key (treated as admin) or JWT token (must be admin user).
    Returns user_id if JWT token is provided, None if API key is provided.
    Raises HTTPException if authentication is invalid or user is not admin.
    """
    # Check for API key first
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    elif x_api_key:
        token = x_api_key.strip()
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication. Provide either 'Authorization: Bearer <token>' or 'X-API-Key: <key>' header."
        )
    
    # Check if it's an API key - API keys are trusted and allowed admin access
    if token == settings.API_KEY:
        return None  # API key provided, treated as admin
    
    # Otherwise, try to decode as JWT and verify admin status
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        sub = payload.get("sub")
        if sub is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        user_id = int(sub)
        
        # Verify user is admin (user_id 2 or 9)
        ADMIN_USER_IDS = {2, 9}
        if user_id not in ADMIN_USER_IDS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access restricted to authorized users only"
            )
        
        return user_id
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication. Provide either a valid JWT token or API key."
        )
