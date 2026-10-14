"""Decimal-safe monetary rounding utilities."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext

# ISO 4217 minor-unit digits for common currencies.
# Expand this registry or load it from a maintained currency metadata source.
CURRENCY_MINOR_UNITS: dict[str, int] = {
    "BHD": 3,
    "CLF": 4,
    "CLP": 0,
    "DJF": 0,
    "EUR": 2,
    "GBP": 2,
    "INR": 2,
    "ISK": 0,
    "JPY": 0,
    "KWD": 3,
    "KRW": 0,
    "OMR": 3,
    "TND": 3,
    "USD": 2,
}

DEFAULT_MINOR_UNITS = 2
DEFAULT_ROUNDING_MODE = ROUND_HALF_EVEN


def get_currency_precision(
    currency: str,
    *,
    default: int = DEFAULT_MINOR_UNITS,
) -> int:
    """Return the configured minor-unit precision for a currency."""
    code = currency.strip().upper()

    if not code.isalpha() or len(code) != 3:
        raise ValueError("Currency must be a three-letter code.")

    return CURRENCY_MINOR_UNITS.get(code, default)


def quantize_amount(
    amount: Decimal,
    currency: str,
    *,
    rounding: str = DEFAULT_ROUNDING_MODE,
    precision: int | None = None,
) -> Decimal:
    """Round an amount to the currency's minor-unit precision."""
    if not amount.is_finite():
        raise ValueError("Amount must be finite.")

    digits = (
        get_currency_precision(currency)
        if precision is None
        else precision
    )

    if digits < 0:
        raise ValueError("Precision cannot be negative.")

    quantum = Decimal(1).scaleb(-digits)

    try:
        with localcontext() as context:
            context.prec = max(
                context.prec,
                len(amount.as_tuple().digits) + abs(amount.as_tuple().exponent) + digits + 10,
            )
            return amount.quantize(quantum, rounding=rounding)
    except InvalidOperation as exc:
        raise ValueError("Amount cannot be represented at the requested precision.") from exc


def multiply_amount(
    amount: Decimal,
    rate: Decimal,
) -> Decimal:
    """Multiply an amount by a rate without converting to binary floats."""
    if not amount.is_finite():
        raise ValueError("Amount must be finite.")

    if not rate.is_finite() or rate <= 0:
        raise ValueError("Exchange rate must be finite and positive.")

    with localcontext() as context:
        context.prec = max(
            context.prec,
            len(amount.as_tuple().digits)
            + len(rate.as_tuple().digits)
            + 10,
        )
        result = amount * rate

    if not result.is_finite():
        raise ValueError("Conversion result is outside the supported numeric range.")

    return result


def convert_and_round(
    amount: Decimal,
    rate: Decimal,
    target_currency: str,
    *,
    rounding: str = DEFAULT_ROUNDING_MODE,
) -> Decimal:
    """Convert an amount and round the result to target-currency precision."""
    return quantize_amount(
        multiply_amount(amount, rate),
        target_currency,
        rounding=rounding,
    )
