"""
Unit-тесты для BindRobotUseCase.
"""
import pytest

from tests.mocks.mock_robot_connector import MockRobotConnector
from tests.mocks.mock_repositories import InMemoryBindingRepository, InMemoryUserRepository

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_successful_binding_initiation(
    mock_binding_repo,
    mock_user_repo,
):
    """Успешная инициация привязки: вызов initiate_binding, start_binding."""
    from app.application.use_cases.bind_robot import BindRobotUseCase

    connector = MockRobotConnector(connected_robot_ids=["0"])
    uc = BindRobotUseCase(mock_binding_repo, mock_user_repo, connector)

    success, message = await uc.start_binding("user1", "0")

    assert success is True
    assert "код" in message.lower() or "привяз" in message.lower()
    from app.domain.value_objects.user_state import UserState

    assert mock_binding_repo.get_binding_code("user1") is not None
    assert mock_user_repo.has_user_state("user1", UserState.WAITING_CODE)


@pytest.mark.asyncio
async def test_binding_fails_when_robot_not_connected(
    mock_binding_repo,
    mock_user_repo,
):
    """Привязка не удаётся, если робот не подключён."""
    from app.application.use_cases.bind_robot import BindRobotUseCase

    connector = MockRobotConnector(connected_robot_ids=[])
    uc = BindRobotUseCase(mock_binding_repo, mock_user_repo, connector)

    success, message = await uc.start_binding("user1", "0")

    assert success is False
    assert "не подключен" in message.lower() or "подключ" in message.lower()
