import pytest
from app.db.session import normalize_database_url, NORMALIZED_DATABASE_URI, engine
from app.core.config import settings
from alembic.config import Config


def test_legacy_postgres_url_normalized():
    """Test legacy postgres:// is converted to postgresql+psycopg2://."""
    url = "postgres://user:password@host:5432/database"
    expected = "postgresql+psycopg2://user:password@host:5432/database"
    assert normalize_database_url(url) == expected


def test_standard_postgresql_url_preserved():
    """Test standard postgresql:// URL is normalized to postgresql+psycopg2://."""
    url = "postgresql://user:secret@db.example.com:5432/neurolearn"
    expected = "postgresql+psycopg2://user:secret@db.example.com:5432/neurolearn"
    assert normalize_database_url(url) == expected


def test_explicit_postgresql_psycopg2_preserved():
    """Test dialect-specific postgresql+psycopg2:// is kept intact."""
    url = "postgresql+psycopg2://usr:pwd@127.0.0.1:5432/neurolearn"
    assert normalize_database_url(url) == url


def test_url_credentials_and_query_parameters_preserved():
    """Test special characters in credentials, ports, and query parameters remain intact."""
    url = "postgres://app_user:p%40ssw0rd!@pg-cluster.internal:5432/neurolearn_prod?sslmode=require&application_name=neurolearn"
    expected = "postgresql+psycopg2://app_user:p%40ssw0rd!@pg-cluster.internal:5432/neurolearn_prod?sslmode=require&application_name=neurolearn"
    assert normalize_database_url(url) == expected


def test_sqlite_url_preserved():
    """Test SQLite file and memory URLs are unchanged."""
    assert normalize_database_url("sqlite:///./neurolearn.db") == "sqlite:///./neurolearn.db"
    assert normalize_database_url("sqlite:///:memory:") == "sqlite:///:memory:"


def test_unrelated_schemes_and_empty_inputs_preserved():
    """Test empty, None, and unrelated schemes (e.g. mysql://) are preserved."""
    assert normalize_database_url(None) == ""
    assert normalize_database_url("") == ""
    assert normalize_database_url("   ") == ""
    assert normalize_database_url("mysql+pymysql://root:pass@localhost/db") == "mysql+pymysql://root:pass@localhost/db"
    assert normalize_database_url("https://example.com/postgres://path") == "https://example.com/postgres://path"


def test_application_engine_and_alembic_integration(monkeypatch):
    """Test application engine creation logic and Alembic config option get normalized."""
    test_legacy_url = "postgres://usr:pwd@localhost:5432/mydb"
    normalized = normalize_database_url(test_legacy_url)
    assert normalized == "postgresql+psycopg2://usr:pwd@localhost:5432/mydb"

    # Verify Alembic config option setting behavior
    cfg = Config()
    cfg.set_main_option("sqlalchemy.url", normalized)
    assert cfg.get_main_option("sqlalchemy.url") == "postgresql+psycopg2://usr:pwd@localhost:5432/mydb"

    # Verify current application engine dialect is active and safe
    assert engine.url is not None
    assert str(engine.url) == normalize_database_url(settings.SQLALCHEMY_DATABASE_URI)
