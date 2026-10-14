
"""Integration tests for the rate cache."""

import asyncio

import pytest

from app.modules.rates.cache import (
    InMemoryRateCache,
    make_rate_cache_key,
)


@pytest.fixture
def cache():
    return InMemoryRateCache(default_ttl_seconds=60)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_miss_returns_none(cache):
    assert await cache.get("rates:latest:EUR:USD") is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_set_and_get(cache):
    value = {"base": "EUR", "rates": {"USD": "1.17"}}

    await cache.set("rates:latest:EUR:USD", value)

    assert await cache.get("rates:latest:EUR:USD") == value


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_expires_entries():
    cache = InMemoryRateCache(default_ttl_seconds=1)

    await cache.set("short-lived", {"value": 1})
    assert await cache.get("short-lived") == {"value": 1}

    await asyncio.sleep(1.1)

    assert await cache.get("short-lived") is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_ttl_zero_deletes_entry(cache):
    await cache.set("key", "value")
    await cache.set("key", "replacement", ttl_seconds=0)

    assert await cache.get("key") is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_rejects_negative_ttl(cache):
    with pytest.raises(ValueError):
        await cache.set("key", "value", ttl_seconds=-1)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_delete(cache):
    await cache.set("key", "value")
    await cache.delete("key")

    assert await cache.get("key") is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_clear(cache):
    await cache.set("key-1", "value-1")
    await cache.set("key-2", "value-2")

    await cache.clear()

    assert await cache.get("key-1") is None
    assert await cache.get("key-2") is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_handles_concurrent_writes(cache):
    async def write(index: int) -> None:
        await cache.set(f"key-{index}", index)

    await asyncio.gather(*(write(i) for i in range(100)))

    for i in range(100):
        assert await cache.get(f"key-{i}") == i


@pytest.mark.integration
def test_cache_key_normalizes_base_and_symbols():
    first = make_rate_cache_key(
        base="eur",
        symbols=["usd", "inr", "USD"],
    )
    second = make_rate_cache_key(
        base="EUR",
        symbols=["INR", "USD"],
    )

    assert first == second


@pytest.mark.integration
def test_cache_key_distinguishes_date_and_base():
    latest = make_rate_cache_key("EUR", ["USD"], "latest")
    historical = make_rate_cache_key("EUR", ["USD"], "2026-10-01")
    other_base = make_rate_cache_key("USD", ["INR"], "latest")

    assert latest != historical
    assert latest != other_base
