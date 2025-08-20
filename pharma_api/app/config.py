from pydantic import Field
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    DATABASE_URL: str
    API_KEY: str

    CORS_ALLOW_ORIGINS: str = "*"
    CORS_ALLOW_CREDENTIALS: bool = False
    CORS_ALLOW_METHODS: str = "GET,OPTIONS"
    CORS_ALLOW_HEADERS: str = "Authorization,Content-Type"

    STATEMENT_TIMEOUT_MS: int = 10000

    class Config:
        env_file = ".env"
        extra = "ignore"

def parse_csv(s: str) -> List[str]:
    return [x.strip() for x in s.split(",") if x.strip()]

settings = Settings()
CORS_ORIGINS = parse_csv(settings.CORS_ALLOW_ORIGINS)
CORS_METHODS = parse_csv(settings.CORS_ALLOW_METHODS)
CORS_HEADERS = parse_csv(settings.CORS_ALLOW_HEADERS)
