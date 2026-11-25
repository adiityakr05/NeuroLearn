import re
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator, Optional
from app.core.config import settings


def normalize_database_url(url: Optional[str]) -> str:
    """
    Normalizes database connection URLs for SQLAlchemy and Alembic compatibility.

    - Replaces legacy 'postgres://' scheme with 'postgresql+psycopg2://' (ensuring psycopg2 driver is selected).
    - Replaces generic 'postgresql://' with 'postgresql+psycopg2://' when psycopg (v3) is absent.
    - Preserves explicit dialect-specific 'postgresql+psycopg2://'.
    - Preserves usernames, passwords, hosts, ports, paths, and query parameters.
    - Preserves SQLite, MySQL, and other unrelated URL schemes untouched.
    """
    if not url:
        return ""

    trimmed = url.strip()

    # Match legacy postgres:// or postgresql:// schemes (only at the beginning of the string)
    if trimmed.startswith("postgres://"):
        return "postgresql+psycopg2://" + trimmed[len("postgres://"):]

    if trimmed.startswith("postgresql://"):
        return "postgresql+psycopg2://" + trimmed[len("postgresql://"):]

    return trimmed


# Retrieve normalized connection URI
NORMALIZED_DATABASE_URI = normalize_database_url(settings.SQLALCHEMY_DATABASE_URI)

# Configure engine with connect_args for SQLite thread safety if using SQLite
connect_args = {}
if NORMALIZED_DATABASE_URI.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    NORMALIZED_DATABASE_URI,
    connect_args=connect_args,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields an independent database session per request
    and guarantees safe closure upon completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
