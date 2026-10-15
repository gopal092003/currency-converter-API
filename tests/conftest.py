"""Shared fixtures for the test suite."""

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from app.api.dependencies import (
    get_currency_service,
    get_rates_service,
)
from app.main import create_app
from app.modules.currency.service import CurrencyConversionService
from app.modules.providers.base import ExchangeRateProvider
from app.modules.rates.service import RatesService
from fastapi.testclient import TestClient

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_json_fixture(filename: str) -> dict[str, Any]:
    """Load a JSON fixture relative to the tests directory.

    Some historical project snapshots used underscore-separated filenames while
    the checked-in fixtures are named with hyphens. Accept both forms so the
    test suite remains stable across naming conventions.
    """
    candidates = [
        FIXTURES_DIR / filename,
        FIXTURES_DIR / filename.replace("_", "-"),
        FIXTURES_DIR / filename.replace("-", "_"),
    ]

    for path in candidates:
        if path.exists():
            with path.open(encoding="utf-8") as file:
                return json.load(file)

    raise FileNotFoundError(f"Fixture not found: {filename}")


class FakeExchangeRateProvider(ExchangeRateProvider):
    """Deterministic provider for tests; never accesses the network."""

    name = "fake"

    def __init__(
        self,
        provider_responses: dict[str, Any],
        known_rates: dict[str, Any],
    ) -> None:
        self.provider_responses = provider_responses
        self.known_rates = known_rates

    def _rates_for_base(
        self,
        base: str,
        symbols: list[str] | None,
    ) -> dict[str, Any]:
        base = base.upper()
        all_rates = self.known_rates["rates_by_base"].get(base)

        if all_rates is None:
            raise ValueError(f"No test rates configured for {base}.")

        if symbols is None:
            return dict(all_rates)

        missing = [code for code in symbols if code not in all_rates]
        if missing:
            raise ValueError(f"No test rates for: {', '.join(missing)}")

        return {code: all_rates[code] for code in symbols}

    async def get_latest_rates(
        self,
        base: str = "EUR",
        symbols: list[str] | None = None,
    ) -> dict[str, Any]:
        template = self.provider_responses["latest"]
        return {
            **template,
            "base": base.upper(),
            "rates": self._rates_for_base(base, symbols),
        }

    async def get_historical_rates(
        self,
        rate_date: date,
        base: str = "EUR",
        symbols: list[str] | None = None,
    ) -> dict[str, Any]:
        template = self.provider_responses["historical"]
        return {
            **template,
            "base": base.upper(),
            "date": rate_date.isoformat(),
            "rates": self._rates_for_base(base, symbols),
        }

    async def get_time_series(
        self,
        start_date: date,
        end_date: date,
        base: str = "EUR",
        symbols: list[str] | None = None,
    ) -> dict[str, Any]:
        template = self.provider_responses["time_series"]
        daily_rates = self._rates_for_base(base, symbols)

        # A deterministic test series: one observation for each calendar
        # day in the requested interval. Real providers may omit weekends
        # and holidays.
        rates: dict[str, Any] = {}
        current = start_date
        while current <= end_date:
            rates[current.isoformat()] = daily_rates
            current = date.fromordinal(current.toordinal() + 1)

        return {
            **template,
            "base": base.upper(),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "rates": rates,
        }


@pytest.fixture
def provider_responses() -> dict[str, Any]:
    """Example provider payloads."""
    return load_json_fixture("provider_responses.json")


@pytest.fixture
def known_rates() -> dict[str, Any]:
    """Deterministic rates used by tests."""
    return load_json_fixture("rates.json")


@pytest.fixture
def fake_provider(
    provider_responses: dict[str, Any],
    known_rates: dict[str, Any],
) -> FakeExchangeRateProvider:
    """Create a network-free exchange-rate provider."""
    return FakeExchangeRateProvider(provider_responses, known_rates)


@pytest.fixture
def currency_service(
    fake_provider: FakeExchangeRateProvider,
) -> CurrencyConversionService:
    """Provide the conversion service with deterministic rates."""
    return CurrencyConversionService(fake_provider)


@pytest.fixture
def rates_service(
    fake_provider: FakeExchangeRateProvider,
) -> RatesService:
    """Provide the rate retrieval service with deterministic rates."""
    return RatesService(fake_provider)


@pytest.fixture
def app(
    currency_service: CurrencyConversionService,
    rates_service: RatesService,
):
    """Create an application with service dependencies overridden."""
    application = create_app()

    application.dependency_overrides[get_currency_service] = lambda: currency_service
    application.dependency_overrides[get_rates_service] = lambda: rates_service

    yield application

    application.dependency_overrides.clear()


@pytest.fixture
def client(app):
    """Provide a synchronous FastAPI test client."""
    with TestClient(app) as test_client:
        yield test_client
