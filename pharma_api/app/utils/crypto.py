from cryptography.fernet import Fernet, InvalidToken
from ..config import settings

_fernet = None
if settings.TOKEN_ENCRYPTION_KEY:
    try:
        _fernet = Fernet(settings.TOKEN_ENCRYPTION_KEY.encode("utf-8"))
    except Exception:
        _fernet = None


def encrypt_token(token: str) -> bytes:
    raw = token.encode("utf-8")
    if _fernet is None:
        return raw
    return _fernet.encrypt(raw)


def decrypt_token(token_enc: bytes) -> str:
    if _fernet is None:
        return token_enc.decode("utf-8")
    try:
        return _fernet.decrypt(token_enc).decode("utf-8")
    except InvalidToken:
        return token_enc.decode("utf-8") 