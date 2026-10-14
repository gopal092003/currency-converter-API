from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        validate_default=True,
    )

    # Application
    app_name: str = "Currency Converter API"
    app_env: Literal["development", "testing", "staging", "production"] = (
        "development"
    )
    app_version: str = "2.0.0"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # API version prefixes
    api_v1_prefix: str = "/api/v1"
    api_v2_prefix: str = "/api/v2"

    # Exchange-rate provider
    exchange_provider: str = "frankfurter"
    exchange_api: str = "https://api.frankfurter.app/latest"
    exchange_timeout_seconds: float = Field(default=5.0, gt=0, le=120)
    exchange_max_retries: int = Field(default=2, ge=0, le=10)

    # Rate freshness and caching
    rate_cache_ttl_seconds: int = Field(default=3600, ge=0)
    max_stale_rate_age_seconds: int = Field(default=86400, ge=0)

    # Optional infrastructure
    redis_url: str | None = None
    database_url: str | None = None

    # API-key authentication
    api_key_auth_enabled: bool = False
    api_key_pepper: SecretStr | None = None

    # Rate limiting
    rate_limit_enabled: bool = False
    rate_limit_requests: int = Field(default=60, gt=0)
    rate_limit_window_seconds: int = Field(default=60, gt=0)

    # Usage quotas
    usage_quota_enabled: bool = False
    monthly_request_quota: int = Field(default=10_000, gt=0)

    # Observability
    metrics_enabled: bool = True
    metrics_path: str = "/metrics"
    request_id_header: str = "X-Request-ID"

    # CORS
    cors_allowed_origins: str = ""

    # HTTP client
    http_max_connections: int = Field(default=100, gt=0)
    http_max_keepalive_connections: int = Field(default=20, ge=0)

    # Testing
    testing: bool = False

    @field_validator("api_v1_prefix", "api_v2_prefix", "metrics_path")
    @classmethod
    def validate_path_prefix(cls, value: str) -> str:
        """Require an absolute URL path without a trailing slash."""
        if not value.startswith("/"):
            raise ValueError("Path must start with '/'")

        if value != "/" and value.endswith("/"):
            raise ValueError("Path must not end with '/'")

        return value

    @field_validator("exchange_api")
    @classmethod
    def validate_exchange_api(cls, value: str) -> str:
        """Require an HTTP(S) provider URL."""
        from urllib.parse import urlparse

        parsed = urlparse(value)

        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("EXCHANGE_API must be a valid HTTP(S) URL")

        return value

    @field_validator("request_id_header")
    @classmethod
    def validate_request_id_header(cls, value: str) -> str:
        """Reject empty or malformed request-ID header names."""
        if not value or not all(
            char.isalnum() or char in "!#$%&'*+-.^_`|~"
            for char in value
        ):
            raise ValueError("REQUEST_ID_HEADER is invalid")

        return value

    @field_validator("cors_allowed_origins")
    @classmethod
    def normalize_cors_origins(cls, value: str) -> str:
        """Normalize comma-separated origins."""
        origins = [origin.strip().rstrip("/") for origin in value.split(",")]
        origins = [origin for origin in origins if origin]

        if "*" in origins and len(origins) > 1:
            raise ValueError(
                "Wildcard CORS origin cannot be combined with other origins"
            )

        return ",".join(origins)

    @model_validator(mode="after")
    def validate_cross_field_settings(self) -> "Settings":
        """Validate settings that depend on one another."""
        if self.http_max_keepalive_connections > self.http_max_connections:
            raise ValueError(
                "HTTP_MAX_KEEPALIVE_CONNECTIONS cannot exceed "
                "HTTP_MAX_CONNECTIONS"
            )

        if self.api_key_auth_enabled and not self.api_key_pepper:
            raise ValueError(
                "API_KEY_PEPPER is required when API_KEY_AUTH_ENABLED=true"
            )

        if self.app_env == "production" and self.debug:
            raise ValueError("DEBUG must be false in production")

        if self.app_env == "production" and self.api_key_auth_enabled:
            if not self.api_key_pepper or not self.api_key_pepper.get_secret_value():
                raise ValueError(
                    "A non-empty API_KEY_PEPPER is required in production"
                )

        return self

    @property
    def cors_origins(self) -> list[str]:
        """Return configured CORS origins as a list."""
        if not self.cors_allowed_origins:
            return []

        return self.cors_allowed_origins.split(",")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()


settings = get_settings()
