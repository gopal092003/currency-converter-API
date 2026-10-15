"""Currency conversion API routes."""

from app.api.dependencies import CurrencyServiceDependency
from app.modules.currency.schemas import (
    ConversionRequest,
    ConversionResponse,
)
from fastapi import APIRouter, status

router = APIRouter(
    prefix="/currency",
    tags=["Currency Conversion"],
)


@router.post(
    "/convert",
    response_model=ConversionResponse,
    status_code=status.HTTP_200_OK,
    summary="Convert an amount between currencies",
    description=(
        "Convert an amount from one supported currency to another "
        "using the latest available exchange rate."
    ),
)
async def convert_currency(
    payload: ConversionRequest,
    service: CurrencyServiceDependency,
) -> ConversionResponse:
    """Convert an amount using the currency conversion service."""
    result = await service.convert(payload)

    return ConversionResponse(
        success=True,
        data=result,
    )
