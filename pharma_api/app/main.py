from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import orjson
from .config import settings, CORS_ORIGINS, CORS_METHODS, CORS_HEADERS
from .routers import pharmacies, days, stock, agg, logbook, products
from .routers import usage
from .routers import users

class ORJSONResponse:
    media_type = "application/json"
    def __init__(self, content, status_code=200, headers=None):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}
    def __call__(self, scope, receive, send):
        # not used directly; FastAPI handles response class
        pass

app = FastAPI(
    title="Pharmacy Data API",
    description="API for pharmacy sales, inventory, and analytics data",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(pharmacies.router)
app.include_router(days.router)
app.include_router(stock.router)
app.include_router(agg.router)
app.include_router(logbook.router)
app.include_router(products.router)
app.include_router(usage.router)
app.include_router(users.router)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
