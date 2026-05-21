from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.routers.analytics import router as analytics_router
from app.api.routers.auth import router as auth_router
from app.api.routers.customers import router as customers_router
from app.api.routers.deliveries import router as deliveries_router
from app.api.routers.orders import router as orders_router
from app.api.routers.payments import router as payments_router
from app.api.routers.products import router as products_router
from app.api.routers.reports import router as reports_router
from app.api.routers.tasks import router as tasks_router
from app.core.config import settings

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"])

app = FastAPI(title="Pixel Pivot InsightFlow API", version="0.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(customers_router)
app.include_router(products_router)
app.include_router(orders_router)
app.include_router(payments_router)
app.include_router(deliveries_router)
app.include_router(analytics_router)
app.include_router(reports_router)
app.include_router(tasks_router)


@app.get("/health")
@limiter.limit("60/minute")
async def health(_: Request):
    return {"status": "ok"}
