"""Exceptions raised by exchange-rate providers."""

from app.core.exceptions import (
    ProviderError,
    ProviderInvalidResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)


class ProviderConfigurationError(ProviderError):
    """Raised when a provider is configured incorrectly."""

    code = "PROVIDER_CONFIGURATION_ERROR"
    default_message = "The exchange-rate provider is misconfigured."
    retryable = False


class ProviderConnectionError(ProviderUnavailableError):
    """Raised when a provider cannot be reached."""

    code = "PROVIDER_CONNECTION_ERROR"
    default_message = "Could not connect to the exchange-rate provider."
    retryable = True


class ProviderRequestTimeoutError(ProviderTimeoutError):
    """Raised when a provider request exceeds its timeout."""

    code = "PROVIDER_TIMEOUT"
    default_message = "The exchange-rate provider request timed out."
    retryable = True


class ProviderHTTPError(ProviderError):
    """Raised when a provider returns an unsuccessful HTTP status."""

    code = "PROVIDER_HTTP_ERROR"
    default_message = "The exchange-rate provider returned an HTTP error."

    def __init__(
        self,
        status_code: int,
        message: str | None = None,
    ) -> None:
        self.provider_status_code = status_code
        self.retryable = status_code == 429 or status_code >= 500

        super().__init__(
            message or self.default_message,
            details={"provider_status_code": status_code},
            retryable=self.retryable,
        )


class ProviderResponseError(ProviderInvalidResponseError):
    """Raised when a provider response cannot be parsed or validated."""

    code = "PROVIDER_RESPONSE_ERROR"
    default_message = "The exchange-rate provider returned invalid data."
    retryable = False
