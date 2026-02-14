"""
Фикстуры для E2E-тестов. Запуск только с pytest -m e2e.
"""
import pytest

pytestmark = pytest.mark.e2e
