
"""Prometheus metrics and HTTP request instrumentation."""

import logging
import time

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )

    REQUESTS_TOTAL = Counter(
        "currency_api_requests_total",
        "Total HTTP requests.",
        ["method", "path", "status"],
    )

    REQUEST_DURATION = Histogram(
        "currency_api_request_duration_seconds",
        "HTTP request duration in seconds.",
        ["method", "path"],
    )

    PROVIDER_REQUESTS_TOTAL = Counter(
        "currency_api_provider_requests_total",
        "Total exchange-rate provider requests.",
        ["provider", "operation", "outcome"],
    )

    CACHE_OPERATIONS_TOTAL = Counter(
        "currency_api_cache_operations_total",
        "Total cache operations.",
        ["operation", "outcome"],
    )

    STALE_RATE_READS_TOTAL = Counter(
        "currency_api_stale_rate_reads_total",
        "Number of times stale exchange rates were served.",
    )

    RATE_AGE_SECONDS = Gauge(
        "currency_api_rate_age_seconds",
        "Age of the most recently evaluated exchange rate.",
        ["base"],
    )

    PROMETHEUS_AVAILABLE = True

except ImportError:
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4"
    PROMETHEUS_AVAILABLE = False
    REQUESTS_TOTAL = None
    REQUEST_DURATION = None
    PROVIDER_REQUESTS_TOTAL = None
    CACHE_OPERATIONS_TOTAL = None
    STALE_RATE_READS_TOTAL = None
    RATE_AGE_SECONDS = None
    generate_latest = None


def record_provider_request(
    provider: str,
    operation: str,
    outcome: str,
) -> None:
    """Record the outcome of a provider operation."""
    if PROMETHEUS_AVAILABLE:
        PROVIDER_REQUESTS_TOTAL.labels(
            provider=provider,
            operation=operation,
            outcome=outcome,
        ).inc()


def record_cache_operation(operation: str, outcome: str) -> None:
    """Record a cache hit, miss, write, or error."""
    if PROMETHEUS_AVAILABLE:
        CACHE_OPERATIONS_TOTAL.labels(
            operation=operation,
            outcome=outcome,
        ).inc()


def record_rate_age(base: str, age_seconds: float) -> None:
    """Record the age of a rate dataset."""
    if PROMETHEUS_AVAILABLE:
        RATE_AGE_SECONDS.labels(base=base).set(max(0, age_seconds))


def record_stale_rate_read() -> None:
    """Record a response that used stale rates."""
    if PROMETHEUS_AVAILABLE:
        STALE_RATE_READS_TOTAL.inc()


class MetricsMiddleware:
    """Collect request count and latency without high-cardinality labels."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or not settings.metrics_enabled:
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status_code = 500
        method = scope.get("method", "UNKNOWN")
        # Avoid raw paths containing IDs or user-controlled values.
        # Use the route template where available in a later metrics hook.
        path = scope.get("path", "/")
        route_label = path if path in {
            "/health/live",
            settings.metrics_path,
        } else "unmatched_or_unresolved"

        async def capture_status(message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, capture_status)
        finally:
            duration = time.perf_counter() - start

            if PROMETHEUS_AVAILABLE:
                REQUESTS_TOTAL.labels(
                    method=method,
                    path=route_label,
                    status=str(status_code),
                ).inc()
                REQUEST_DURATION.labels(
                    method=method,
                    path=route_label,
                ).observe(duration)


def render_metrics() -> tuple[bytes, str]:
    """Return the Prometheus exposition payload."""
    if not settings.metrics_enabled or not PROMETHEUS_AVAILABLE:
        return (
            b"Metrics are disabled or prometheus-client is not installed.",
            "text/plain; charset=utf-8",
        )

    return generate_latest(), CONTENT_TYPE_LATEST
