from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import configure_logging
from app.modules.currency.service import CurrencyConversionService
from app.modules.providers.factory import create_provider
from app.modules.rate_limiting.service import RateLimitService
from app.modules.rate_limiting.storage import create_rate_limit_storage
from app.modules.rates.service import RatesService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Manage shared application resources and their shutdown."""
    configure_logging()

    http_client: httpx.AsyncClient | None = None
    rate_storage = None
    redis_client = None

    try:
        http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.exchange_timeout_seconds),
            limits=httpx.Limits(
                max_connections=settings.http_max_connections,
                max_keepalive_connections=settings.http_max_keepalive_connections,
            ),
        )

        provider = create_provider(client=http_client)

        application.state.http_client = http_client
        application.state.provider = provider
        application.state.currency_service = CurrencyConversionService(provider)
        application.state.rates_service = RatesService(provider)

        rate_storage = await create_rate_limit_storage(settings.redis_url)
        application.state.rate_limit_storage = rate_storage
        application.state.rate_limit_service = RateLimitService(rate_storage)

        # RedisRateLimitStorage owns a Redis client, but it intentionally
        # doesn't close it itself because other services may share clients.
        # Keep a reference here so the application can close it at shutdown.
        redis_client = getattr(rate_storage, "_redis", None)

        logger.info("Application startup completed")
        yield

    except Exception:
        logger.exception("Application startup or runtime lifecycle failed")
        raise

    finally:
        if rate_storage is not None:
            try:
                await rate_storage.close()
            except Exception:
                logger.exception("Failed to close rate-limit storage")

        if redis_client is not None:
            try:
                await redis_client.aclose()
            except Exception:
                logger.exception("Failed to close Redis client")

        if http_client is not None:
            try:
                await http_client.aclose()
            except Exception:
                logger.exception("Failed to close HTTP client")

        logger.info("Application shutdown completed")
