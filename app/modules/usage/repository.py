from __future__ import annotations

from datetime import UTC, datetime

from app.db.models.usage import UsageRecord
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session


class UsageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        api_key_id: int | None,
        request_id: str | None,
        endpoint: str,
        http_method: str,
        status_code: int,
        duration_ms: float,
        occurred_at: datetime | None = None,
    ) -> UsageRecord:
        record = UsageRecord(
            api_key_id=api_key_id,
            request_id=request_id,
            endpoint=endpoint,
            http_method=http_method.upper(),
            status_code=status_code,
            duration_ms=duration_ms,
            occurred_at=occurred_at or datetime.now(UTC),
        )
        self.db.add(record)
        self.db.flush()
        return record

    def get_by_id(self, usage_id: int) -> UsageRecord | None:
        return self.db.get(UsageRecord, usage_id)

    def list_for_api_key(
        self,
        *,
        api_key_id: int,
        limit: int = 100,
        offset: int = 0,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[UsageRecord]:
        statement = select(UsageRecord).where(UsageRecord.api_key_id == api_key_id)

        if start is not None:
            statement = statement.where(UsageRecord.occurred_at >= start)
        if end is not None:
            statement = statement.where(UsageRecord.occurred_at < end)

        statement = (
            statement.order_by(
                UsageRecord.occurred_at.desc(),
                UsageRecord.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def count_for_period(
        self,
        *,
        api_key_id: int,
        start: datetime,
        end: datetime,
    ) -> int:
        statement = (
            select(func.count())
            .select_from(UsageRecord)
            .where(
                UsageRecord.api_key_id == api_key_id,
                UsageRecord.occurred_at >= start,
                UsageRecord.occurred_at < end,
            )
        )
        return int(self.db.scalar(statement) or 0)

    def summarize_for_period(
        self,
        *,
        api_key_id: int,
        start: datetime,
        end: datetime,
    ) -> dict[str, int | float]:
        statement = select(
            func.count(UsageRecord.id).label("request_count"),
            func.coalesce(
                func.sum(
                    case(
                        (UsageRecord.status_code < 400, 1),
                        else_=0,
                    )
                ),
                0,
            ).label("successful_requests"),
            func.coalesce(
                func.sum(
                    case(
                        (UsageRecord.status_code >= 400, 1),
                        else_=0,
                    )
                ),
                0,
            ).label("failed_requests"),
            func.coalesce(
                func.sum(UsageRecord.duration_ms),
                0,
            ).label("total_duration_ms"),
        ).where(
            UsageRecord.api_key_id == api_key_id,
            UsageRecord.occurred_at >= start,
            UsageRecord.occurred_at < end,
        )

        row = self.db.execute(statement).one()

        return {
            "request_count": int(row.request_count or 0),
            "successful_requests": int(row.successful_requests or 0),
            "failed_requests": int(row.failed_requests or 0),
            "total_duration_ms": float(row.total_duration_ms or 0),
        }

    def delete_before(self, cutoff: datetime) -> int:
        """Delete old records according to a retention policy."""
        from sqlalchemy import delete

        result = self.db.execute(
            delete(UsageRecord).where(UsageRecord.occurred_at < cutoff)
        )
        self.db.flush()
        return int(result.rowcount or 0)
