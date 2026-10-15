"""ORM model for API usage records."""

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.models.api_key import APIKey

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base


class UsageRecord(Base):
    """One request-level usage event."""

    __tablename__ = "usage_records"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    api_key_id: Mapped[int | None] = mapped_column(
        ForeignKey("api_keys.id", ondelete="SET NULL"),
        nullable=True,
    )

    request_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    endpoint: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    http_method: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    status_code: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    api_key: Mapped["APIKey | None"] = relationship(
        back_populates="usage_records",
    )

    __table_args__ = (
        Index("ix_usage_records_occurred_at", "occurred_at"),
        Index("ix_usage_records_api_key_occurred", "api_key_id", "occurred_at"),
    )
