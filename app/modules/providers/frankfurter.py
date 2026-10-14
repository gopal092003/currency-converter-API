"""Frankfurter exchange-rate provider."""

import asyncio
import math
from datetime import date
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx

from app.core.config import settings
from app.modules.providers.base import ExchangeRateProvider
from app.modules.providers.exceptions import (
    ProviderConnectionError,
    ProviderHTTPError,
    ProviderRequestTimeoutError,
    ProviderResponseError,
)


class FrankfurterProvider(ExchangeRateProvider):
    """Client for the Frankfurter exchange-rate API."""

    name = "frankfurter"

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._client = client
        self._owns_client = client is None

        self._base_url = self._resolve_base_url(settings.exchange_api)
        self._timeout = settings.exchange_timeout_seconds
        self._max_retries = settings.exchange_max_retries

    @staticmethod
    def _resolve_base_url(configured_url: str) -> str:
        """Derive the API base URL from a configured endpoint."""
        parsed = urlsplit(configured_url)
        path = parsed.path.rstrip("/")

        if path.endswith("/latest"):
            path = path[:-len("/latest")]

        return urlunsplit(
            (parsed.scheme, parsed.netloc, path.rstrip("/"), "", "")
        )

    async def _request_json(
        self,
        endpoint: str,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Request JSON with bounded retries for transient failures."""
        url = f"{self._base_url}/{endpoint.lstrip('/')}"
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                if self._client is None:
                    async with httpx.AsyncClient(
                        timeout=self._timeout
                    ) as client:
                        response = await client.get(url, params=params)
                else:
                    response = await self._client.get(url, params=params)

                if response.status_code == 429 or response.status_code >= 500:
                    raise ProviderHTTPError(response.status_code)

                if not response.is_success:
                    raise ProviderHTTPError(response.status_code)

                try:
                    payload = response.json()
                except ValueError as exc:
                    raise ProviderResponseError() from exc

                if not isinstance(payload, dict):
                    raise ProviderResponseError(
                        "Provider response must be a JSON object."
                    )

                return payload

            except ProviderHTTPError as exc:
                last_error = exc
                if not exc.retryable:
                    raise

            except httpx.TimeoutException as exc:
                last_error = ProviderRequestTimeoutError()
                last_error.__cause__ = exc

            except httpx.RequestError as exc:
                last_error = ProviderConnectionError()
                last_error.__cause__ = exc

            if attempt < self._max_retries:
                await asyncio.sleep(min(0.25 * (2**attempt), 2.0))

        if last_error is not None:
            raise last_error

        raise ProviderConnectionError()

    @staticmethod
    def _validate_currency_code(code: str) -> str:
        """Validate and normalize a three-letter currency code."""
        normalized = code.strip().upper()

        if len(normalized) != 3 or not normalized.isalpha():
            raise ValueError(f"Invalid currency code: {code!r}")

        return normalized

    @classmethod
    def _build_params(
        cls,
        base: str,
        symbols: list[str] | None,
    ) -> dict[str, str]:
        """Build provider query parameters."""
        params = {
            "from": cls._validate_currency_code(base),
        }

        if symbols:
            normalized_symbols = sorted(
                {cls._validate_currency_code(symbol) for symbol in symbols}
            )
            params["to"] = ",".join(normalized_symbols)

        return params

    @classmethod
    def _validate_rate_payload(
        cls,
        payload: dict[str, Any],
        expected_base: str,
    ) -> dict[str, Any]:
        """Validate a standard Frankfurter rates response."""
        base = payload.get("base")
        rate_date = payload.get("date")
        rates = payload.get("rates")

        if not isinstance(base, str) or not isinstance(rate_date, str):
            raise ProviderResponseError(
                "Provider response is missing its base currency or date."
            )

        try:
            normalized_base = cls._validate_currency_code(base)
            date.fromisoformat(rate_date)
        except (TypeError, ValueError) as exc:
            raise ProviderResponseError(
                "Provider response contains invalid currency or date data."
            ) from exc

        if normalized_base != expected_base:
            raise ProviderResponseError(
                "Provider response base currency does not match the request."
            )

        if not isinstance(rates, dict):
            raise ProviderResponseError(
                "Provider response does not contain a valid rates object."
            )

        normalized_rates: dict[str, float] = {}

        for currency, value in rates.items():
            if not isinstance(currency, str):
                raise ProviderResponseError(
                    "Provider response contains an invalid currency code."
                )

            try:
                code = cls._validate_currency_code(currency)

                if isinstance(value, bool) or not isinstance(
                    value, (int, float)
                ):
                    raise ValueError("Rate must be numeric.")

                rate = float(value)

                if not math.isfinite(rate) or rate <= 0:
                    raise ValueError("Rate must be finite and positive.")

            except ValueError as exc:
                raise ProviderResponseError(
                    "Provider response contains an invalid exchange rate."
                ) from exc

            normalized_rates[code] = rate

        return {
            "base": normalized_base,
            "date": rate_date,
            "rates": normalized_rates,
        }

    async def get_latest_rates(
        self,
        base: str = "EUR",
        symbols: list[str] | None = None,
    ) -> dict[str, Any]:
        """Fetch the latest available rates."""
        normalized_base = self._validate_currency_code(base)
        payload = await self._request_json(
            "latest",
            self._build_params(normalized_base, symbols),
        )

        return self._validate_rate_payload(payload, normalized_base)

    async def get_historical_rates(
        self,
        rate_date: date,
        base: str = "EUR",
        symbols: list[str] | None = None,
    ) -> dict[str, Any]:
        """Fetch rates for a specific date."""
        normalized_base = self._validate_currency_code(base)

        payload = await self._request_json(
            rate_date.isoformat(),
            self._build_params(normalized_base, symbols),
        )

        return self._validate_rate_payload(payload, normalized_base)

    async def get_time_series(
        self,
        start_date: date,
        end_date: date,
        base: str = "EUR",
        symbols: list[str] | None = None,
    ) -> dict[str, Any]:
        """Fetch rates across an inclusive date range."""
        if start_date > end_date:
            raise ValueError("start_date must be on or before end_date")

        normalized_base = self._validate_currency_code(base)

        payload = await self._request_json(
            f"{start_date.isoformat()}..{end_date.isoformat()}",
            self._build_params(normalized_base, symbols),
        )

        # Frankfurter returns date-keyed rates for time-series queries.
        rates_payload = payload.get("rates")
        if not isinstance(rates_payload, dict) or not rates_payload:
            raise ProviderResponseError(
                "Provider returned an empty time-series response."
            )

        normalized_series: dict[str, dict[str, Any]] = {}

        for date_string, day_payload in rates_payload.items():
            try:
                parsed_date = date.fromisoformat(date_string)
            except (TypeError, ValueError) as exc:
                raise ProviderResponseError(
                    "Provider returned an invalid time-series date."
                ) from exc

            if not isinstance(day_payload, dict):
                raise ProviderResponseError(
                    "Provider returned an invalid time-series entry."
                )

            normalized_rates: dict[str, float] = {}
            for currency, value in day_payload.items():
                try:
                    code = self._validate_currency_code(currency)
                    if isinstance(value, bool) or not isinstance(
                        value, (int, float)
                    ):
                        raise ValueError("Rate must be numeric.")
                    rate = float(value)
                    if not math.isfinite(rate) or rate <= 0:
                        raise ValueError("Rate must be finite and positive.")
                except ValueError as exc:
                    raise ProviderResponseError(
                        "Provider returned an invalid exchange rate."
                    ) from exc
                normalized_rates[code] = rate

            normalized_series[parsed_date.isoformat()] = normalized_rates

        return {
            "base": normalized_base,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "rates": normalized_series,
        }

    async def aclose(self) -> None:
        """Close the HTTP client if this provider owns it."""
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None
