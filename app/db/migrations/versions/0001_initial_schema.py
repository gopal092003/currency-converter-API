"""Create the initial Currency Converter API schema.

Revision ID: 0001_initial
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the initial tables and indexes."""

    op.create_table(
        "rate_sets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("base_currency", sa.String(length=3), nullable=False),
        sa.Column("rate_date", sa.Date(), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "provider",
            "base_currency",
            "rate_date",
            name="uq_rate_sets_provider_base_date",
        ),
    )

    op.create_index(
        "ix_rate_sets_base_date",
        "rate_sets",
        ["base_currency", "rate_date"],
    )

    op.create_table(
        "exchange_rates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "rate_set_id",
            sa.Integer(),
            sa.ForeignKey("rate_sets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_currency", sa.String(length=3), nullable=False),
        sa.Column("rate", sa.Numeric(precision=30, scale=15), nullable=False),
        sa.UniqueConstraint(
            "rate_set_id",
            "target_currency",
            name="uq_exchange_rates_set_target",
        ),
    )

    op.create_index(
        "ix_exchange_rates_target",
        "exchange_rates",
        ["target_currency"],
    )

    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key_prefix", sa.String(length=16), nullable=False),
        sa.Column("key_hash", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("owner_id", sa.String(length=128), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "last_used_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("monthly_quota", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("key_hash", name="uq_api_keys_key_hash"),
    )

    op.create_index(
        "ix_api_keys_owner_id",
        "api_keys",
        ["owner_id"],
    )
    op.create_index(
        "ix_api_keys_prefix_active",
        "api_keys",
        ["key_prefix", "is_active"],
    )

    op.create_table(
        "usage_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "api_key_id",
            sa.Integer(),
            sa.ForeignKey("api_keys.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("endpoint", sa.String(length=200), nullable=False),
        sa.Column("http_method", sa.String(length=10), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_usage_records_occurred_at",
        "usage_records",
        ["occurred_at"],
    )
    op.create_index(
        "ix_usage_records_api_key_occurred",
        "usage_records",
        ["api_key_id", "occurred_at"],
    )


def downgrade() -> None:
    """Drop the initial schema in dependency-safe order."""

    op.drop_index(
        "ix_usage_records_api_key_occurred",
        table_name="usage_records",
    )
    op.drop_index(
        "ix_usage_records_occurred_at",
        table_name="usage_records",
    )
    op.drop_table("usage_records")

    op.drop_index(
        "ix_api_keys_prefix_active",
        table_name="api_keys",
    )
    op.drop_index(
        "ix_api_keys_owner_id",
        table_name="api_keys",
    )
    op.drop_table("api_keys")

    op.drop_index(
        "ix_exchange_rates_target",
        table_name="exchange_rates",
    )
    op.drop_table("exchange_rates")

    op.drop_index(
        "ix_rate_sets_base_date",
        table_name="rate_sets",
    )
    op.drop_table("rate_sets")
