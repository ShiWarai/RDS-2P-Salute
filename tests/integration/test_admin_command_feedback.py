"""
Интеграционные тесты для GET /v1/admin/command-feedback.
Доступ из localhost не блокируется в тестах (require_local_network переопределён).
"""
import pytest

pytestmark = pytest.mark.integration


def test_admin_command_feedback_returns_list(app_client):
    """GET /v1/admin/command-feedback — 200, список (может быть пустым)."""
    resp = app_client.get("/v1/admin/command-feedback")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
