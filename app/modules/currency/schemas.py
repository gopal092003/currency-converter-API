"""Pydantic schemas for currency conversion."""

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

CurrencyCode = Annotated[
    str,
    Field(
        min_length=3,
        max_length=3,
        pattern=r"^[A-Z]{3}$",
        description="Three-letter uppercase currency code.",
        examples=["USD", "INR", "EUR"],
    ),
]

Amount = Annotated[
    Decimal,
    Field(
        ge=Decimal("0"),
        max_digits=30,
        decimal_places=10,
        description="Non-negative monetary amount.",
        examples=["100.00"],
    ),
]


class CurrencyMetadata(BaseModel):
    """Metadata describing a supported currency."""

    model_config = ConfigDict(extra="forbid")

    code: CurrencyCode
    name: str | None = None
    symbol: str | None = None
    minor_units: int = Field(default=2, ge=0, le=6)


class ConversionRequest(BaseModel):
    """Input parameters for a currency conversion."""

    model_config = ConfigDict(extra="forbid")

    amount: Amount
    from_currency: CurrencyCode = Field(
        description="Currency to convert from.",
        examples=["USD"],
    )
    to_currency: CurrencyCode = Field(
        description="Currency to convert to.",
        examples=["INR"],
    )

    @field_validator("from_currency", "to_currency", mode="before")
    @classmethod
    def normalize_currency_code(cls, value: object) -> object:
        """Normalize currency codes before validating them."""
        if isinstance(value, str):
            return value.strip().upper()
        return value


class ConversionResult(BaseModel):
    """Result of a successful currency conversion."""

    model_config = ConfigDict(extra="forbid")

    amount: Decimal = Field(ge=Decimal("0"))
    from_currency: CurrencyCode
    to_currency: CurrencyCode
    exchange_rate: Decimal = Field(gt=Decimal("0"))
    converted_amount: Decimal = Field(ge=Decimal("0"))
    rate_date: date | None = None


class ConversionResponse(BaseModel):
    """Public response schema for a conversion request."""

    model_config = ConfigDict(extra="forbid")

    success: bool = True
    data: ConversionResult


class SupportedCurrenciesResponse(BaseModel):
    """Response containing supported currency metadata."""

    model_config = ConfigDict(extra="forbid")

    success: bool = True
    currencies: list[CurrencyMetadata]
    count: int = Field(ge=0)
