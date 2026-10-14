
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import QuotaExceededError
from app.db.models.api_key import APIKey
from app.modules.usage.repository import UsageRepository
from app.modules.usage.schemas import (
    QuotaStatus,
    UsageRecordCreate,
    UsageRecordResponse,
    UsageSummary,
)


def current_utc_month(
    now: datetime | None = None,
) -> tuple[datetime, datetime]:
    current = now or datetime.now(timezone.utc)

    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    else:
        current = current.astimezone(timezone.utc)

    start = current.replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)

    return start, end


class UsageService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = UsageRepository(db)

    def record_request(
        self,
        payload: UsageRecordCreate,
    ) -> UsageRecordResponse:
        """Persist a completed request within the caller's transaction."""
        record = self.repository.create(
            api_key_id=payload.api_key_id,
            request_id=payload.request_id,
            endpoint=payload.endpoint,
            http_method=payload.http_method,
            status_code=payload.status_code,
            duration_ms=payload.duration_ms,
        )
        return UsageRecordResponse.model_validate(record)

    def get_monthly_usage(
        self,
        *,
        api_key: APIKey,
        now: datetime | None = None,
    ) -> UsageSummary:
        start, end = current_utc_month(now)
        totals = self.repository.summarize_for_period(
            api_key_id=api_key.id,
            start=start,
            end=end,
        )

        quota = api_key.monthly_quota
        used = int(totals["request_count"])

        return UsageSummary(
            period_start=start,
            period_end=end,
            request_count=used,
            successful_requests=int(totals["successful_requests"]),
            failed_requests=int(totals["failed_requests"]),
            total_duration_ms=float(totals["total_duration_ms"]),
            monthly_quota=quota,
            remaining_quota=(
                max(0, quota - used) if quota is not None else None
            ),
        )

    def get_quota_status(
        self,
        *,
        api_key: APIKey,
        now: datetime | None = None,
    ) -> QuotaStatus:
        start, end = current_utc_month(now)
        used = self.repository.count_for_period(
            api_key_id=api_key.id,
            start=start,
            end=end,
        )
        quota = api_key.monthly_quota

        return QuotaStatus(
            quota=quota,
            used=used,
            remaining=(
                max(0, quota - used) if quota is not None else None
            ),
            exceeded=quota is not None and used >= quota,
            period_start=start,
            period_end=end,
        )

    def enforce_monthly_quota(
        self,
        *,
        api_key: APIKey,
        now: datetime | None = None,
    ) -> QuotaStatus:
        """Raise if the key has already exhausted its monthly allowance."""
        status = self.get_quota_status(api_key=api_key, now=now)

        if status.exceeded:
            raise QuotaExceededError(
                message="Monthly API quota exceeded",
                details={
                    "quota": status.quota,
                    "used": status.used,
                    "period_start": status.period_start.isoformat(),
                    "period_end": status.period_end.isoformat(),
                },
            )

        return status
