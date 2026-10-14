
"""Rate cache abstraction and in-memory implementation."""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from app.core.config import settings
from app.observability.metrics import record_cache_operation


@dataclass(frozen=True)
class CacheEntry:
    """A cached value and its expiration deadline."""

    value: Any
    expires_at: float


@runtime_checkable
class RateCache(Protocol):
    """Interface for rate-data caches."""

    async def get(self, key: str) -> Any | None:
        """Return a cached value, or None on a miss."""
        ...

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int | None = None,
    ) -> None:
        """Store a value with a time-to-live."""
        ...

    async def delete(self, key: str) -> None:
        """Delete one cached value."""
        ...

    async def clear(self) -> None:
        """Clear all cached values."""
        ...


class InMemoryRateCache:
    """Single-process in-memory cache with TTL expiration."""

    def __init__(self, default_ttl_seconds: int | None = None) -> None:
        self._default_ttl = (
            settings.rate_cache_ttl_seconds
            if default_ttl_seconds is None
            else default_ttl_seconds
        )
        self._entries: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            entry = self._entries.get(key)

            if entry is None:
                record_cache_operation("get", "miss")
                return None

            if entry.expires_at <= time.monotonic():
                self._entries.pop(key, None)
                record_cache_operation("get", "expired")
                return None

            record_cache_operation("get", "hit")
            return entry.value

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int | None = None,
    ) -> None:
        ttl = self._default_ttl if ttl_seconds is None else ttl_seconds

        if ttl < 0:
            raise ValueError("Cache TTL cannot be negative.")

        if ttl == 0:
            await self.delete(key)
            return

        entry = CacheEntry(
            value=value,
            expires_at=time.monotonic() + ttl,
        )

        async with self._lock:
            self._entries[key] = entry

        record_cache_operation("set", "success")

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._entries.pop(key, None)

        record_cache_operation("delete", "success")

    async def clear(self) -> None:
        async with self._lock:
            self._entries.clear()

        record_cache_operation("clear", "success")


def make_rate_cache_key(
    base: str,
    symbols: list[str] | None = None,
    rate_date: str = "latest",
) -> str:
    """Build a deterministic cache key for a rate query."""
    normalized_base = base.strip().upper()

    normalized_symbols = (
        sorted({symbol.strip().upper() for symbol in symbols})
        if symbols is not None
        else ["*"]
    )

    symbols_part = ",".join(normalized_symbols)
    return f"rates:{rate_date}:{normalized_base}:{symbols_part}"
