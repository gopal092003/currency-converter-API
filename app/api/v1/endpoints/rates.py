"""V1 exchange-rate endpoints."""

from datetime import date
from typing import Annotated

from app.api.dependencies import RatesServiceDependency
from app.modules.rates.schemas import (
    RateResponse,
    TimeSeriesRateResponse,
)
from fastapi import APIRouter, Query, status

router = APIRouter(tags=["V1 - Exchange Rates"])


def _normalize_symbols(symbols: str | list[str] | None) -> list[str] | None:
    """Accept repeated query params and comma-delimited values."""
    if symbols is None:
        return None
    if isinstance(symbols, str):
        items = symbols.split(",")
    else:
        items = [item for value in symbols for item in str(value).split(",")]
    return [item.strip() for item in items if item.strip()]


@router.get(
    "/latest",
    response_model=RateResponse,
    status_code=status.HTTP_200_OK,
    summary="Get latest exchange rates",
)
async def get_latest_rates(
    service: RatesServiceDependency,
    base: Annotated[
        str,
        Query(
            min_length=3,
            max_length=3,
            description="Base currency, such as EUR or USD.",
        ),
    ] = "EUR",
    symbols: Annotated[
        str | list[str] | None,
        Query(description="Optional target currency codes."),
    ] = None,
) -> RateResponse:
    """Return the latest rates for the requested base currency."""
    normalized_symbols = _normalize_symbols(symbols)
    data = await service.get_latest_rates(
        base=base,
        symbols=normalized_symbols,
    )
    return RateResponse(success=True, data=data)


@router.get(
    "/historical",
    response_model=RateResponse,
    status_code=status.HTTP_200_OK,
    summary="Get historical exchange rates",
)
async def get_historical_rates(
    service: RatesServiceDependency,
    rate_date: Annotated[
        date,
        Query(
            alias="date",
            description="Requested date in YYYY-MM-DD format.",
        ),
    ],
    base: Annotated[
        str,
        Query(min_length=3, max_length=3),
    ] = "EUR",
    symbols: Annotated[
        str | list[str] | None,
        Query(description="Optional target currency codes."),
    ] = None,
) -> RateResponse:
    """Return rates for the requested historical date."""
    normalized_symbols = _normalize_symbols(symbols)
    data = await service.get_historical_rates(
        rate_date=rate_date,
        base=base,
        symbols=normalized_symbols,
    )
    return RateResponse(success=True, data=data)


@router.get(
    "/time-series",
    response_model=TimeSeriesRateResponse,
    status_code=status.HTTP_200_OK,
    summary="Get exchange rates over a date range",
)
async def get_time_series(
    service: RatesServiceDependency,
    start_date: Annotated[
        date,
        Query(description="Inclusive start date in YYYY-MM-DD format."),
    ],
    end_date: Annotated[
        date,
        Query(description="Inclusive end date in YYYY-MM-DD format."),
    ],
    base: Annotated[
        str,
        Query(min_length=3, max_length=3),
    ] = "EUR",
    symbols: Annotated[
        str | list[str] | None,
        Query(description="Optional target currency codes."),
    ] = None,
) -> TimeSeriesRateResponse:
    """Return rates for an inclusive date range."""
    normalized_symbols = _normalize_symbols(symbols)
    data = await service.get_time_series(
        start_date=start_date,
        end_date=end_date,
        base=base,
        symbols=normalized_symbols,
    )
    return TimeSeriesRateResponse(success=True, data=data)
