
"""V1 supported-currency endpoint."""

from fastapi import APIRouter, status

from app.api.dependencies import RatesServiceDependency
from app.modules.currency.schemas import (
    CurrencyMetadata,
    SupportedCurrenciesResponse,
)

router = APIRouter(tags=["V1 - Currencies"])


@router.get(
    "",
    response_model=SupportedCurrenciesResponse,
    status_code=status.HTTP_200_OK,
    summary="List supported currencies",
    description=(
        "List currency codes available from the configured exchange-rate "
        "provider's latest rates."
    ),
)
async def get_supported_currencies(
    service: RatesServiceDependency,
) -> SupportedCurrenciesResponse:
    """Return currencies available through the current rate provider."""
    rate_data = await service.get_latest_rates(base="EUR")

    # The base currency is valid even though providers commonly omit it
    # from the returned rates mapping.
    codes = sorted({rate_data.base, *rate_data.rates.keys()})

    currencies = [
        CurrencyMetadata(code=code)
        for code in codes
    ]

    return SupportedCurrenciesResponse(
        success=True,
        currencies=currencies,
        count=len(currencies),
    )
