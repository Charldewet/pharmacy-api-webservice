from fastapi import Depends, HTTPException, status, Header
from typing import Optional
from .config import settings
from .db import get_conn
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


def _check_user_role(user_id: int, role: str) -> bool:
    """Check if a user has a specific role (admin or accounting)"""
    with get_conn() as conn, conn.cursor() as cur:
        if role == "admin":
            cur.execute("SELECT is_admin FROM pharma.users WHERE user_id = %s", (user_id,))
        elif role == "accounting":
            cur.execute("SELECT is_accounting FROM pharma.users WHERE user_id = %s", (user_id,))
        else:
            return False
        
        row = cur.fetchone()
        if not row:
            return False
        
        return row['is_admin'] if role == "admin" else row['is_accounting']


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
        
        # Verify user is admin by checking database
        if not _check_user_role(user_id, "admin"):
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


def require_accounting_or_api_key(
    authorization: Optional[str] = Header(None), 
    x_api_key: Optional[str] = Header(None)
) -> Optional[int]:
    """
    Accepts either API key (treated as accounting) or JWT token (must be accounting user).
    Returns user_id if JWT token is provided, None if API key is provided.
    Raises HTTPException if authentication is invalid or user is not accounting.
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
    
    # Check if it's an API key - API keys are trusted and allowed accounting access
    if token == settings.API_KEY:
        return None  # API key provided, treated as accounting
    
    # Otherwise, try to decode as JWT and verify accounting status
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        sub = payload.get("sub")
        if sub is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        user_id = int(sub)
        
        # Verify user has accounting role by checking database
        if not _check_user_role(user_id, "accounting"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accounting access restricted to authorized users only"
            )
        
        return user_id
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication. Provide either a valid JWT token or API key."
        )


def require_admin_or_accounting_or_api_key(
    authorization: Optional[str] = Header(None), 
    x_api_key: Optional[str] = Header(None)
) -> Optional[int]:
    """
    Accepts either API key (treated as authorized) or JWT token (must be admin or accounting user).
    Returns user_id if JWT token is provided, None if API key is provided.
    Raises HTTPException if authentication is invalid or user is not admin or accounting.
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
    
    # Check if it's an API key - API keys are trusted
    if token == settings.API_KEY:
        return None  # API key provided, treated as authorized
    
    # Otherwise, try to decode as JWT and verify admin or accounting status
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        sub = payload.get("sub")
        if sub is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        user_id = int(sub)
        
        # Verify user has admin or accounting role
        is_admin = _check_user_role(user_id, "admin")
        is_accounting = _check_user_role(user_id, "accounting")
        
        if not (is_admin or is_accounting):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access restricted to admin or accounting users only"
            )
        
        return user_id
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication. Provide either a valid JWT token or API key."
        )
