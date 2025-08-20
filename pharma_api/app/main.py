from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import orjson
from .config import settings, CORS_ORIGINS, CORS_METHODS, CORS_HEADERS
from .routers import pharmacies, days, stock, agg, logbook, products

class ORJSONResponse:
    media_type = "application/json"
    def __init__(self, content, status_code=200, headers=None):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}
    def __call__(self, scope, receive, send):
        # not used directly; FastAPI handles response class
        pass

app = FastAPI(title="Pharma API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS or ["*"],
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=CORS_METHODS or ["GET", "OPTIONS"],
    allow_headers=CORS_HEADERS or ["Authorization","Content-Type"],
)

@app.get("/health")
def health():
    return {"ok": True}

# mount routers
app.include_router(pharmacies.router)
app.include_router(days.router)
app.include_router(stock.router)
app.include_router(agg.router)
app.include_router(logbook.router)
app.include_router(products.router)
