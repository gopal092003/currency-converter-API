"""Schemas for exchange-rate data and API responses."""

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

CurrencyCode = Annotated[
    str,
    Field(
        min_length=3,
        max_length=3,
        pattern=r"^[A-Z]{3}$",
        description="Three-letter uppercase currency code.",
        examples=["EUR", "USD", "INR"],
    ),
]

PositiveRate = Annotated[
    Decimal,
    Field(
        gt=Decimal("0"),
        max_digits=30,
        decimal_places=15,
        description="Positive exchange rate.",
    ),
]


class RateData(BaseModel):
    """Normalized exchange rates for a single base currency and date."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    base: CurrencyCode
    rate_date: date = Field(description="Date the rates apply to.")
    rates: dict[CurrencyCode, PositiveRate]

    @field_validator("base", mode="before")
    @classmethod
    def normalize_base(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @field_validator("rates", mode="before")
    @classmethod
    def normalize_rate_codes(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value

        normalized: dict[str, object] = {}
        for code, rate in value.items():
            if not isinstance(code, str):
                raise ValueError("Currency codes must be strings.")

            normalized_code = code.strip().upper()
            if normalized_code in normalized:
                raise ValueError(
                    f"Duplicate currency code after normalization: {normalized_code}"
                )
            normalized[normalized_code] = rate

        return normalized

    @model_validator(mode="after")
    def validate_base_not_in_rates(self) -> "RateData":
        if self.base in self.rates:
            raise ValueError("The base currency must not appear in the rates mapping.")
        return self


class RateQuery(BaseModel):
    """Validated input for retrieving rates."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    base: CurrencyCode = "EUR"
    symbols: list[CurrencyCode] | None = None

    @field_validator("base", mode="before")
    @classmethod
    def normalize_base(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @field_validator("symbols", mode="before")
    @classmethod
    def normalize_symbols(cls, value: object) -> object:
        if value is None:
            return None

        if not isinstance(value, list):
            raise ValueError("symbols must be a list of currency codes.")

        normalized: list[str] = []
        seen: set[str] = set()

        for item in value:
            if not isinstance(item, str):
                raise ValueError("Currency codes must be strings.")

            code = item.strip().upper()
            if code in seen:
                continue

            seen.add(code)
            normalized.append(code)

        return normalized


class RateResponse(BaseModel):
    """API response for latest or historical exchange rates."""

    model_config = ConfigDict(extra="forbid")

    success: bool = True
    data: RateData


class TimeSeriesRateData(BaseModel):
    """Normalized exchange rates across a date range."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    base: CurrencyCode
    start_date: date
    end_date: date
    rates: dict[date, dict[CurrencyCode, PositiveRate]]

    @model_validator(mode="after")
    def validate_date_range(self) -> "TimeSeriesRateData":
        if self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date.")

        for rate_date, daily_rates in self.rates.items():
            if not self.start_date <= rate_date <= self.end_date:
                raise ValueError(
                    f"Rate date {rate_date} is outside the requested range."
                )

            if self.base in daily_rates:
                raise ValueError(
                    f"Base currency {self.base} must not appear "
                    f"in rates for {rate_date}."
                )

        return self


class TimeSeriesRateResponse(BaseModel):
    """API response for a range of exchange rates."""

    model_config = ConfigDict(extra="forbid")

    success: bool = True
    data: TimeSeriesRateData


class RateMetadata(BaseModel):
    """Metadata describing the source and freshness of rate data."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    fetched_at: date | None = None
    is_stale: bool = False
