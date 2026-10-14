
"""Background worker for refreshing exchange-rate cache entries."""

import asyncio
import logging
from datetime import date
from decimal import Decimal
from typing import Sequence

from app.core.config import settings
from app.modules.providers.base import ExchangeRateProvider
from app.modules.rates.cache import (
    RateCache,
    make_rate_cache_key,
)
from app.modules.rates.schemas import RateData
from app.observability.metrics import record_provider_request

logger = logging.getLogger(__name__)


class RateRefreshWorker:
    """Periodically refresh cached rates for configured base currencies."""

    def __init__(
        self,
        provider: ExchangeRateProvider,
        cache: RateCache,
        *,
        base_currencies: Sequence[str] = ("EUR", "USD", "INR"),
        interval_seconds: int = 1800,
        cache_ttl_seconds: int | None = None,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("Refresh interval must be positive.")

        self.provider = provider
        self.cache = cache
        self.base_currencies = tuple(
            sorted({code.strip().upper() for code in base_currencies})
        )
        self.interval_seconds = interval_seconds
        self.cache_ttl_seconds = (
            settings.rate_cache_ttl_seconds
            if cache_ttl_seconds is None
            else cache_ttl_seconds
        )

        if self.cache_ttl_seconds <= 0:
            raise ValueError("Cache TTL must be positive for refreshes.")

        self._stop_event = asyncio.Event()

    async def refresh_one(self, base: str) -> bool:
        """Refresh the latest rate dataset for one base currency."""
        try:
            payload = await self.provider.get_latest_rates(base=base)
            record_provider_request(
                self.provider.name,
                "latest_rates",
                "success",
            )

            if not isinstance(payload, dict):
                raise ValueError("Provider response must be an object.")

            returned_base = payload.get("base")
            if not isinstance(returned_base, str):
                raise ValueError("Provider response has no valid base.")

            returned_base = returned_base.strip().upper()
            if returned_base != base:
                raise ValueError(
                    f"Expected base {base}, received {returned_base}."
                )

            rate_date = date.fromisoformat(payload["date"])
            if rate_date > date.today():
                raise ValueError("Provider returned a future rate date.")

            raw_rates = payload.get("rates")
            if not isinstance(raw_rates, dict):
                raise ValueError("Provider rates must be an object.")

            normalized_rates: dict[str, Decimal] = {}

            for raw_code, raw_rate in raw_rates.items():
                if not isinstance(raw_code, str):
                    raise ValueError("Currency codes must be strings.")

                code = raw_code.strip().upper()
                rate = Decimal(str(raw_rate))

                if (
                    len(code) != 3
                    or not code.isalpha()
                    or code == base
                    or not rate.is_finite()
                    or rate <= 0
                ):
                    raise ValueError(
                        f"Invalid rate entry returned for {raw_code!r}."
                    )

                if code in normalized_rates:
                    raise ValueError(
                        f"Duplicate currency code returned: {code}."
                    )

                normalized_rates[code] = rate

            rate_data = RateData(
                base=base,
                rate_date=rate_date,
                rates=normalized_rates,
            )

            cache_key = make_rate_cache_key(
                base=base,
                symbols=None,
                rate_date="latest",
            )

            await self.cache.set(
                cache_key,
                rate_data,
                ttl_seconds=self.cache_ttl_seconds,
            )

            logger.info(
                "Rate cache refreshed",
                extra={
                    "provider": self.provider.name,
                    "base_currency": base,
                    "rate_date": rate_date.isoformat(),
                    "rate_count": len(normalized_rates),
                },
            )
            return True

        except asyncio.CancelledError:
            raise
        except Exception:
            record_provider_request(
                self.provider.name,
                "latest_rates",
                "error",
            )
            logger.exception(
                "Rate refresh failed",
                extra={"base_currency": base},
            )
            return False

    async def run_once(self) -> dict[str, int]:
        """Refresh all configured base currencies once."""
        successes = 0
        failures = 0

        for base in self.base_currencies:
            if await self.refresh_one(base):
                successes += 1
            else:
                failures += 1

        return {
            "successes": successes,
            "failures": failures,
        }

    async def run_forever(self) -> None:
        """Run refresh cycles until cancellation or stop is requested."""
        logger.info(
            "Rate refresh worker started",
            extra={
                "base_currencies": list(self.base_currencies),
                "interval_seconds": self.interval_seconds,
            },
        )

        try:
            while not self._stop_event.is_set():
                await self.run_once()

                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self.interval_seconds,
                    )
                except asyncio.TimeoutError:
                    pass
        finally:
            logger.info("Rate refresh worker stopped")

    def stop(self) -> None:
        """Request a graceful stop after the current cycle."""
        self._stop_event.set()
