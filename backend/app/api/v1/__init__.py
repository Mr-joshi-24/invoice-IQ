from fastapi import APIRouter
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.documents import router as documents_router
from backend.app.api.v1.review import router as review_router
from backend.app.api.v1.analytics import router as analytics_router
from backend.app.api.v1.settings import router as settings_router

api_v1_router = APIRouter()

# Include Feature Routers
api_v1_router.include_router(auth_router)
api_v1_router.include_router(documents_router)
api_v1_router.include_router(review_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(settings_router)

__all__ = ["api_v1_router"]
