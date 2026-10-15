"""Integration tests for the Frankfurter provider."""

import os
from datetime import date
from decimal import Decimal

import httpx
import pytest
import respx
from app.modules.providers.exceptions import (
    ProviderRequestTimeoutError,
    ProviderResponseError,
)
from app.modules.providers.frankfurter import FrankfurterProvider

BASE_URL = "https://api.frankfurter.app"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_latest_rates_with_mocked_provider():
    """Parse a representative latest-rates response."""
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/latest").mock(
            return_value=httpx.Response(
                200,
                json={
                    "amount": 1.0,
                    "base": "EUR",
                    "date": "2026-10-13",
                    "rates": {"USD": 1.17, "INR": 103.5},
                },
            )
        )

        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            provider = FrankfurterProvider(client=client)
            result = await provider.get_latest_rates(
                base="EUR",
                symbols=["USD", "INR"],
            )

    assert result["base"] == "EUR"
    assert result["date"] == "2026-10-13"
    assert Decimal(str(result["rates"]["USD"])) == Decimal("1.17")
    assert Decimal(str(result["rates"]["INR"])) == Decimal("103.5")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_historical_rates_with_mocked_provider():
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/2026-10-01").mock(
            return_value=httpx.Response(
                200,
                json={
                    "amount": 1.0,
                    "base": "EUR",
                    "date": "2026-10-01",
                    "rates": {"USD": 1.16},
                },
            )
        )

        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            provider = FrankfurterProvider(client=client)
            result = await provider.get_historical_rates(
                rate_date=date(2026, 10, 1),
                base="EUR",
                symbols=["USD"],
            )

    assert result["date"] == "2026-10-01"
    assert Decimal(str(result["rates"]["USD"])) == Decimal("1.16")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_time_series_with_mocked_provider():
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/2026-10-01..2026-10-03").mock(
            return_value=httpx.Response(
                200,
                json={
                    "amount": 1.0,
                    "base": "EUR",
                    "start_date": "2026-10-01",
                    "end_date": "2026-10-03",
                    "rates": {
                        "2026-10-01": {"USD": 1.16},
                        "2026-10-02": {"USD": 1.165},
                        "2026-10-03": {"USD": 1.17},
                    },
                },
            )
        )

        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            provider = FrankfurterProvider(client=client)
            result = await provider.get_time_series(
                start_date=date(2026, 10, 1),
                end_date=date(2026, 10, 3),
                base="EUR",
                symbols=["USD"],
            )

    assert result["base"] == "EUR"
    assert "2026-10-02" in result["rates"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_invalid_provider_json_is_rejected():
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/latest").mock(
            return_value=httpx.Response(
                200,
                content=b"not-json",
                headers={"Content-Type": "application/json"},
            )
        )

        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            provider = FrankfurterProvider(client=client)

            with pytest.raises(ProviderResponseError):
                await provider.get_latest_rates(base="EUR")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_provider_timeout_is_mapped():
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/latest").mock(side_effect=httpx.ReadTimeout("simulated timeout"))

        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            provider = FrankfurterProvider(client=client)

            with pytest.raises(ProviderRequestTimeoutError):
                await provider.get_latest_rates(base="EUR")


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
async def test_live_frankfurter_latest_rates():
    """Optional smoke test against the actual upstream provider."""
    if os.getenv("RUN_NETWORK_TESTS") != "1":
        pytest.skip("Set RUN_NETWORK_TESTS=1 to enable network tests.")

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(10.0),
    ) as client:
        provider = FrankfurterProvider(client=client)
        result = await provider.get_latest_rates(
            base="EUR",
            symbols=["USD"],
        )

    assert result["base"] == "EUR"
    assert date.fromisoformat(result["date"]) <= date.today()
    assert Decimal(str(result["rates"]["USD"])) > 0
