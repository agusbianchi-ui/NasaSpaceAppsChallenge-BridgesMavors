from fastapi.testclient import TestClient


def test_health_returns_exact_legacy_payload(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "project": "MARS OPS",
    }


def test_health_allows_documented_frontend_origins(
    client: TestClient,
) -> None:
    for origin in ("http://localhost:5173", "http://127.0.0.1:5173"):
        response = client.get("/api/health", headers={"Origin": origin})

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin


def test_health_rejects_unknown_origin(client: TestClient) -> None:
    response = client.get(
        "/api/health", headers={"Origin": "http://example.com"}
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
