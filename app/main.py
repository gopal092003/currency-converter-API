
"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import AppException
from app.modules.currency.service import CurrencyConversionService
from app.modules.providers.factory import create_provider
from app.modules.rates.service import RatesService

# This module should combine your API version routers.
from app.api.router import api_router


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Initialize shared resources and release them at shutdown."""

    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(settings.exchange_timeout_seconds),
        limits=httpx.Limits(
            max_connections=settings.http_max_connections,
            max_keepalive_connections=(
                settings.http_max_keepalive_connections
            ),
        ),
    )

    try:
        provider = create_provider(client=http_client)

        application.state.http_client = http_client
        application.state.provider = provider
        application.state.currency_service = CurrencyConversionService(
            provider
        )
        application.state.rates_service = RatesService(provider)

        yield
    finally:
        await http_client.aclose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "A currency conversion API with exchange-rate retrieval, "
            "historical rates, and currency conversion."
        ),
        debug=settings.debug,
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
        openapi_url=(
            "/openapi.json"
            if settings.app_env != "production"
            else None
        ),
        lifespan=lifespan,
    )

    # Enable CORS only for explicitly configured origins.
    if settings.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=[
                "Authorization",
                "Content-Type",
                settings.request_id_header,
            ],
        )

    @application.exception_handler(AppException)
    async def handle_app_exception(
        request: Request,
        exc: AppException,
    ) -> JSONResponse:
        """Return a consistent response for application exceptions."""

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": str(exc),
                    "details": exc.details,
                },
            },
        )

    @application.exception_handler(RequestValidationError)
    async def handle_validation_exception(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Return a consistent response for invalid request data."""

        errors = [
            {
                "location": list(error.get("loc", ())),
                "message": error.get("msg", "Invalid input."),
                "type": error.get("type", "value_error"),
            }
            for error in exc.errors()
        ]

        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "The request contains invalid data.",
                    "details": {"errors": errors},
                },
            },
        )

    @application.get(
        "/health/live",
        tags=["Health"],
        summary="Liveness check",
    )
    async def liveness() -> dict[str, str]:
        """Confirm that the application process is responding."""

        return {"status": "ok"}

    application.include_router(api_router)

    return application


app = create_app()
