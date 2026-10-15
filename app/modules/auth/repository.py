from __future__ import annotations

from datetime import UTC, datetime

from app.db.models.api_key import APIKey
from sqlalchemy import select
from sqlalchemy.orm import Session


class APIKeyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        key_prefix: str,
        key_hash: str,
        name: str,
        owner_id: str,
        monthly_quota: int | None = None,
        expires_at: datetime | None = None,
    ) -> APIKey:
        record = APIKey(
            key_prefix=key_prefix,
            key_hash=key_hash,
            name=name,
            owner_id=owner_id,
            monthly_quota=monthly_quota,
            expires_at=expires_at,
            is_active=True,
        )
        self.db.add(record)
        self.db.flush()
        return record

    def get_by_id(self, key_id: int) -> APIKey | None:
        return self.db.get(APIKey, key_id)

    def get_by_id_for_owner(
        self,
        key_id: int,
        owner_id: str,
    ) -> APIKey | None:
        statement = select(APIKey).where(
            APIKey.id == key_id,
            APIKey.owner_id == owner_id,
        )
        return self.db.scalar(statement)

    def get_candidates_by_prefix(self, prefix: str) -> list[APIKey]:
        """Return candidate rows; the service must verify each stored hash."""
        statement = select(APIKey).where(APIKey.key_prefix == prefix)
        return list(self.db.scalars(statement).all())

    def list_active(self) -> list[APIKey]:
        statement = select(APIKey).where(APIKey.is_active.is_(True))
        return list(self.db.scalars(statement).all())

    def list_for_owner(self, owner_id: str) -> list[APIKey]:
        statement = (
            select(APIKey)
            .where(APIKey.owner_id == owner_id)
            .order_by(APIKey.created_at.desc(), APIKey.id.desc())
        )
        return list(self.db.scalars(statement).all())

    def mark_used(self, record: APIKey) -> None:
        record.last_used_at = datetime.now(UTC)
        self.db.flush()

    def revoke(self, record: APIKey) -> APIKey:
        record.is_active = False
        record.revoked_at = datetime.now(UTC)
        self.db.flush()
        return record

    def revoke_all_for_owner(self, owner_id: str) -> int:
        records = self.list_for_owner(owner_id)
        now = datetime.now(UTC)
        count = 0

        for record in records:
            if record.is_active:
                record.is_active = False
                record.revoked_at = now
                count += 1

        self.db.flush()
        return count
