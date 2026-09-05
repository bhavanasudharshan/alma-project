"""Stage 0 smoke test: the app boots and serves the health endpoint (M2)."""

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app

client = TestClient(create_app())


def test_health_returns_ok() -> None:
    """GET /api/v1/health returns 200 with an ok status body."""
    response = client.get(f"{get_settings().api_v1_prefix}/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
