import pytest
from fastapi.testclient import TestClient
from app.main import app

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
