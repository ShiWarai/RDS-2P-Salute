"""
Фикстуры для unit-тестов.
"""
import pytest

from app.application.use_cases.process_command import ProcessCommandUseCase
from app.application.use_cases.bind_robot import BindRobotUseCase
from app.application.use_cases.unbind_robot import UnbindRobotUseCase
from app.application.use_cases.get_help import GetHelpUseCase
from app.application.use_cases.handle_binding_flow import HandleBindingFlowUseCase

from tests.mocks.mock_classifier import MockClassifier
from tests.mocks.mock_robot_connector import MockRobotConnector
from tests.mocks.mock_repositories import (
    InMemoryBindingRepository,
    InMemoryUserRepository,
    InMemoryCommandFeedbackRepository,
)


@pytest.fixture
def process_command_use_case(
    mock_classifier,
    mock_binding_repo,
    mock_user_repo,
    mock_robot_connector,
    mock_command_feedback_repo,
):
    """ProcessCommandUseCase с моками."""
    bind_robot_uc = BindRobotUseCase(
        mock_binding_repo, mock_user_repo, mock_robot_connector
    )
    unbind_robot_uc = UnbindRobotUseCase(mock_binding_repo)
    get_help_uc = GetHelpUseCase(mock_user_repo)
    handle_binding_flow_uc = HandleBindingFlowUseCase(
        mock_binding_repo, mock_user_repo, bind_robot_uc
    )
    return ProcessCommandUseCase(
        user_repository=mock_user_repo,
        binding_repository=mock_binding_repo,
        command_classifier=mock_classifier,
        robot_connector=mock_robot_connector,
        bind_robot_uc=bind_robot_uc,
        unbind_robot_uc=unbind_robot_uc,
        get_help_uc=get_help_uc,
        handle_binding_flow_uc=handle_binding_flow_uc,
        command_feedback_repository=mock_command_feedback_repo,
    )
