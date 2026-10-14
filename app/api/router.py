
"""Root API router with versioned route prefixes."""

from fastapi import APIRouter

from app.api.v1.router import router as v1_router
from app.core.config import settings

api_router = APIRouter()

api_router.include_router(
    v1_router,
    prefix=settings.api_v1_prefix,
)

# Add V2 when app/api/v2/router.py is implemented:
#
# from app.api.v2.router import router as v2_router
# api_router.include_router(v2_router, prefix="/v2")
