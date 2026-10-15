"""Business logic for retrieving and normalizing exchange rates."""

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.exceptions import (
    ProviderError,
    RateNotFoundError,
    UnsupportedCurrencyError,
    ValidationError,
)
from app.modules.providers.base import ExchangeRateProvider
from app.modules.rates.schemas import (
    RateData,
    RateQuery,
    TimeSeriesRateData,
)


class RatesService:
    """Retrieve, validate, and normalize exchange-rate data."""

    def __init__(self, provider: ExchangeRateProvider) -> None:
        self._provider = provider

    async def get_latest_rates(
        self,
        base: str = "EUR",
        symbols: list[str] | None = None,
    ) -> RateData:
        """Retrieve the latest available rates for a base currency."""
        query = self._validate_query(base, symbols)

        try:
            payload = await self._provider.get_latest_rates(
                base=query.base,
                symbols=query.symbols,
            )
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                "Unable to retrieve the latest exchange rates.",
                retryable=False,
            ) from exc

        return self._normalize_rate_payload(
            payload=payload,
            expected_base=query.base,
        )

    async def get_historical_rates(
        self,
        rate_date: date,
        base: str = "EUR",
        symbols: list[str] | None = None,
    ) -> RateData:
        """Retrieve rates for a specific historical date."""
        query = self._validate_query(base, symbols)

        if rate_date > date.today():
            raise ValidationError("Historical rate date cannot be in the future.")

        try:
            payload = await self._provider.get_historical_rates(
                rate_date=rate_date,
                base=query.base,
                symbols=query.symbols,
            )
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                "Unable to retrieve historical exchange rates.",
                retryable=False,
            ) from exc

        result = self._normalize_rate_payload(
            payload=payload,
            expected_base=query.base,
        )

        # Some providers return the most recent business-day rates when
        # a requested date is a weekend or holiday. Preserve the date
        # returned by the provider rather than mislabeling it.
        if result.rate_date > rate_date:
            raise ProviderError(
                "The provider returned a rate date after the requested date.",
                retryable=False,
            )

        return result

    async def get_time_series(
        self,
        start_date: date,
        end_date: date,
        base: str = "EUR",
        symbols: list[str] | None = None,
    ) -> TimeSeriesRateData:
        """Retrieve rates across an inclusive date range."""
        query = self._validate_query(base, symbols)

        if start_date > end_date:
            raise ValidationError("start_date must be on or before end_date.")

        if end_date > date.today():
            raise ValidationError("The time-series end date cannot be in the future.")

        try:
            payload = await self._provider.get_time_series(
                start_date=start_date,
                end_date=end_date,
                base=query.base,
                symbols=query.symbols,
            )
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                "Unable to retrieve exchange-rate time-series data.",
                retryable=False,
            ) from exc

        if not isinstance(payload, dict):
            raise ProviderError(
                "The provider returned an invalid time-series response.",
                retryable=False,
            )

        returned_base = self._normalize_base(payload.get("base"))
        if returned_base != query.base:
            raise ProviderError(
                "The provider returned rates for an unexpected base currency.",
                retryable=False,
            )

        raw_rates = payload.get("rates")
        if not isinstance(raw_rates, dict):
            raise ProviderError(
                "The provider returned an invalid time-series rates mapping.",
                retryable=False,
            )

        normalized_rates: dict[date, dict[str, Decimal]] = {}

        for raw_date, daily_rates in raw_rates.items():
            try:
                parsed_date = self._parse_date(raw_date)
            except (TypeError, ValueError) as exc:
                raise ProviderError(
                    "The provider returned an invalid date in its time series.",
                    retryable=False,
                ) from exc

            if not start_date <= parsed_date <= end_date:
                raise ProviderError(
                    "The provider returned rates outside the requested date range.",
                    retryable=False,
                )

            normalized_rates[parsed_date] = self._normalize_rates(
                daily_rates,
                expected_base=query.base,
                symbols=query.symbols,
            )

        return TimeSeriesRateData(
            base=query.base,
            start_date=start_date,
            end_date=end_date,
            rates=normalized_rates,
        )

    @staticmethod
    def _validate_query(
        base: str,
        symbols: list[str] | None,
    ) -> RateQuery:
        """Normalize and validate requested currency codes."""
        try:
            query = RateQuery(base=base, symbols=symbols)
        except ValueError as exc:
            raise ValidationError(
                "The base currency or requested currency codes are invalid."
            ) from exc

        if query.symbols is not None and query.base in query.symbols:
            raise ValidationError("The base currency must not be included in symbols.")

        return query

    @staticmethod
    def _normalize_base(value: Any) -> str:
        """Validate and normalize a provider's base currency."""
        if not isinstance(value, str):
            raise ProviderError(
                "The provider response is missing a valid base currency.",
                retryable=False,
            )

        normalized = value.strip().upper()

        if len(normalized) != 3 or not normalized.isalpha():
            raise ProviderError(
                "The provider returned an invalid base currency.",
                retryable=False,
            )

        return normalized

    @staticmethod
    def _parse_date(value: Any) -> date:
        """Parse a provider date into a Python date."""
        if isinstance(value, date):
            return value

        if isinstance(value, str):
            return date.fromisoformat(value)

        raise ValueError("Expected an ISO-formatted date.")

    def _normalize_rate_payload(
        self,
        payload: Any,
        expected_base: str,
    ) -> RateData:
        """Validate and normalize a single-date provider response."""
        if not isinstance(payload, dict):
            raise ProviderError(
                "The provider returned an invalid rate response.",
                retryable=False,
            )

        returned_base = self._normalize_base(payload.get("base"))

        if returned_base != expected_base:
            raise ProviderError(
                "The provider returned rates for an unexpected base currency.",
                retryable=False,
            )

        try:
            rate_date = self._parse_date(payload.get("date"))
        except (TypeError, ValueError) as exc:
            raise ProviderError(
                "The provider returned an invalid rate date.",
                retryable=False,
            ) from exc

        if rate_date > date.today():
            raise ProviderError(
                "The provider returned a future rate date.",
                retryable=False,
            )

        normalized_rates = self._normalize_rates(
            payload.get("rates"),
            expected_base=expected_base,
        )

        if not normalized_rates:
            raise RateNotFoundError(
                "No exchange rates were returned for the requested query."
            )

        return RateData(
            base=expected_base,
            rate_date=rate_date,
            rates=normalized_rates,
        )

    @staticmethod
    def _normalize_rates(
        raw_rates: Any,
        expected_base: str,
        symbols: list[str] | None = None,
    ) -> dict[str, Decimal]:
        """Validate currency codes and convert rates to Decimal."""
        if not isinstance(raw_rates, dict):
            raise ProviderError(
                "The provider returned an invalid rates mapping.",
                retryable=False,
            )

        normalized: dict[str, Decimal] = {}

        for raw_code, raw_value in raw_rates.items():
            if not isinstance(raw_code, str):
                raise ProviderError(
                    "The provider returned an invalid currency code.",
                    retryable=False,
                )

            code = raw_code.strip().upper()

            if len(code) != 3 or not code.isalpha():
                raise ProviderError(
                    "The provider returned an invalid currency code.",
                    retryable=False,
                )

            if code == expected_base:
                raise ProviderError(
                    "The provider included the base currency in its rates.",
                    retryable=False,
                )

            if symbols is not None and code not in symbols:
                continue

            try:
                rate = Decimal(str(raw_value))
            except (InvalidOperation, ValueError, TypeError) as exc:
                raise ProviderError(
                    "The provider returned a non-numeric exchange rate.",
                    retryable=False,
                ) from exc

            if not rate.is_finite() or rate <= Decimal("0"):
                raise ProviderError(
                    "The provider returned a non-positive or non-finite rate.",
                    retryable=False,
                )

            if code in normalized:
                raise ProviderError(
                    "The provider returned duplicate currency codes.",
                    retryable=False,
                )

            normalized[code] = rate

        if symbols is not None:
            missing = set(symbols) - set(normalized)

            if missing:
                missing_codes = ", ".join(sorted(missing))
                raise UnsupportedCurrencyError(
                    f"No rates were returned for: {missing_codes}."
                )

        return normalized
