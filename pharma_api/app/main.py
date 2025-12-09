from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import orjson
from .config import settings, CORS_ORIGINS, CORS_METHODS, CORS_HEADERS
from .routers import pharmacies, days, stock, agg, logbook, products, usage, users
from .routers import notifications
from .routers import broadcast
from .routers import authn
from .routers import admin
from .routers import debtors
from .routers import banking, ledger, bank_imports, accounts

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
    allow_origins=CORS_ORIGINS,  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=CORS_METHODS,
    allow_headers=CORS_HEADERS,
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
app.include_router(notifications.router)
app.include_router(broadcast.router)
app.include_router(authn.router)
app.include_router(admin.router)
app.include_router(debtors.router)
app.include_router(banking.router)
app.include_router(ledger.router)
app.include_router(bank_imports.router)
app.include_router(accounts.router)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
