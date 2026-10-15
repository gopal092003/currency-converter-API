"""Currency conversion business logic."""

from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.exceptions import (
    UnsupportedCurrencyError,
    ValidationError,
)
from app.modules.currency.rounding import convert_and_round
from app.modules.currency.schemas import (
    ConversionRequest,
    ConversionResult,
)
from app.modules.providers.base import ExchangeRateProvider
from app.modules.providers.exceptions import ProviderError


class CurrencyConversionService:
    """Convert monetary amounts using an exchange-rate provider."""

    def __init__(self, provider: ExchangeRateProvider) -> None:
        self._provider = provider

    async def convert(
        self,
        request: ConversionRequest,
    ) -> ConversionResult:
        """Convert an amount using the latest available exchange rate."""
        source = request.from_currency
        target = request.to_currency
        amount = request.amount

        if not amount.is_finite() or amount < 0:
            raise ValidationError("Amount must be a finite, non-negative decimal.")

        if source == target:
            return ConversionResult(
                amount=amount,
                from_currency=source,
                to_currency=target,
                exchange_rate=Decimal("1"),
                converted_amount=convert_and_round(
                    amount,
                    Decimal("1"),
                    target,
                ),
            )

        try:
            payload = await self._provider.get_latest_rates(
                base=source,
                symbols=[target],
            )
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                "Unable to retrieve exchange rates.",
                retryable=False,
            ) from exc

        rates = payload.get("rates")

        if not isinstance(rates, dict):
            raise ProviderError(
                "The provider returned an invalid rates structure.",
                retryable=False,
            )

        raw_rate: Any = rates.get(target)

        if raw_rate is None:
            raise UnsupportedCurrencyError(
                f"No exchange rate is available for {target}.",
                details={
                    "from_currency": source,
                    "to_currency": target,
                },
            )

        try:
            rate = Decimal(str(raw_rate))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ProviderError(
                "The provider returned a non-numeric exchange rate.",
                retryable=False,
            ) from exc

        if not rate.is_finite() or rate <= 0:
            raise ProviderError(
                "The provider returned an invalid exchange rate.",
                retryable=False,
            )

        raw_date = payload.get("date")
        rate_date = None

        if raw_date is not None:
            from datetime import date

            try:
                rate_date = date.fromisoformat(raw_date)
            except (TypeError, ValueError) as exc:
                raise ProviderError(
                    "The provider returned an invalid rate date.",
                    retryable=False,
                ) from exc

        converted_amount = convert_and_round(
            amount,
            rate,
            target,
        )

        return ConversionResult(
            amount=amount,
            from_currency=source,
            to_currency=target,
            exchange_rate=rate,
            converted_amount=converted_amount,
            rate_date=rate_date,
        )
