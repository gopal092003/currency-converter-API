"""Unit tests for rate freshness policies."""

from datetime import UTC, datetime, timedelta

import pytest
from app.modules.rates.freshness import (
    FreshnessStatus,
    RateFreshnessPolicy,
)


@pytest.fixture
def policy():
    return RateFreshnessPolicy(
        fresh_ttl_seconds=3600,
        max_stale_age_seconds=86400,
    )


@pytest.fixture
def now():
    return datetime(2026, 10, 14, 12, 0, tzinfo=UTC)


@pytest.mark.unit
def test_recent_rate_is_fresh(policy, now):
    fetched_at = now - timedelta(minutes=30)

    result = policy.evaluate(fetched_at, now=now)

    assert result.status == FreshnessStatus.FRESH
    assert result.is_usable is True
    assert result.should_refresh is False
    assert result.age_seconds == 1800


@pytest.mark.unit
def test_rate_at_freshness_boundary_is_fresh(policy, now):
    timestamp = now - timedelta(seconds=3600)

    result = policy.evaluate(timestamp, now=now)

    assert result.status == FreshnessStatus.FRESH
    assert result.is_usable is True


@pytest.mark.unit
def test_old_rate_is_stale_but_usable(policy, now):
    timestamp = now - timedelta(hours=2)

    result = policy.evaluate(timestamp, now=now)

    assert result.status == FreshnessStatus.STALE
    assert result.is_usable is True
    assert result.should_refresh is True


@pytest.mark.unit
def test_rate_at_maximum_stale_boundary_is_usable(policy, now):
    timestamp = now - timedelta(hours=24)

    result = policy.evaluate(timestamp, now=now)

    assert result.status == FreshnessStatus.STALE
    assert result.is_usable is True
    assert result.should_refresh is True


@pytest.mark.unit
def test_expired_rate_is_not_usable(policy, now):
    timestamp = now - timedelta(hours=24, seconds=1)

    result = policy.evaluate(timestamp, now=now)

    assert result.status == FreshnessStatus.EXPIRED
    assert result.is_usable is False
    assert result.should_refresh is True


@pytest.mark.unit
def test_future_timestamp_has_zero_age(policy, now):
    timestamp = now + timedelta(minutes=5)

    result = policy.evaluate(timestamp, now=now)

    assert result.age_seconds == 0
    assert result.status == FreshnessStatus.FRESH


@pytest.mark.unit
def test_date_input_is_supported(policy):
    result = policy.evaluate(
        datetime(2026, 10, 14, tzinfo=UTC).date(),
        now=datetime(2026, 10, 14, 12, 0, tzinfo=UTC),
    )

    assert result.age_seconds == 43200
    assert result.status == FreshnessStatus.STALE


@pytest.mark.unit
def test_naive_datetime_is_treated_as_utc(policy):
    result = policy.evaluate(
        datetime(2026, 10, 14, 11, 30),
        now=datetime(2026, 10, 14, 12, 0, tzinfo=UTC),
    )

    assert result.age_seconds == 1800
    assert result.status == FreshnessStatus.FRESH


@pytest.mark.unit
def test_invalid_freshness_thresholds_are_rejected():
    with pytest.raises(ValueError):
        RateFreshnessPolicy(
            fresh_ttl_seconds=3600,
            max_stale_age_seconds=1800,
        )


@pytest.mark.unit
def test_negative_ttl_is_rejected():
    with pytest.raises(ValueError):
        RateFreshnessPolicy(
            fresh_ttl_seconds=-1,
            max_stale_age_seconds=3600,
        )
