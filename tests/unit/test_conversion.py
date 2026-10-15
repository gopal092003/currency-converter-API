"""Unit tests for the currency conversion service."""

from datetime import date
from decimal import Decimal

import pytest
from app.core.exceptions import ProviderError, UnsupportedCurrencyError
from app.modules.currency.schemas import ConversionRequest
from app.modules.currency.service import CurrencyConversionService


@pytest.mark.unit
@pytest.mark.asyncio
async def test_convert_eur_to_usd(fake_provider):
    service = CurrencyConversionService(fake_provider)

    request = ConversionRequest(
        amount=Decimal("100"),
        from_currency="EUR",
        to_currency="USD",
    )

    result = await service.convert(request)

    assert result.amount == Decimal("100")
    assert result.from_currency == "EUR"
    assert result.to_currency == "USD"
    assert result.exchange_rate == Decimal("1.17")
    assert result.converted_amount == Decimal("117.00")
    assert isinstance(result.rate_date, date)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_convert_usd_to_inr(fake_provider):
    service = CurrencyConversionService(fake_provider)

    request = ConversionRequest(
        amount=Decimal("100"),
        from_currency="USD",
        to_currency="INR",
    )

    result = await service.convert(request)

    assert result.exchange_rate == Decimal("88.46153846153846")
    assert result.converted_amount == Decimal("8846.15")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_convert_same_currency_does_not_need_provider(
    fake_provider,
):
    service = CurrencyConversionService(fake_provider)

    request = ConversionRequest(
        amount=Decimal("25.50"),
        from_currency="INR",
        to_currency="INR",
    )

    result = await service.convert(request)

    assert result.exchange_rate == Decimal("1")
    assert result.converted_amount == Decimal("25.50")
    assert result.rate_date is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_convert_zero_amount(fake_provider):
    service = CurrencyConversionService(fake_provider)

    request = ConversionRequest(
        amount=Decimal("0"),
        from_currency="EUR",
        to_currency="USD",
    )

    result = await service.convert(request)

    assert result.converted_amount == Decimal("0.00")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_convert_unsupported_target_currency(fake_provider):
    service = CurrencyConversionService(fake_provider)

    request = ConversionRequest(
        amount=Decimal("10"),
        from_currency="EUR",
        to_currency="ZZZ",
    )

    with pytest.raises((UnsupportedCurrencyError, ProviderError)):
        await service.convert(request)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_convert_provider_failure_is_propagated(fake_provider):
    async def fail_latest_rates(*args, **kwargs):
        raise ProviderError(
            "Provider unavailable.",
            retryable=True,
        )

    fake_provider.get_latest_rates = fail_latest_rates
    service = CurrencyConversionService(fake_provider)

    request = ConversionRequest(
        amount=Decimal("10"),
        from_currency="EUR",
        to_currency="USD",
    )

    with pytest.raises(ProviderError):
        await service.convert(request)


@pytest.mark.unit
def test_conversion_request_normalizes_currency_codes():
    request = ConversionRequest(
        amount=Decimal("10"),
        from_currency=" usd ",
        to_currency=" inr ",
    )

    assert request.from_currency == "USD"
    assert request.to_currency == "INR"
