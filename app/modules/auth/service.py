from __future__ import annotations

from datetime import UTC, datetime

from app.core.exceptions import (
    AuthenticationError,
    InvalidRequestError,
)
from app.core.security import (
    generate_api_key,
    get_api_key_prefix,
    hash_api_key,
    is_valid_api_key_format,
    verify_api_key,
)
from app.db.models.api_key import APIKey
from app.modules.auth.repository import APIKeyRepository
from sqlalchemy.orm import Session


class APIKeyService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = APIKeyRepository(db)

    @staticmethod
    def _is_expired(record: APIKey) -> bool:
        if record.expires_at is None:
            return False

        expires_at = record.expires_at
        now = datetime.now(UTC)

        # SQLite may return naive datetimes even for timezone-aware columns.
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        return expires_at <= now

    def create_key(
        self,
        *,
        owner_id: str,
        name: str,
        monthly_quota: int | None = None,
        expires_at: datetime | None = None,
        environment: str = "live",
    ) -> tuple[APIKey, str]:
        owner_id = owner_id.strip()
        name = name.strip()

        if not owner_id:
            raise InvalidRequestError("owner_id cannot be empty")
        if not name:
            raise InvalidRequestError("API key name cannot be empty")

        raw_key = generate_api_key(environment=environment)

        try:
            record = self.repository.create(
                key_prefix=get_api_key_prefix(raw_key),
                key_hash=hash_api_key(raw_key),
                name=name,
                owner_id=owner_id,
                monthly_quota=monthly_quota,
                expires_at=expires_at,
            )
            self.db.commit()
            self.db.refresh(record)
        except Exception:
            self.db.rollback()
            raise

        return record, raw_key

    def authenticate(self, raw_key: str) -> APIKey:
        """Authenticate a key and update its last-used timestamp."""
        if not is_valid_api_key_format(raw_key):
            raise AuthenticationError("Invalid API key")

        try:
            prefix = get_api_key_prefix(raw_key)
            candidates = self.repository.get_candidates_by_prefix(prefix)

            # Prefixes are hints, not proof of identity. If a record is stored
            # with a non-matching or duplicate prefix, fall back to the full set
            # of active records to verify the hash instead of rejecting early.
            if not candidates:
                candidates = self.repository.list_active()

            matched: APIKey | None = None
            for candidate in candidates:
                valid_hash = verify_api_key(raw_key, candidate.key_hash)
                if valid_hash:
                    matched = candidate
                    break

            if matched is None:
                # Try the full active set as a final fallback for prefix drift or
                # collisions, then reject if the key still cannot be verified.
                for candidate in self.repository.list_active():
                    if verify_api_key(raw_key, candidate.key_hash):
                        matched = candidate
                        break

            if (
                matched is None
                or not matched.is_active
                or matched.revoked_at is not None
                or self._is_expired(matched)
            ):
                raise AuthenticationError("Invalid API key")

            self.repository.mark_used(matched)
            self.db.commit()
            self.db.refresh(matched)
            return matched
        except AuthenticationError:
            self.db.rollback()
            raise
        except Exception:
            self.db.rollback()
            raise

    def list_keys(self, *, owner_id: str) -> list[APIKey]:
        return self.repository.list_for_owner(owner_id)

    def revoke_key(
        self,
        *,
        key_id: int,
        owner_id: str,
    ) -> APIKey:
        record = self.repository.get_by_id_for_owner(key_id, owner_id)
        if record is None:
            # Avoid revealing whether a key belonging to another owner exists.
            raise InvalidRequestError("API key not found")

        if not record.is_active or record.revoked_at is not None:
            raise InvalidRequestError("API key is already revoked")

        try:
            self.repository.revoke(record)
            self.db.commit()
            self.db.refresh(record)
            return record
        except Exception:
            self.db.rollback()
            raise

    def rotate_key(
        self,
        *,
        key_id: int,
        owner_id: str,
    ) -> tuple[APIKey, str]:
        old_record = self.repository.get_by_id_for_owner(key_id, owner_id)
        if old_record is None:
            raise InvalidRequestError("API key not found")

        if (
            not old_record.is_active
            or old_record.revoked_at is not None
            or self._is_expired(old_record)
        ):
            raise InvalidRequestError("Only an active, unexpired key can be rotated")

        raw_key = generate_api_key()

        try:
            # Both changes are committed together. If creation fails, the
            # old key remains active after rollback.
            self.repository.revoke(old_record)
            new_record = self.repository.create(
                key_prefix=get_api_key_prefix(raw_key),
                key_hash=hash_api_key(raw_key),
                name=old_record.name,
                owner_id=old_record.owner_id,
                monthly_quota=old_record.monthly_quota,
                expires_at=old_record.expires_at,
            )
            self.db.commit()
            self.db.refresh(new_record)
        except Exception:
            self.db.rollback()
            raise

        return new_record, raw_key

    def revoke_all(self, *, owner_id: str) -> int:
        try:
            count = self.repository.revoke_all_for_owner(owner_id)
            self.db.commit()
            return count
        except Exception:
            self.db.rollback()
            raise
