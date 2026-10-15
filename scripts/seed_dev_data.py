from __future__ import annotations

import sys
from datetime import UTC, date, datetime
from decimal import Decimal

from app.core.config import settings
from app.core.security import generate_api_key, get_api_key_prefix, hash_api_key
from app.db.models import APIKey, ExchangeRate, RateSet
from app.db.session import SessionLocal
from sqlalchemy import select

DEVELOPMENT_OWNER_ID = "local-dev"
DEVELOPMENT_KEY_NAME = "Local development key"

# Illustrative values for local development only. Never use these as
# production exchange rates or financial data.
SAMPLE_RATES: dict[str, dict[str, str]] = {
    "EUR": {
        "USD": "1.08000",
        "GBP": "0.85000",
        "INR": "90.00000",
        "JPY": "160.00000",
    },
    "USD": {
        "EUR": "0.92593",
        "GBP": "0.78704",
        "INR": "83.33333",
        "JPY": "148.14815",
    },
    "INR": {
        "EUR": "0.01111",
        "USD": "0.01200",
        "GBP": "0.00944",
        "JPY": "1.77778",
    },
}


def seed_rates(session) -> int:
    """Insert missing sample rate sets; preserve existing data."""
    seeded = 0
    today = date.today()

    for base_currency, rates in SAMPLE_RATES.items():
        existing = session.scalar(
            select(RateSet).where(
                RateSet.provider == "development-seed",
                RateSet.base_currency == base_currency,
                RateSet.rate_date == today,
            )
        )

        if existing is not None:
            continue

        rate_set = RateSet(
            provider="development-seed",
            base_currency=base_currency,
            rate_date=today,
            fetched_at=datetime.now(UTC),
        )
        session.add(rate_set)
        session.flush()

        for target_currency, value in rates.items():
            session.add(
                ExchangeRate(
                    rate_set_id=rate_set.id,
                    target_currency=target_currency,
                    rate=Decimal(value),
                )
            )

        seeded += 1

    return seeded


def seed_api_key(session) -> str | None:
    """Create one development key if none already exists for this owner."""
    existing = session.scalar(
        select(APIKey).where(
            APIKey.owner_id == DEVELOPMENT_OWNER_ID,
            APIKey.name == DEVELOPMENT_KEY_NAME,
            APIKey.is_active.is_(True),
        )
    )

    if existing is not None:
        print(
            "An active development key already exists. "
            "Its secret cannot be recovered from the database."
        )
        print(f"Key record ID: {existing.id}")
        print(f"Key prefix: {existing.key_prefix}")
        print("Create a new key through the API if the secret is needed.")
        return None

    raw_key = generate_api_key(environment="test")
    record = APIKey(
        key_prefix=get_api_key_prefix(raw_key),
        key_hash=hash_api_key(raw_key),
        name=DEVELOPMENT_KEY_NAME,
        owner_id=DEVELOPMENT_OWNER_ID,
        is_active=True,
    )
    session.add(record)
    session.flush()
    return raw_key


def main() -> int:
    if settings.app_env not in {"development", "testing"}:
        print(
            "Refusing to seed data: APP_ENV must be development or testing.",
            file=sys.stderr,
        )
        return 1

    if SessionLocal is None:
        print(
            "Database is not configured. Set DATABASE_URL first.",
            file=sys.stderr,
        )
        return 1

    session = SessionLocal()

    try:
        rate_sets_created = seed_rates(session)
        raw_key = seed_api_key(session)
        session.commit()

        print(f"Development rate sets created: {rate_sets_created}")

        if raw_key is not None:
            print("\nDevelopment API key (shown once; save it securely):")
            print(raw_key)

        print("\nSeeding completed.")
        return 0

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
