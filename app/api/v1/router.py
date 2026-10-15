"""V1 API router."""

from app.api.v1.endpoints import convert, currencies, rates
from fastapi import APIRouter

router = APIRouter()

router.include_router(
    convert.router,
    prefix="/convert",
)

router.include_router(
    rates.router,
    prefix="/rates",
)

router.include_router(
    currencies.router,
    prefix="/currencies",
)
