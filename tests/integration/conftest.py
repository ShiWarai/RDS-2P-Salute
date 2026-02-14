"""
Фикстуры для интеграционных тестов. TestClient с переопределёнными Depends.
"""
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import (
    router,
    get_process_command_use_case,
    get_command_feedback_repository,
    require_local_network,
)
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


def _create_test_process_command_use_case(
    binding_repo=None,
    user_repo=None,
    command_feedback_repo=None,
):
    """Создаёт ProcessCommandUseCase с моками (без CVC, без Redis)."""
    binding_repo = binding_repo or InMemoryBindingRepository()
    user_repo = user_repo or InMemoryUserRepository()
    command_feedback_repo = command_feedback_repo or InMemoryCommandFeedbackRepository()
    classifier = MockClassifier(available=True)
    robot_connector = MockRobotConnector(
        connected_robot_ids=["0"],
        fixed_code="1234",
    )

    bind_robot_uc = BindRobotUseCase(binding_repo, user_repo, robot_connector)
    unbind_robot_uc = UnbindRobotUseCase(binding_repo)
    get_help_uc = GetHelpUseCase(user_repo)
    handle_binding_flow_uc = HandleBindingFlowUseCase(
        binding_repo, user_repo, bind_robot_uc
    )

    return ProcessCommandUseCase(
        user_repository=user_repo,
        binding_repository=binding_repo,
        command_classifier=classifier,
        robot_connector=robot_connector,
        bind_robot_uc=bind_robot_uc,
        unbind_robot_uc=unbind_robot_uc,
        get_help_uc=get_help_uc,
        handle_binding_flow_uc=handle_binding_flow_uc,
        command_feedback_repository=command_feedback_repo,
    )


@pytest.fixture
def app_client():
    """TestClient с переопределёнными зависимостями."""
    shared_states: dict = {}
    binding_repo = InMemoryBindingRepository(shared_user_states=shared_states)
    user_repo = InMemoryUserRepository(shared_states=shared_states)
    command_feedback_repo = InMemoryCommandFeedbackRepository()

    @asynccontextmanager
    async def test_lifespan(app: FastAPI):
        app.state.binding_repository = binding_repo
        yield

    app = FastAPI(title="Test API", lifespan=test_lifespan)
    app.include_router(router)

    use_case = _create_test_process_command_use_case(
        binding_repo=binding_repo,
        user_repo=user_repo,
        command_feedback_repo=command_feedback_repo,
    )
    app.dependency_overrides[get_process_command_use_case] = lambda: use_case
    app.dependency_overrides[get_command_feedback_repository] = lambda: command_feedback_repo
    app.dependency_overrides[require_local_network] = lambda request=None: None

    with TestClient(app) as client:
        yield client
