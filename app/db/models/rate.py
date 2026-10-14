
"""ORM models for exchange-rate persistence."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin


class RateSet(TimestampMixin, Base):
    """One provider's rate snapshot for a base currency and effective date."""

    __tablename__ = "rate_sets"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    base_currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    rate_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    rates: Mapped[list["ExchangeRate"]] = relationship(
        back_populates="rate_set",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ExchangeRate.target_currency",
    )

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "base_currency",
            "rate_date",
            name="uq_rate_sets_provider_base_date",
        ),
        Index(
            "ix_rate_sets_base_date",
            "base_currency",
            "rate_date",
        ),
    )


class ExchangeRate(Base):
    """An individual target-currency rate belonging to a rate snapshot."""

    __tablename__ = "exchange_rates"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    rate_set_id: Mapped[int] = mapped_column(
        ForeignKey("rate_sets.id", ondelete="CASCADE"),
        nullable=False,
    )

    target_currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    rate: Mapped[Decimal] = mapped_column(
        Numeric(30, 15),
        nullable=False,
    )

    rate_set: Mapped[RateSet] = relationship(
        back_populates="rates",
    )

    __table_args__ = (
        UniqueConstraint(
            "rate_set_id",
            "target_currency",
            name="uq_exchange_rates_set_target",
        ),
        Index(
            "ix_exchange_rates_target",
            "target_currency",
        ),
    )
