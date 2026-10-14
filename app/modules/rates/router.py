
"""Exchange-rate retrieval API routes."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import RatesServiceDependency
from app.modules.rates.schemas import (
    RateResponse,
    TimeSeriesRateResponse,
)

router = APIRouter(
    prefix="/rates",
    tags=["Exchange Rates"],
)


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
            description="Base currency code, such as EUR or USD.",
        ),
    ] = "EUR",
    symbols: Annotated[
        list[str] | None,
        Query(
            description=(
                "Optional target currency codes. Repeat the parameter "
                "to request multiple currencies."
            ),
        ),
    ] = None,
) -> RateResponse:
    """Retrieve the latest rates for the requested base currency."""
    data = await service.get_latest_rates(
        base=base,
        symbols=symbols,
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
        list[str] | None,
        Query(
            description=(
                "Optional target currency codes. Repeat the parameter "
                "to request multiple currencies."
            ),
        ),
    ] = None,
) -> RateResponse:
    """Retrieve rates for a specific historical date."""
    data = await service.get_historical_rates(
        rate_date=rate_date,
        base=base,
        symbols=symbols,
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
        Query(description="Start date in YYYY-MM-DD format."),
    ],
    end_date: Annotated[
        date,
        Query(description="End date in YYYY-MM-DD format."),
    ],
    base: Annotated[
        str,
        Query(min_length=3, max_length=3),
    ] = "EUR",
    symbols: Annotated[
        list[str] | None,
        Query(
            description=(
                "Optional target currency codes. Repeat the parameter "
                "to request multiple currencies."
            ),
        ),
    ] = None,
) -> TimeSeriesRateResponse:
    """Retrieve exchange rates over an inclusive date range."""
    data = await service.get_time_series(
        start_date=start_date,
        end_date=end_date,
        base=base,
        symbols=symbols,
    )

    return TimeSeriesRateResponse(success=True, data=data)
