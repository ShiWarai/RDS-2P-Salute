"""
Unit-тесты для request_parser.
"""
import pytest

from app.utils.request_parser import (
    extract_robot_id_from_bind_command,
    extract_user_id,
    extract_code_from_utterance,
    is_bind_command,
    is_unbind_command,
)

pytestmark = pytest.mark.unit


def test_extract_robot_id_from_bind_command():
    """extract_robot_id_from_bind_command — «привяжи робота 0» -> «0», «привяжи робота 1» -> «1»."""
    assert extract_robot_id_from_bind_command("привяжи робота 0") == "0"
    assert extract_robot_id_from_bind_command("привяжи робота 1") == "1"
    assert extract_robot_id_from_bind_command("привяжи робота 42") == "42"
    assert extract_robot_id_from_bind_command("привяжи панду 2") == "2"
    assert extract_robot_id_from_bind_command("подключи робота 3") == "3"


def test_extract_user_id():
    """extract_user_id — нормализация, sub/userId, пробелы."""
    assert extract_user_id({"sub": "user-123"}) == "user-123"
    assert extract_user_id({"userId": "user-456"}) == "user-456"
    assert extract_user_id({"sub": "  user-789  "}) == "user-789"
    assert extract_user_id({"sub": ""}) is None
    assert extract_user_id({}) is None


def test_extract_code_from_utterance():
    """extract_code_from_utterance — извлечение 4-значного кода."""
    assert extract_code_from_utterance("1234") == "1234"
    assert extract_code_from_utterance("код 5678") == "5678"
    assert extract_code_from_utterance("верификация 9012") == "9012"
    assert extract_code_from_utterance("1 2 3 4") == "1234"
    assert extract_code_from_utterance("лапу") is None
    assert extract_code_from_utterance("123") is None


def test_is_bind_command():
    """is_bind_command — распознавание команд привязки."""
    assert is_bind_command("привяжи робота 0") is True
    assert is_bind_command("привязать робота 1") is True
    assert is_bind_command("подключи робота 2") is True
    assert is_bind_command("настрой робота 3") is True
    assert is_bind_command("лапу") is False
    assert is_bind_command("отвяжи робота") is False


def test_is_unbind_command():
    """is_unbind_command — распознавание команд отвязки."""
    assert is_unbind_command("отвяжи робота") is True
    assert is_unbind_command("отвязать робота") is True
    assert is_unbind_command("отключи робота") is True
    assert is_unbind_command("привяжи робота 0") is False
    assert is_unbind_command("лапу") is False
