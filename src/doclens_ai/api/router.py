from fastapi import APIRouter

from doclens_ai.api.routes.documents import router as documents_router
from doclens_ai.api.routes.health import router as health_router
from doclens_ai.api.routes.jobs import router as jobs_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(documents_router)
api_router.include_router(jobs_router)
