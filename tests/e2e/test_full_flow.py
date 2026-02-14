"""
E2E-тесты полного потока (опционально).
Запуск: pytest -m e2e
В CI по умолчанию не выполняются.
"""
import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.skip(reason="E2E требует docker compose up redis app и fake_robot")
def test_full_binding_and_command_flow():
    """
    Сценарий E2E:
    1. docker compose up -d redis app
    2. fake_robot в фоне
    3. POST /v1/webhook с привязкой и командой
    4. Проверка привязки и команды
    """
    pass
