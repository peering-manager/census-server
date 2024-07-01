from fastapi import APIRouter

from .routes import health, records

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(records.router, prefix="/records", tags=["records"])
