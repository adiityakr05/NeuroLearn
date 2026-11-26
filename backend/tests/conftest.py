import os
import re
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db, normalize_database_url
from app.core.config import settings


def get_test_database_url() -> str:
    """
    Retrieves and validates the test database URL.

    - Uses TEST_DATABASE_URL environment variable if set.
    - Otherwise defaults to in-memory SQLite: 'sqlite:///:memory:'.
    - Safety guard: Rejects URLs pointing to production databases or containing production identifiers.
    """
    raw_url = os.environ.get("TEST_DATABASE_URL")
    if not raw_url:
        return "sqlite:///:memory:"

    normalized = normalize_database_url(raw_url.strip())

    # Production safety guard checks
    lower_url = normalized.lower()
    unsafe_patterns = [
        "production",
        "prod",
        "live",
        "aws.com",
        "azure.com",
        "supabase.co",
        "render.com",
        "neon.tech",
        "railway.app",
    ]
    # Check if the database name, host, or path matches any unsafe production indicator
    for pattern in unsafe_patterns:
        if pattern in lower_url:
            raise ValueError(
                f"Safety Guard Blocked: TEST_DATABASE_URL contains production indicator '{pattern}'. "
                "Tests must never run against production databases!"
            )

    # Check if TEST_DATABASE_URL accidentally equals the app's configured production URI (if not sqlite)
    app_uri = normalize_database_url(settings.SQLALCHEMY_DATABASE_URI)
    if not app_uri.startswith("sqlite") and normalized == app_uri:
        raise ValueError(
            "Safety Guard Blocked: TEST_DATABASE_URL matches the application's SQLALCHEMY_DATABASE_URI. "
            "Tests must use a dedicated isolated test database."
        )

    return normalized


def create_test_engine(url: str):
    """
    Creates an appropriately configured SQLAlchemy engine for testing.
    Uses StaticPool and check_same_thread=False for in-memory SQLite,
    or standard pooling for PostgreSQL test databases.
    """
    if url.startswith("sqlite"):
        connect_args = {}
        if ":memory:" in url or "check_same_thread" not in url:
            connect_args = {"check_same_thread": False}
        return create_engine(
            url,
            connect_args=connect_args,
            poolclass=StaticPool if ":memory:" in url else None,
        )
    return create_engine(url, pool_pre_ping=True)


# Module-level engine and sessionmaker derived from configured test URL
TEST_DB_URL = get_test_database_url()
test_engine = create_test_engine(TEST_DB_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """
    Provides an isolated database session for each test function.
    Creates schema prior to test execution and cleanly drops schema afterwards.
    """
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    Provides a FastAPI TestClient with get_db overridden to use the isolated test session.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
