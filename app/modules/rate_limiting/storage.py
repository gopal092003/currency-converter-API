from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CounterResult:
    count: int
    reset_after_seconds: int


class RateLimitStorage(Protocol):
    async def increment(
        self,
        key: str,
        window_seconds: int,
    ) -> CounterResult: ...

    async def close(self) -> None: ...


class InMemoryRateLimitStorage:
    """Single-process backend for tests and local development only."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._counters: dict[str, tuple[int, float]] = {}

    async def increment(
        self,
        key: str,
        window_seconds: int,
    ) -> CounterResult:
        now = time.monotonic()

        async with self._lock:
            current = self._counters.get(key)

            if current is None or now >= current[1]:
                count = 1
                reset_at = now + window_seconds
            else:
                count = current[0] + 1
                reset_at = current[1]

            self._counters[key] = (count, reset_at)
            reset_after = max(1, int(reset_at - now + 0.999))

            return CounterResult(
                count=count,
                reset_after_seconds=reset_after,
            )

    async def close(self) -> None:
        async with self._lock:
            self._counters.clear()


class RedisRateLimitStorage:
    """Distributed fixed-window counter backed by Redis."""

    _INCREMENT_SCRIPT = """
    local count = redis.call('INCR', KEYS[1])
    if count == 1 then
        redis.call('EXPIRE', KEYS[1], ARGV[1])
    end
    local ttl = redis.call('TTL', KEYS[1])
    return {count, ttl}
    """

    def __init__(self, redis_client) -> None:
        self._redis = redis_client

    async def increment(
        self,
        key: str,
        window_seconds: int,
    ) -> CounterResult:
        result = await self._redis.eval(
            self._INCREMENT_SCRIPT,
            1,
            key,
            window_seconds,
        )

        count, ttl = int(result[0]), int(result[1])

        # A positive TTL should exist after the atomic script. Keep the
        # response safe if a Redis-compatible backend returns an unusual TTL.
        return CounterResult(
            count=count,
            reset_after_seconds=max(1, ttl),
        )

    async def close(self) -> None:
        # The client may be shared by the rest of the application.
        # Its lifecycle should be managed by the application lifespan.
        return None


async def create_rate_limit_storage(redis_url: str | None):
    """Choose Redis when configured; otherwise use local memory.

    The in-memory fallback is unsuitable for multi-worker or multi-instance
    production deployments because each process has independent counters.
    """
    if not redis_url:
        return InMemoryRateLimitStorage()

    try:
        from redis.asyncio import Redis
    except ImportError as exc:
        raise RuntimeError(
            "Redis is configured but the redis package is not installed. "
            'Install the optional dependency with: pip install ".[redis]"'
        ) from exc

    client = Redis.from_url(redis_url, decode_responses=False)
    await client.ping()
    return RedisRateLimitStorage(client)
