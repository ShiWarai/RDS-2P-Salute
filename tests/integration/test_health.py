"""
Интеграционные тесты для GET /v1/health.
"""
import pytest

pytestmark = pytest.mark.integration


def test_health_returns_200(app_client):
    """GET /v1/health — 200, {"status": "healthy"}."""
    resp = app_client.get("/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}
