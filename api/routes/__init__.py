from fastapi import APIRouter

from .documents import router as documents_router
from .health import router as health_router
from .redactions import router as redactions_router
from .reports import router as reports_router
from .reviews import router as reviews_router
from .upload import router as upload_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(upload_router)
api_router.include_router(documents_router)
api_router.include_router(reviews_router)
api_router.include_router(redactions_router)
api_router.include_router(reports_router)