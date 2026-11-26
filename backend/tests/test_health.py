import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.main import app
from app.db.session import get_db

client = TestClient(app)


def test_health_check_endpoint():
    """
    Test the GET /api/health endpoint returns 200 OK
    and includes database connectivity status.
    """
    response = client.get("/api/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert data["project"] == "NeuroLearn API"
    assert "version" in data
    assert data["database"] == "connected"
    # Ensure debug mode is NOT exposed
    assert "debug" not in data


def test_health_check_db_failure_does_not_leak_details(monkeypatch):
    """
    Test that when database connectivity fails, health check returns degraded/disconnected
    WITHOUT exposing raw exception details or credentials.
    """
    mock_db = MagicMock()
    # Simulate DB operational failure with sensitive simulated connection string in exception
    mock_db.execute.side_effect = OperationalError(
        "FATAL: password authentication failed for user 'admin' at postgres://admin:secret123@db.prod:5432/neurolearn",
        params=None,
        orig=Exception("connection refused"),
    )

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"] == "disconnected"
        # Confirm no leak of sensitive tokens or technical stack details
        assert "password" not in response.text
        assert "secret123" not in response.text
        assert "FATAL" not in response.text
        assert "debug" not in data
    finally:
        app.dependency_overrides.pop(get_db, None)
