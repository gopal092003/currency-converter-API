
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.exceptions import AuthenticationError, InvalidRequestError
from app.db.models import APIKey, Base
from app.modules.auth.service import APIKeyService


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    try:
        with Session(engine, expire_on_commit=False) as session:
            yield session
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture(autouse=True)
def test_pepper(monkeypatch):
    # Avoid dependence on the developer's real environment secret.
    monkeypatch.setattr(
        "app.core.security._pepper",
        lambda: b"integration-test-only-pepper",
    )


@pytest.fixture
def service(db_session):
    return APIKeyService(db_session)


def test_valid_key_authenticates_and_updates_last_used(service):
    record, raw_key = service.create_key(
        owner_id="account-1",
        name="Integration test key",
    )

    authenticated = service.authenticate(raw_key)

    assert authenticated.id == record.id
    assert authenticated.owner_id == "account-1"
    assert authenticated.last_used_at is not None


def test_wrong_key_is_rejected(service):
    service.create_key(
        owner_id="account-1",
        name="Expected key",
    )

    with pytest.raises(AuthenticationError):
        service.authenticate("cc_live_" + "x" * 40)


@pytest.mark.parametrize(
    "malformed_key",
    [
        "",
        "not-an-api-key",
        "cc_live_short",
        "cc_unknown_" + "x" * 40,
    ],
)
def test_malformed_key_is_rejected(service, malformed_key):
    with pytest.raises(AuthenticationError):
        service.authenticate(malformed_key)


def test_revoked_key_is_rejected(service):
    record, raw_key = service.create_key(
        owner_id="account-1",
        name="Revoked key",
    )

    service.revoke_key(
        key_id=record.id,
        owner_id="account-1",
    )

    with pytest.raises(AuthenticationError):
        service.authenticate(raw_key)


def test_expired_key_is_rejected(service):
    expired_at = datetime.now(timezone.utc) - timedelta(minutes=5)

    record, raw_key = service.create_key(
        owner_id="account-1",
        name="Expired key",
        expires_at=expired_at,
    )

    assert record.expires_at is not None

    with pytest.raises(AuthenticationError):
        service.authenticate(raw_key)


def test_rotation_invalidates_old_key(service):
    old_record, old_key = service.create_key(
        owner_id="account-1",
        name="Rotating key",
        monthly_quota=500,
    )

    new_record, new_key = service.rotate_key(
        key_id=old_record.id,
        owner_id="account-1",
    )

    assert new_record.id != old_record.id
    assert new_key != old_key
    assert new_record.owner_id == old_record.owner_id
    assert new_record.monthly_quota == 500

    with pytest.raises(AuthenticationError):
        service.authenticate(old_key)

    assert service.authenticate(new_key).id == new_record.id


def test_key_cannot_be_revoked_by_another_owner(service):
    record, raw_key = service.create_key(
        owner_id="account-1",
        name="Private key",
    )

    with pytest.raises(InvalidRequestError):
        service.revoke_key(
            key_id=record.id,
            owner_id="account-2",
        )

    # The failed ownership check must not revoke the original key.
    assert service.authenticate(raw_key).id == record.id


def test_revoked_key_cannot_be_rotated(service):
    record, _ = service.create_key(
        owner_id="account-1",
        name="Already revoked",
    )

    service.revoke_key(
        key_id=record.id,
        owner_id="account-1",
    )

    with pytest.raises(InvalidRequestError):
        service.rotate_key(
            key_id=record.id,
            owner_id="account-1",
        )


def test_key_hash_is_persisted_not_plaintext(db_session, service):
    record, raw_key = service.create_key(
        owner_id="account-1",
        name="Hash verification",
    )

    persisted = db_session.get(APIKey, record.id)

    assert persisted is not None
    assert persisted.key_hash != raw_key
    assert len(persisted.key_hash) == 64


def test_list_keys_returns_only_requested_owner(service):
    service.create_key(owner_id="account-1", name="First")
    service.create_key(owner_id="account-1", name="Second")
    service.create_key(owner_id="account-2", name="Other account")

    records = service.list_keys(owner_id="account-1")

    assert len(records) == 2
    assert all(record.owner_id == "account-1" for record in records)


def test_rotation_preserves_expiry_and_quota(service):
    expiry = datetime.now(timezone.utc) + timedelta(days=7)
    old_record, _ = service.create_key(
        owner_id="account-1",
        name="Limited key",
        monthly_quota=2000,
        expires_at=expiry,
    )

    new_record, _ = service.rotate_key(
        key_id=old_record.id,
        owner_id="account-1",
    )

    assert new_record.monthly_quota == 2000
    assert new_record.expires_at == old_record.expires_at
