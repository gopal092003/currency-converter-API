
"""OpenTelemetry tracing setup."""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def configure_tracing() -> None:
    """Configure OpenTelemetry tracing when dependencies are installed."""
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logger.warning(
            "OpenTelemetry dependencies are unavailable; tracing is disabled."
        )
        return

    current_provider = trace.get_tracer_provider()
    if isinstance(current_provider, TracerProvider):
        logger.debug("OpenTelemetry tracing is already configured.")
        return

    resource = Resource.create(
        {
            "service.name": settings.app_name,
            "service.version": settings.app_version,
            "deployment.environment": settings.app_env,
        }
    )

    provider = TracerProvider(resource=resource)

    # The exporter reads OTEL_EXPORTER_OTLP_ENDPOINT and related
    # standard OpenTelemetry environment variables.
    exporter = OTLPSpanExporter()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    HTTPXClientInstrumentor().instrument()

    logger.info("OpenTelemetry tracing configured.")


def instrument_fastapi(application) -> None:
    """Instrument a FastAPI application if OpenTelemetry is available."""
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    except ImportError:
        logger.debug("FastAPI tracing instrumentation is unavailable.")
        return

    FastAPIInstrumentor.instrument_app(application)
