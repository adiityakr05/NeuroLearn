import os
import pytest
from tests.conftest import get_test_database_url, create_test_engine


def test_default_test_database_url_is_sqlite_in_memory(monkeypatch):
    """Test that absent TEST_DATABASE_URL defaults to in-memory SQLite."""
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    url = get_test_database_url()
    assert url == "sqlite:///:memory:"


def test_custom_sqlite_test_url(monkeypatch):
    """Test that custom SQLite URL is respected."""
    monkeypatch.setenv("TEST_DATABASE_URL", "sqlite:///./test_custom.db")
    url = get_test_database_url()
    assert url == "sqlite:///./test_custom.db"


def test_postgres_test_url_normalized(monkeypatch):
    """Test that legacy postgres:// URL in TEST_DATABASE_URL is normalized to postgresql+psycopg2://."""
    monkeypatch.setenv("TEST_DATABASE_URL", "postgres://test_user:test_pass@localhost:5432/neurolearn_test")
    url = get_test_database_url()
    assert url == "postgresql+psycopg2://test_user:test_pass@localhost:5432/neurolearn_test"


def test_production_safety_guard_blocks_prod_identifiers(monkeypatch):
    """Test that TEST_DATABASE_URL containing production indicators fails safely with ValueError."""
    unsafe_urls = [
        "postgresql://user:pass@localhost:5432/neurolearn_production",
        "postgresql://user:pass@localhost:5432/neurolearn_prod",
        "postgresql://user:pass@prod-db.internal:5432/test",
        "postgresql://user:pass@aws.com:5432/db",
        "postgresql://user:pass@supabase.co:5432/db",
    ]
    for unsafe_url in unsafe_urls:
        monkeypatch.setenv("TEST_DATABASE_URL", unsafe_url)
        with pytest.raises(ValueError) as exc_info:
            get_test_database_url()
        assert "Safety Guard Blocked" in str(exc_info.value)


def test_create_test_engine_sqlite():
    """Test creating SQLite test engine uses check_same_thread."""
    engine = create_test_engine("sqlite:///:memory:")
    assert engine.url.drivername == "sqlite"
