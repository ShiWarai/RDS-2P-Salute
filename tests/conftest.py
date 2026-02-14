"""
Общие фикстуры для всех тестов.
"""
import pytest

from tests.mocks.mock_classifier import MockClassifier
from tests.mocks.mock_robot_connector import MockRobotConnector
from tests.mocks.mock_repositories import (
    InMemoryBindingRepository,
    InMemoryUserRepository,
    InMemoryCommandFeedbackRepository,
)


@pytest.fixture
def mock_classifier():
    """Мок классификатора (CVC недоступен в тестах)."""
    return MockClassifier(available=True)


@pytest.fixture
def mock_classifier_unavailable():
    """Мок классификатора в состоянии «недоступен»."""
    return MockClassifier(available=False)


@pytest.fixture
def mock_binding_repo():
    """In-memory репозиторий привязок."""
    return InMemoryBindingRepository()


@pytest.fixture
def mock_user_repo():
    """In-memory репозиторий пользователей."""
    return InMemoryUserRepository()


@pytest.fixture
def mock_command_feedback_repo():
    """In-memory репозиторий обратной связи по командам."""
    return InMemoryCommandFeedbackRepository()


@pytest.fixture
def mock_robot_connector():
    """Мок коннектора робота. По умолчанию робот 0 «подключён»."""
    connector = MockRobotConnector(connected_robot_ids=["0"])
    return connector
