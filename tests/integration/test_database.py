from __future__ import annotations

import pytest
from app.core.security import hash_api_key
from app.db.models import APIKey, Base
from app.modules.auth.service import APIKeyService
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


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
def configure_test_pepper(monkeypatch):
    # Adapt the attribute if your Settings object uses a different name.
    monkeypatch.setattr(
        "app.core.security.settings.api_key_pepper",
        "test-only-pepper-for-integration-tests",
    )


def test_create_key_persists_only_hash(db_session):
    service = APIKeyService(db_session)

    record, raw_key = service.create_key(
        owner_id="test-owner",
        name="Integration test key",
    )

    persisted = db_session.get(APIKey, record.id)

    assert persisted is not None
    assert persisted.key_hash == hash_api_key(raw_key)
    assert persisted.key_hash != raw_key
    assert persisted.key_prefix
    assert persisted.is_active is True
    assert persisted.owner_id == "test-owner"


def test_authenticate_updates_last_used_at(db_session):
    service = APIKeyService(db_session)
    record, raw_key = service.create_key(
        owner_id="test-owner",
        name="Authentication test",
    )

    authenticated = service.authenticate(raw_key)

    assert authenticated.id == record.id
    assert authenticated.last_used_at is not None


def test_revoked_key_cannot_authenticate(db_session):
    service = APIKeyService(db_session)
    record, raw_key = service.create_key(
        owner_id="test-owner",
        name="Revocation test",
    )

    service.revoke_key(key_id=record.id, owner_id="test-owner")

    from app.core.exceptions import AuthenticationError

    with pytest.raises(AuthenticationError):
        service.authenticate(raw_key)


def test_owner_cannot_manage_another_owners_key(db_session):
    service = APIKeyService(db_session)
    record, _ = service.create_key(
        owner_id="owner-a",
        name="Owner A key",
    )

    from app.core.exceptions import InvalidRequestError

    with pytest.raises(InvalidRequestError):
        service.revoke_key(key_id=record.id, owner_id="owner-b")


def test_rotation_revokes_old_key_and_creates_new_key(db_session):
    service = APIKeyService(db_session)
    old_record, old_raw_key = service.create_key(
        owner_id="test-owner",
        name="Rotation test",
        monthly_quota=1000,
    )

    new_record, new_raw_key = service.rotate_key(
        key_id=old_record.id,
        owner_id="test-owner",
    )

    assert new_record.id != old_record.id
    assert new_record.owner_id == old_record.owner_id
    assert new_record.monthly_quota == old_record.monthly_quota
    assert new_raw_key != old_raw_key

    old_persisted = db_session.get(APIKey, old_record.id)
    assert old_persisted is not None
    assert old_persisted.is_active is False
    assert old_persisted.revoked_at is not None

    from app.core.exceptions import AuthenticationError

    with pytest.raises(AuthenticationError):
        service.authenticate(old_raw_key)

    authenticated_new = service.authenticate(new_raw_key)
    assert authenticated_new.id == new_record.id


def test_list_keys_is_scoped_to_owner(db_session):
    service = APIKeyService(db_session)
    service.create_key(owner_id="owner-a", name="A key")
    service.create_key(owner_id="owner-b", name="B key")

    owner_a_keys = service.list_keys(owner_id="owner-a")

    assert len(owner_a_keys) == 1
    assert all(record.owner_id == "owner-a" for record in owner_a_keys)


def test_duplicate_key_prefixes_do_not_authenticate_wrong_key(db_session):
    service = APIKeyService(db_session)
    first, first_raw = service.create_key(
        owner_id="owner-a",
        name="First key",
    )
    second, second_raw = service.create_key(
        owner_id="owner-b",
        name="Second key",
    )

    # Explicitly force a shared lookup prefix to exercise hash verification.
    shared_prefix = first.key_prefix
    second.key_prefix = shared_prefix
    db_session.commit()

    assert service.authenticate(first_raw).id == first.id
    assert service.authenticate(second_raw).id == second.id


def test_database_has_no_plaintext_api_key_column(db_session):
    columns = {column.name for column in APIKey.__table__.columns}

    assert "key_hash" in columns
    assert "key" not in columns
    assert "raw_key" not in columns

    stored_hashes = db_session.scalars(select(APIKey.key_hash)).all()
    assert all(len(value) == 64 for value in stored_hashes) or not stored_hashes
