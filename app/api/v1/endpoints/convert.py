"""V1 currency conversion endpoint."""

from app.api.dependencies import CurrencyServiceDependency
from app.modules.currency.schemas import (
    ConversionRequest,
    ConversionResponse,
)
from fastapi import APIRouter, status

router = APIRouter(
    tags=["V1 - Currency Conversion"],
)


@router.post(
    "",
    response_model=ConversionResponse,
    status_code=status.HTTP_200_OK,
    summary="Convert between currencies",
)
async def convert_currency(
    payload: ConversionRequest,
    service: CurrencyServiceDependency,
) -> ConversionResponse:
    """Convert an amount using the latest available exchange rate."""
    result = await service.convert(payload)

    return ConversionResponse(
        success=True,
        data=result,
    )
