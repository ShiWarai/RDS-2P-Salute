"""
Unit-тесты для ProcessCommandUseCase.
"""
import pytest

from app.application.dto.command_request import CommandRequestDTO

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_cvc_unavailable_returns_message(
    mock_binding_repo,
    mock_user_repo,
    mock_robot_connector,
    mock_command_feedback_repo,
):
    """При недоступном CVC — ответ «сервис классификации временно недоступен»."""
    from app.application.use_cases.process_command import ProcessCommandUseCase
    from app.application.use_cases.bind_robot import BindRobotUseCase
    from app.application.use_cases.unbind_robot import UnbindRobotUseCase
    from app.application.use_cases.get_help import GetHelpUseCase
    from app.application.use_cases.handle_binding_flow import HandleBindingFlowUseCase
    from tests.mocks.mock_classifier import MockClassifier

    classifier = MockClassifier(available=False)
    bind_robot_uc = BindRobotUseCase(
        mock_binding_repo, mock_user_repo, mock_robot_connector
    )
    unbind_robot_uc = UnbindRobotUseCase(mock_binding_repo)
    get_help_uc = GetHelpUseCase(mock_user_repo)
    handle_binding_flow_uc = HandleBindingFlowUseCase(
        mock_binding_repo, mock_user_repo, bind_robot_uc
    )
    uc = ProcessCommandUseCase(
        user_repository=mock_user_repo,
        binding_repository=mock_binding_repo,
        command_classifier=classifier,
        robot_connector=mock_robot_connector,
        bind_robot_uc=bind_robot_uc,
        unbind_robot_uc=unbind_robot_uc,
        get_help_uc=get_help_uc,
        handle_binding_flow_uc=handle_binding_flow_uc,
        command_feedback_repository=mock_command_feedback_repo,
    )

    req = CommandRequestDTO(
        user_id="user1",
        utterance="лапу",
        is_new_session=False,
        intent="",
        data={},
        message=None,
        is_chatapp=False,
    )
    resp = await uc.execute(req)
    assert "недоступен" in resp.text.lower() or "временно" in resp.text.lower()


@pytest.mark.asyncio
async def test_help_returns_menu(process_command_use_case):
    """При «help» — возвращается меню помощи."""
    req = CommandRequestDTO(
        user_id="user1",
        utterance="помощь",
        is_new_session=False,
        intent="",
        data={},
        message=None,
        is_chatapp=False,
    )
    resp = await process_command_use_case.execute(req)
    assert "служебн" in resp.text.lower() or "раздел" in resp.text.lower()


@pytest.mark.asyncio
async def test_bind_with_robot_id_calls_start_binding(
    process_command_use_case,
    mock_robot_connector,
    mock_binding_repo,
):
    """При «bind» + robot_id — вызывается bind_robot_uc.start_binding."""
    req = CommandRequestDTO(
        user_id="user1",
        utterance="привяжи робота 0",
        is_new_session=False,
        intent="",
        data={},
        message=None,
        is_chatapp=False,
    )
    resp = await process_command_use_case.execute(req)
    assert "код" in resp.text.lower() or "привяз" in resp.text.lower()
    assert mock_binding_repo.has_binding("user1") or "user1" in str(mock_binding_repo._binding_data)


@pytest.mark.asyncio
async def test_unbind_calls_unbind(
    process_command_use_case,
    mock_binding_repo,
):
    """При «unbind» — вызывается unbind_robot_uc.execute."""
    from app.domain.value_objects.robot_id import RobotId

    mock_binding_repo._bindings["user1"] = "0"
    req = CommandRequestDTO(
        user_id="user1",
        utterance="отвяжи робота",
        is_new_session=False,
        intent="",
        data={},
        message=None,
        is_chatapp=False,
    )
    resp = await process_command_use_case.execute(req)
    assert not mock_binding_repo.has_binding("user1")
    assert "отвяз" in resp.text.lower() or "отвязан" in resp.text.lower()


@pytest.mark.asyncio
async def test_command_without_binding_returns_message(
    process_command_use_case,
):
    """При команде роботу без привязки — сообщение «привяжите робота»."""
    req = CommandRequestDTO(
        user_id="user1",
        utterance="лапу",
        is_new_session=False,
        intent="",
        data={},
        message=None,
        is_chatapp=False,
    )
    resp = await process_command_use_case.execute(req)
    assert "привяж" in resp.text.lower() or "робот" in resp.text.lower()


@pytest.mark.asyncio
async def test_command_with_binding_sends_to_robot(
    process_command_use_case,
    mock_binding_repo,
    mock_robot_connector,
):
    """При команде роботу с привязкой — вызывается robot_connector.send_command."""
    from app.domain.value_objects.robot_id import RobotId

    mock_binding_repo._bindings["user1"] = "0"
    req = CommandRequestDTO(
        user_id="user1",
        utterance="лапу",
        is_new_session=False,
        intent="",
        data={},
        message=None,
        is_chatapp=False,
    )
    resp = await process_command_use_case.execute(req)
    assert mock_robot_connector.sent_commands
    assert len(mock_robot_connector.sent_commands) >= 1
    assert mock_robot_connector.sent_commands[0][1] == "give_paw"
    assert "лапу" in resp.text.lower() or "🐾" in resp.text
