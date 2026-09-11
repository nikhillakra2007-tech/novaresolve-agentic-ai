from unittest.mock import patch
from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "NovaCart API"
    assert data["status"] == "running"


def test_health_endpoint_connected(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "NovaCart API"
    assert data["status"] == "healthy"
    assert data["environment"] == "development"
    assert "database" in data

    db_info = data["database"]
    assert db_info["status"] == "connected"
    assert isinstance(db_info["latency_ms"], (int, float))
    assert db_info["latency_ms"] >= 0
    assert "pool" in db_info
    assert "size" in db_info["pool"]


def test_health_endpoint_disconnected(client: TestClient):
    mock_disconnected = {
        "status": "disconnected",
        "latency_ms": None,
        "error": "Connection refused",
    }
    with patch("backend.app.api.routes.health.check_db_connection", return_value=mock_disconnected):
        response = client.get("/api/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"]["status"] == "disconnected"
