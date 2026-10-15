"""Database engine and session management."""

from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _normalize_database_url(url: str) -> str:
    """Normalize common PostgreSQL URL schemes for psycopg."""
    url = url.strip()

    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]

    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]

    return url


def _create_engine() -> Engine | None:
    """Create the engine only when database configuration is present."""
    url = settings.database_url

    if not url or not url.strip():
        return None

    normalized_url = _normalize_database_url(url)

    return create_engine(
        normalized_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=1800,
        echo=settings.debug,
    )


engine = _create_engine()

SessionLocal = (
    sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )
    if engine is not None
    else None
)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for a request."""
    if SessionLocal is None:
        raise RuntimeError(
            "Database is not configured. Set DATABASE_URL before "
            "using database-backed endpoints."
        )

    with SessionLocal() as session:
        yield session


def dispose_engine() -> None:
    """Release pooled database connections during application shutdown."""
    if engine is not None:
        engine.dispose()
