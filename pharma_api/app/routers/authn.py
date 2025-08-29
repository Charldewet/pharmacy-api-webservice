from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import hashlib
import jwt
from ..db import get_conn
from ..config import settings

router = APIRouter(prefix="/auth", tags=["auth"])  

class LoginRequest(BaseModel):
    username: str
    password: str

class UserInfo(BaseModel):
    user_id: int
    username: str
    email: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInfo


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT user_id, username, email, password_hash, is_active
            FROM pharma.users
            WHERE username = %s
            """,
            (req.username,),
        )
        row = cur.fetchone()
        if not row or not row["is_active"]:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        expected = row["password_hash"]
        if _sha256(req.password) != expected:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        now = datetime.now(timezone.utc)
        exp = now + timedelta(hours=12)
        payload = {"sub": str(row["user_id"]), "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

        return TokenResponse(
            access_token=token,
            expires_in=int((exp - now).total_seconds()),
            user=UserInfo(user_id=row["user_id"], username=row["username"], email=row["email"]),
        ) 