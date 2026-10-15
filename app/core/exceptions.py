"""Application-specific exceptions.
Services raise these exceptions without depending on HTTP response handling.
The API layer is responsible for converting them into HTTP responses.
"""

from typing import Any

from app.core.constants import (
    ERROR_AUTHENTICATION,
    ERROR_AUTHORIZATION,
    ERROR_INTERNAL_ERROR,
    ERROR_INVALID_REQUEST,
    ERROR_PROVIDER_ERROR,
    ERROR_PROVIDER_INVALID_RESPONSE,
    ERROR_PROVIDER_TIMEOUT,
    ERROR_PROVIDER_UNAVAILABLE,
    ERROR_QUOTA_EXCEEDED,
    ERROR_RATE_LIMIT_EXCEEDED,
    ERROR_RATE_NOT_FOUND,
    ERROR_UNSUPPORTED_CURRENCY,
    ERROR_VALIDATION,
)


class AppException(Exception):
    """Base exception for expected application-level failures."""

    status_code: int = 500
    code: str = ERROR_INTERNAL_ERROR
    default_message: str = "An unexpected application error occurred."
    retryable: bool = False

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
        retryable: bool | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details
        if retryable is not None:
            self.retryable = retryable
        super().__init__(self.message)


class InvalidRequestError(AppException):
    """Raised when request parameters are invalid."""

    status_code = 400
    code = ERROR_INVALID_REQUEST
    default_message = "The request is invalid."


class ValidationError(AppException):
    """Raised when application-level input validation fails."""

    status_code = 422
    code = ERROR_VALIDATION
    default_message = "Request validation failed."


class UnsupportedCurrencyError(AppException):
    """Raised when a currency is not supported."""

    status_code = 422
    code = ERROR_UNSUPPORTED_CURRENCY
    default_message = "The requested currency is not supported."


class RateNotFoundError(AppException):
    """Raised when the requested exchange rate is unavailable."""

    status_code = 404
    code = ERROR_RATE_NOT_FOUND
    default_message = "The requested exchange rate was not found."


class ProviderError(AppException):
    """Base exception for exchange-rate provider failures."""

    status_code = 502
    code = ERROR_PROVIDER_ERROR
    default_message = "The exchange-rate provider encountered an error."
    retryable = True


class ProviderTimeoutError(ProviderError):
    """Raised when the exchange-rate provider times out."""

    status_code = 504
    code = ERROR_PROVIDER_TIMEOUT
    default_message = "The exchange-rate provider timed out."


class ProviderUnavailableError(ProviderError):
    """Raised when the provider cannot be reached."""

    status_code = 502
    code = ERROR_PROVIDER_UNAVAILABLE
    default_message = "The exchange-rate provider is unavailable."


class ProviderInvalidResponseError(ProviderError):
    """Raised when the provider returns an invalid response."""

    status_code = 502
    code = ERROR_PROVIDER_INVALID_RESPONSE
    default_message = "The exchange-rate provider returned invalid data."
    retryable = False


class AuthenticationError(AppException):
    """Raised when authentication is missing or invalid."""

    status_code = 401
    code = ERROR_AUTHENTICATION
    default_message = "Authentication is required or invalid."


class AuthorizationError(AppException):
    """Raised when the caller lacks permission."""

    status_code = 403
    code = ERROR_AUTHORIZATION
    default_message = "You do not have permission to perform this operation."


class RateLimitExceededError(AppException):
    """Raised when a request rate limit is exceeded."""

    status_code = 429
    code = ERROR_RATE_LIMIT_EXCEEDED
    default_message = "The request rate limit has been exceeded."
    retryable = True


class QuotaExceededError(AppException):
    """Raised when an account has exhausted its usage quota."""

    status_code = 429
    code = ERROR_QUOTA_EXCEEDED
    default_message = "The usage quota has been exceeded."
    retryable = False
