"""Abstract interface for exchange-rate providers."""

from abc import ABC, abstractmethod
from datetime import date
from typing import Any


class ExchangeRateProvider(ABC):
    """Contract implemented by every exchange-rate provider."""

    name: str

    @abstractmethod
    async def get_latest_rates(
        self,
        base: str = "EUR",
        symbols: list[str] | None = None,
    ) -> dict[str, Any]:
        """Return the latest available rates for a base currency."""
        raise NotImplementedError

    @abstractmethod
    async def get_historical_rates(
        self,
        rate_date: date,
        base: str = "EUR",
        symbols: list[str] | None = None,
    ) -> dict[str, Any]:
        """Return rates for a specific historical date."""
        raise NotImplementedError

    @abstractmethod
    async def get_time_series(
        self,
        start_date: date,
        end_date: date,
        base: str = "EUR",
        symbols: list[str] | None = None,
    ) -> dict[str, Any]:
        """Return rates over an inclusive date range."""
        raise NotImplementedError
