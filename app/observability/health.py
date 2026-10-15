from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

HealthStatus = Literal["ok", "degraded", "unavailable"]


class ComponentHealth(BaseModel):
    status: HealthStatus
    message: str | None = None
    latency_ms: float | None = Field(default=None, ge=0)


class HealthResponse(BaseModel):
    status: HealthStatus
    timestamp: datetime
    checks: dict[str, ComponentHealth]


def liveness() -> dict[str, Any]:
    """Return process liveness without checking external dependencies."""
    return {
        "status": "ok",
        "timestamp": datetime.now(UTC),
    }


def check_database(db: Session) -> ComponentHealth:
    """Check database connectivity using a lightweight query."""
    import time

    started = time.perf_counter()
    try:
        db.execute(text("SELECT 1"))
        return ComponentHealth(
            status="ok",
            latency_ms=(time.perf_counter() - started) * 1000,
        )
    except Exception:
        return ComponentHealth(
            status="unavailable",
            message="Database check failed",
            latency_ms=(time.perf_counter() - started) * 1000,
        )


async def check_redis(redis_client: Any | None) -> ComponentHealth:
    """Check Redis when configured; treat an absent client as unconfigured."""
    import time

    if redis_client is None:
        return ComponentHealth(
            status="degraded",
            message="Redis is not configured",
        )

    started = time.perf_counter()
    try:
        await redis_client.ping()
        return ComponentHealth(
            status="ok",
            latency_ms=(time.perf_counter() - started) * 1000,
        )
    except Exception:
        return ComponentHealth(
            status="unavailable",
            message="Redis check failed",
            latency_ms=(time.perf_counter() - started) * 1000,
        )


async def check_provider(provider: Any) -> ComponentHealth:
    """Check the configured provider with a lightweight latest-rates request.

    A provider outage should normally degrade readiness, not liveness.
    This check makes a real provider request and should be used deliberately
    to avoid adding unnecessary traffic to external services.
    """
    import time

    started = time.perf_counter()
    try:
        await provider.get_latest_rates(base="EUR", symbols=["USD"])
        return ComponentHealth(
            status="ok",
            latency_ms=(time.perf_counter() - started) * 1000,
        )
    except Exception:
        return ComponentHealth(
            status="unavailable",
            message="Exchange-rate provider check failed",
            latency_ms=(time.perf_counter() - started) * 1000,
        )


def combine_health(
    checks: dict[str, ComponentHealth],
) -> HealthResponse:
    statuses = {item.status for item in checks.values()}

    if "unavailable" in statuses:
        overall: HealthStatus = "unavailable"
    elif "degraded" in statuses:
        overall = "degraded"
    else:
        overall = "ok"

    return HealthResponse(
        status=overall,
        timestamp=datetime.now(UTC),
        checks=checks,
    )
