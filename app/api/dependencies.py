"""Shared FastAPI dependencies."""

from typing import Annotated

from app.modules.currency.service import CurrencyConversionService
from app.modules.providers.base import ExchangeRateProvider
from app.modules.rates.service import RatesService
from fastapi import Depends, Request


def get_provider(request: Request) -> ExchangeRateProvider:
    """Return the application's shared exchange-rate provider."""
    return request.app.state.provider


def get_currency_service(
    request: Request,
) -> CurrencyConversionService:
    """Return the currency conversion service."""
    return request.app.state.currency_service


def get_rates_service(request: Request) -> RatesService:
    """Return the exchange-rates service."""
    return request.app.state.rates_service


ProviderDependency = Annotated[
    ExchangeRateProvider,
    Depends(get_provider),
]

CurrencyServiceDependency = Annotated[
    CurrencyConversionService,
    Depends(get_currency_service),
]

RatesServiceDependency = Annotated[
    RatesService,
    Depends(get_rates_service),
]
