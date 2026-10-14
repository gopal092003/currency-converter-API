
"""Persistence interface for exchange-rate datasets."""

from abc import ABC, abstractmethod
from datetime import date

from app.modules.rates.schemas import RateData, TimeSeriesRateData


class RateRepository(ABC):
    """Abstract interface for storing and retrieving rate data."""

    @abstractmethod
    async def get_latest(
        self,
        base: str,
        symbols: list[str] | None = None,
    ) -> RateData | None:
        """Return the latest stored rates for a base currency."""
        raise NotImplementedError

    @abstractmethod
    async def save_latest(
        self,
        data: RateData,
    ) -> None:
        """Store the latest rate dataset."""
        raise NotImplementedError

    @abstractmethod
    async def get_historical(
        self,
        rate_date: date,
        base: str,
        symbols: list[str] | None = None,
    ) -> RateData | None:
        """Return stored rates for a specific effective date."""
        raise NotImplementedError

    @abstractmethod
    async def save_historical(
        self,
        data: RateData,
    ) -> None:
        """Store a historical rate dataset."""
        raise NotImplementedError

    @abstractmethod
    async def get_time_series(
        self,
        start_date: date,
        end_date: date,
        base: str,
        symbols: list[str] | None = None,
    ) -> TimeSeriesRateData | None:
        """Return a stored time series if the requested range is available."""
        raise NotImplementedError

    @abstractmethod
    async def save_time_series(
        self,
        data: TimeSeriesRateData,
    ) -> None:
        """Store a time-series dataset."""
        raise NotImplementedError
