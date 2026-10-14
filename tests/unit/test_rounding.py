
"""Unit tests for currency precision and rounding."""

from decimal import Decimal, ROUND_HALF_UP

import pytest

from app.modules.currency.rounding import (
    convert_and_round,
    get_currency_precision,
    multiply_amount,
    quantize_amount,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("currency", "expected"),
    [
        ("USD", 2),
        ("EUR", 2),
        ("INR", 2),
        ("JPY", 0),
        ("CLP", 0),
        ("KWD", 3),
        ("BHD", 3),
        ("CLF", 4),
    ],
)
def test_get_currency_precision(currency, expected):
    assert get_currency_precision(currency) == expected


@pytest.mark.unit
def test_unknown_currency_uses_default_precision():
    assert get_currency_precision("XYZ") == 2


@pytest.mark.unit
@pytest.mark.parametrize(
    ("amount", "currency", "expected"),
    [
        ("12.345", "USD", "12.34"),
        ("12.355", "USD", "12.36"),
        ("12.5", "JPY", "12"),
        ("12.9", "JPY", "13"),
        ("1.23456", "KWD", "1.235"),
        ("0", "INR", "0.00"),
    ],
)
def test_quantize_amount_half_even(amount, currency, expected):
    result = quantize_amount(Decimal(amount), currency)
    assert result == Decimal(expected)


@pytest.mark.unit
def test_quantize_amount_supports_explicit_rounding_mode():
    result = quantize_amount(
        Decimal("12.345"),
        "USD",
        rounding=ROUND_HALF_UP,
    )
    assert result == Decimal("12.35")


@pytest.mark.unit
def test_quantize_amount_supports_explicit_precision():
    result = quantize_amount(
        Decimal("1.234567"),
        "USD",
        precision=4,
    )
    assert result == Decimal("1.2346")


@pytest.mark.unit
@pytest.mark.parametrize(
    "amount",
    [
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
    ],
)
def test_quantize_rejects_non_finite_amount(amount):
    with pytest.raises(ValueError):
        quantize_amount(amount, "USD")


@pytest.mark.unit
def test_quantize_rejects_negative_precision():
    with pytest.raises(ValueError):
        quantize_amount(
            Decimal("1.23"),
            "USD",
            precision=-1,
        )


@pytest.mark.unit
def test_multiply_amount_uses_decimal_arithmetic():
    assert multiply_amount(
        Decimal("0.1"),
        Decimal("0.2"),
    ) == Decimal("0.02")


@pytest.mark.unit
def test_multiply_rejects_non_positive_rate():
    with pytest.raises(ValueError):
        multiply_amount(
            Decimal("10"),
            Decimal("0"),
        )

    with pytest.raises(ValueError):
        multiply_amount(
            Decimal("10"),
            Decimal("-1"),
        )


@pytest.mark.unit
def test_convert_and_round():
    result = convert_and_round(
        amount=Decimal("100"),
        rate=Decimal("83.456"),
        target_currency="INR",
    )
    assert result == Decimal("8345.60")


@pytest.mark.unit
def test_convert_and_round_to_zero_decimal_currency():
    result = convert_and_round(
        amount=Decimal("10"),
        rate=Decimal("1.25"),
        target_currency="JPY",
    )
    assert result == Decimal("12")
