from fastapi import APIRouter

from app.api.v1 import mars, science

api_v1_router = APIRouter()
api_v1_router.include_router(mars.router)
api_v1_router.include_router(science.router)

__all__ = ["api_v1_router"]

