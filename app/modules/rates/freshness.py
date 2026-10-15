"""Exchange-rate freshness and stale-data policies."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from enum import StrEnum

from app.core.config import settings


class FreshnessStatus(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    EXPIRED = "expired"


@dataclass(frozen=True)
class FreshnessResult:
    """Freshness evaluation for a rate dataset."""

    status: FreshnessStatus
    age_seconds: float
    is_usable: bool
    should_refresh: bool


class RateFreshnessPolicy:
    """Evaluate rate age against configured freshness thresholds."""

    def __init__(
        self,
        fresh_ttl_seconds: int | None = None,
        max_stale_age_seconds: int | None = None,
    ) -> None:
        self.fresh_ttl_seconds = (
            settings.rate_cache_ttl_seconds
            if fresh_ttl_seconds is None
            else fresh_ttl_seconds
        )
        self.max_stale_age_seconds = (
            settings.max_stale_rate_age_seconds
            if max_stale_age_seconds is None
            else max_stale_age_seconds
        )

        if self.fresh_ttl_seconds < 0:
            raise ValueError("Fresh TTL cannot be negative.")

        if self.max_stale_age_seconds < self.fresh_ttl_seconds:
            raise ValueError("Maximum stale age must be at least the fresh TTL.")

    @staticmethod
    def _as_utc_datetime(
        value: date | datetime,
    ) -> datetime:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=UTC)
            return value.astimezone(UTC)

        if isinstance(value, date):
            return datetime.combine(
                value,
                time.min,
                tzinfo=UTC,
            )

        raise TypeError("Rate timestamp must be a date or datetime.")

    def evaluate(
        self,
        rate_timestamp: date | datetime,
        now: datetime | None = None,
    ) -> FreshnessResult:
        """Evaluate freshness at the specified time or current UTC time."""
        observed_at = self._as_utc_datetime(rate_timestamp)
        current_time = self._as_utc_datetime(now or datetime.now(UTC))

        age_seconds = max(
            0.0,
            (current_time - observed_at).total_seconds(),
        )

        if age_seconds <= self.fresh_ttl_seconds:
            status = FreshnessStatus.FRESH
            usable = True
            should_refresh = False
        elif age_seconds <= self.max_stale_age_seconds:
            status = FreshnessStatus.STALE
            usable = True
            should_refresh = True
        else:
            status = FreshnessStatus.EXPIRED
            usable = False
            should_refresh = True

        return FreshnessResult(
            status=status,
            age_seconds=age_seconds,
            is_usable=usable,
            should_refresh=should_refresh,
        )
