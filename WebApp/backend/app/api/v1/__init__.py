from fastapi import APIRouter

from app.api.v1 import aeolian, mars, meda, tasks, ai

api_v1_router = APIRouter()
api_v1_router.include_router(mars.router)
api_v1_router.include_router(aeolian.router)
api_v1_router.include_router(meda.router)
api_v1_router.include_router(tasks.router)
api_v1_router.include_router(ai.router)

__all__ = ["api_v1_router"]

from app.api.v1 import science
api_v1_router.include_router(science.router)
