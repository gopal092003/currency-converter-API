"""ORM model for API-key authentication."""

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.models.usage import UsageRecord

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin


class APIKey(TimestampMixin, Base):
    """An API credential issued to a customer or application."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    # Public identifier used to look up the key without scanning hashes.
    key_prefix: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )

    # Store a cryptographic digest, never the original API key.
    key_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    owner_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    monthly_quota: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    usage_records: Mapped[list["UsageRecord"]] = relationship(
        back_populates="api_key",
        passive_deletes=True,
    )

    __table_args__ = (Index("ix_api_keys_prefix_active", "key_prefix", "is_active"),)
