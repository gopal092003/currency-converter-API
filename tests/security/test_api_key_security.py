
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.exceptions import AuthenticationError, InvalidRequestError
from app.core.security import (
    generate_api_key,
    get_api_key_prefix,
    hash_api_key,
    is_valid_api_key_format,
    verify_api_key,
)
from app.db.models import APIKey, Base
from app.modules.auth.schemas import APIKeyPublic
from app.modules.auth.service import APIKeyService


TEST_PEPPER = b"test-only-secret-pepper"


@pytest.fixture(autouse=True)
def patch_pepper(monkeypatch):
    monkeypatch.setattr(
        "app.core.security._pepper",
        lambda: TEST_PEPPER,
    )


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


@pytest.fixture
def service(db_session):
    return APIKeyService(db_session)


def test_generated_key_has_expected_format():
    key = generate_api_key()

    assert is_valid_api_key_format(key)
    assert key.startswith("cc_live_")


def test_test_environment_key_has_test_prefix():
    key = generate_api_key(environment="test")

    assert key.startswith("cc_test_")
    assert is_valid_api_key_format(key)


def test_invalid_environment_is_rejected():
    with pytest.raises(ValueError):
        generate_api_key(environment="production")


@pytest.mark.parametrize(
    "key",
    [
        "",
        "random-string",
        "cc_live_short",
        "cc_live_" + "a" * 10,
        "cc_admin_" + "a" * 40,
        "cc_live_" + "!" * 40,
    ],
)
def test_malformed_keys_fail_format_validation(key):
    assert is_valid_api_key_format(key) is False


def test_hash_is_deterministic_and_not_plaintext():
    key = generate_api_key()

    digest_a = hash_api_key(key)
    digest_b = hash_api_key(key)

    assert digest_a == digest_b
    assert digest_a != key
    assert len(digest_a) == 64


def test_hash_depends_on_pepper(monkeypatch):
    key = generate_api_key()
    original_hash = hash_api_key(key)

    monkeypatch.setattr(
        "app.core.security._pepper",
        lambda: b"a-different-test-pepper",
    )

    assert hash_api_key(key) != original_hash


def test_verification_accepts_correct_key():
    key = generate_api_key()
    stored_hash = hash_api_key(key)

    assert verify_api_key(key, stored_hash) is True


def test_verification_rejects_wrong_key():
    first = generate_api_key()
    second = generate_api_key()

    assert verify_api_key(second, hash_api_key(first)) is False


def test_verification_rejects_malformed_key():
    assert verify_api_key("not-a-key", "0" * 64) is False


def test_prefix_is_derived_from_key():
    key = generate_api_key()

    prefix = get_api_key_prefix(key)

    assert key.startswith(prefix)
    assert len(prefix) == 12


def test_prefix_rejects_malformed_key():
    with pytest.raises(ValueError):
        get_api_key_prefix("malformed")


def test_unknown_key_cannot_authenticate(service):
    with pytest.raises(AuthenticationError):
        service.authenticate(generate_api_key())


def test_revocation_prevents_future_authentication(service):
    record, key = service.create_key(
        owner_id="security-test-owner",
        name="Revocation test",
    )

    service.revoke_key(
        key_id=record.id,
        owner_id="security-test-owner",
    )

    with pytest.raises(AuthenticationError):
        service.authenticate(key)


def test_expired_key_cannot_authenticate(service):
    record, key = service.create_key(
        owner_id="security-test-owner",
        name="Expiry test",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )

    assert record.id is not None

    with pytest.raises(AuthenticationError):
        service.authenticate(key)


def test_rotation_invalidates_old_key(service):
    record, old_key = service.create_key(
        owner_id="security-test-owner",
        name="Rotation test",
    )

    new_record, new_key = service.rotate_key(
        key_id=record.id,
        owner_id="security-test-owner",
    )

    assert new_key != old_key

    with pytest.raises(AuthenticationError):
        service.authenticate(old_key)

    assert service.authenticate(new_key).id == new_record.id


def test_other_owner_cannot_revoke_key(service):
    record, key = service.create_key(
        owner_id="owner-a",
        name="Owner A key",
    )

    with pytest.raises(InvalidRequestError):
        service.revoke_key(
            key_id=record.id,
            owner_id="owner-b",
        )

    # A failed ownership check must leave the key usable.
    assert service.authenticate(key).id == record.id


def test_public_schema_does_not_expose_hash_or_raw_key(service):
    record, raw_key = service.create_key(
        owner_id="security-test-owner",
        name="Response leak test",
    )

    public = APIKeyPublic.model_validate(record)
    serialized = public.model_dump_json()

    assert "key_hash" not in public.model_fields
    assert "raw_key" not in public.model_fields
    assert raw_key not in serialized
    assert record.key_hash not in serialized


def test_creation_response_is_the_only_place_raw_key_is_returned(service):
    from app.modules.auth.schemas import APIKeyCreatedResponse

    record, raw_key = service.create_key(
        owner_id="security-test-owner",
        name="One-time secret test",
    )

    response = APIKeyCreatedResponse(
        data=APIKeyPublic.model_validate(record),
        api_key=raw_key,
    )

    serialized = response.model_dump_json()

    assert raw_key in serialized
    assert record.key_hash not in serialized


def test_raw_key_is_not_a_database_model_column():
    column_names = set(APIKey.__table__.columns.keys())

    assert "key_hash" in column_names
    assert "raw_key" not in column_names
    assert "secret" not in column_names


def test_public_schema_rejects_unexpected_fields():
    with pytest.raises(ValidationError):
        APIKeyPublic.model_validate(
            {
                "id": 1,
                "key_prefix": "cc_live_abc",
                "name": "test",
                "owner_id": "owner-a",
                "is_active": True,
                "key_hash": "sensitive-value",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        )
