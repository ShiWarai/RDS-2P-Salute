"""
Unit-тесты для RedisBindingRepository с fakeredis.
"""
import time
from unittest.mock import patch

import fakeredis
import pytest

from app.domain.value_objects.robot_id import RobotId
from app.domain.value_objects.binding_code import BindingCode
from app.domain.value_objects.user_state import UserState
from app.infrastructure.persistence.redis_binding_repository import (
    RedisBindingRepository,
    BINDINGS_PREFIX,
    BINDING_DATA_PREFIX,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def fake_redis():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def redis_binding_repo(fake_redis):
    with patch("app.infrastructure.persistence.redis_binding_repository.redis") as mock_redis:
        mock_redis.from_url.return_value = fake_redis
        return RedisBindingRepository("redis://localhost:6379/0")


def test_has_binding(redis_binding_repo, fake_redis):
    """has_binding — проверка наличия привязки."""
    assert redis_binding_repo.has_binding("user1") is False
    fake_redis.set(f"{BINDINGS_PREFIX}user1", "0")
    assert redis_binding_repo.has_binding("user1") is True


def test_get_robot_id(redis_binding_repo, fake_redis):
    """get_robot_id — получение ID робота."""
    assert redis_binding_repo.get_robot_id("user1") is None
    fake_redis.set(f"{BINDINGS_PREFIX}user1", "0")
    robot_id = redis_binding_repo.get_robot_id("user1")
    assert robot_id is not None
    assert robot_id.value == "0"


def test_start_binding(redis_binding_repo):
    """start_binding — начало процесса привязки."""
    robot_id = RobotId("0")
    code = BindingCode("1234")
    expires_at = time.time() + 300

    result = redis_binding_repo.start_binding("user1", robot_id, code, expires_at)

    assert result is True
    data_key = f"{BINDING_DATA_PREFIX}user1"
    assert redis_binding_repo.redis_client.exists(data_key) > 0
    state_data = redis_binding_repo.redis_client.hgetall(data_key)
    assert state_data.get("robot_id") == "0"
    assert state_data.get("code") == "1234"


def test_complete_binding(redis_binding_repo):
    """complete_binding — завершение привязки."""
    robot_id = RobotId("0")
    code = BindingCode("1234")
    expires_at = time.time() + 300
    redis_binding_repo.start_binding("user1", robot_id, code, expires_at)

    result = redis_binding_repo.complete_binding("user1")

    assert result is True
    assert redis_binding_repo.has_binding("user1") is True
    assert redis_binding_repo.get_robot_id("user1").value == "0"


def test_unbind_robot(redis_binding_repo, fake_redis):
    """unbind_robot — отвязка робота."""
    fake_redis.set(f"{BINDINGS_PREFIX}user1", "0")
    assert redis_binding_repo.has_binding("user1") is True

    result = redis_binding_repo.unbind_robot("user1")

    assert result is True
    assert redis_binding_repo.has_binding("user1") is False
