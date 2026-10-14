"""Factory for exchange-rate provider implementations."""

from typing import TYPE_CHECKING

import httpx

from app.core.config import settings
from app.modules.providers.exceptions import ProviderConfigurationError
from app.modules.providers.frankfurter import FrankfurterProvider

if TYPE_CHECKING:
    from app.modules.providers.base import ExchangeRateProvider


def create_provider(
    provider_name: str | None = None,
    *,
    client: httpx.AsyncClient | None = None,
) -> "ExchangeRateProvider":
    """Create the configured exchange-rate provider.

    Args:
        provider_name: Optional provider override. Defaults to application
            configuration.
        client: Optional shared HTTPX client managed by the application.

    Returns:
        An initialized exchange-rate provider.

    Raises:
        ProviderConfigurationError: If the provider is unsupported.
    """
    name = (provider_name or settings.exchange_provider).strip().lower()

    providers = {
        "frankfurter": FrankfurterProvider,
    }

    provider_class = providers.get(name)

    if provider_class is None:
        supported = ", ".join(sorted(providers))
        raise ProviderConfigurationError(
            f"Unsupported exchange-rate provider '{name}'. "
            f"Supported providers: {supported}."
        )

    return provider_class(client=client)
