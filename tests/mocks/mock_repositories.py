"""
In-memory реализации репозиториев для тестов.
"""
from typing import Dict, Optional, Set, List, Tuple
import time

from app.domain.repositories.binding_repository import IBindingRepository
from app.domain.repositories.user_repository import IUserRepository
from app.domain.repositories.command_feedback_repository import ICommandFeedbackRepository
from app.domain.entities.user import User
from app.domain.value_objects.robot_id import RobotId
from app.domain.value_objects.binding_code import BindingCode
from app.domain.value_objects.user_state import UserState


class InMemoryBindingRepository(IBindingRepository):
    """In-memory реализация IBindingRepository."""

    def __init__(self, shared_user_states: Optional[Dict[str, Set]] = None):
        self._bindings: Dict[str, str] = {}  # user_id -> robot_id
        self._binding_data: Dict[str, dict] = {}  # user_id -> {robot_id, code, expires_at, attempts}
        self._user_states: Dict[str, Set] = shared_user_states if shared_user_states is not None else {}

    def has_binding(self, user_id: str) -> bool:
        return user_id in self._bindings

    def get_robot_id(self, user_id: str) -> Optional[RobotId]:
        robot_id_str = self._bindings.get(user_id)
        if robot_id_str:
            return RobotId(robot_id_str)
        data = self._binding_data.get(user_id)
        if data:
            return RobotId(data["robot_id"])
        return None

    def start_binding(
        self,
        user_id: str,
        robot_id: RobotId,
        code: BindingCode,
        expires_at: float
    ) -> bool:
        self._binding_data[user_id] = {
            "robot_id": robot_id.value,
            "code": code.value,
            "expires_at": expires_at,
            "attempts": 0,
        }
        states_key = user_id
        if states_key not in self._user_states:
            self._user_states[states_key] = set()
        self._user_states[states_key].add(UserState.WAITING_CODE)
        return True

    def get_binding_code(self, user_id: str) -> Optional[Tuple[BindingCode, float]]:
        data = self._binding_data.get(user_id)
        if not data or time.time() > data["expires_at"]:
            return None
        return BindingCode(data["code"]), data["expires_at"]

    def verify_binding_code(self, user_id: str, code: BindingCode) -> Tuple[bool, str, int]:
        data = self._binding_data.get(user_id)
        if not data:
            return False, "Процесс привязки не начат", 0
        if time.time() > data["expires_at"]:
            self.cancel_binding(user_id)
            return False, "Код истек. Начните привязку заново.", 0
        if code.value != data["code"]:
            data["attempts"] = data["attempts"] + 1
            if data["attempts"] >= 3:
                self.cancel_binding(user_id)
                return False, "Превышено количество попыток. Начните привязку заново.", data["attempts"]
            return False, f"Неверный код. Осталось попыток: {3 - data['attempts']}", data["attempts"]
        return True, "Код подтвержден", data["attempts"]

    def complete_binding(self, user_id: str) -> bool:
        data = self._binding_data.get(user_id)
        if not data:
            return False
        self._bindings[user_id] = data["robot_id"]
        self.cancel_binding(user_id)
        return True

    def cancel_binding(self, user_id: str) -> bool:
        states = self._user_states.get(user_id, set())
        states.discard(UserState.WAITING_CODE)
        if not states:
            self._user_states.pop(user_id, None)
        self._binding_data.pop(user_id, None)
        return True

    def unbind_robot(self, user_id: str) -> bool:
        if user_id in self._bindings:
            del self._bindings[user_id]
            return True
        return False

    def get_all_bindings(self) -> list:
        return [{"user_id": u, "robot_id": r} for u, r in self._bindings.items()]


class InMemoryUserRepository(IUserRepository):
    """In-memory реализация IUserRepository."""

    def __init__(self, shared_states: Optional[Dict[str, Set[UserState]]] = None):
        self._states: Dict[str, Set[UserState]] = shared_states if shared_states is not None else {}

    def get_user(self, user_id: str) -> Optional[User]:
        states = self._states.get(user_id, set())
        if states or user_id in self._states:
            return User(user_id, states)
        return None

    def save_user(self, user: User) -> bool:
        self._states[user.user_id] = user.states.copy()
        return True

    def get_user_states(self, user_id: str) -> Set[UserState]:
        return self._states.get(user_id, set()).copy()

    def has_user_state(self, user_id: str, state: UserState) -> bool:
        return state in self._states.get(user_id, set())

    def add_user_state(self, user_id: str, state: UserState, ttl: int = 300) -> bool:
        if user_id not in self._states:
            self._states[user_id] = set()
        self._states[user_id].add(state)
        return True

    def remove_user_state(self, user_id: str, state: UserState) -> bool:
        if user_id in self._states:
            self._states[user_id].discard(state)
            if not self._states[user_id]:
                del self._states[user_id]
        return True

    def clear_user_states(self, user_id: str) -> bool:
        if user_id in self._states:
            del self._states[user_id]
            return True
        return False


class InMemoryCommandFeedbackRepository(ICommandFeedbackRepository):
    """In-memory реализация ICommandFeedbackRepository."""

    def __init__(self):
        self._last_command: Dict[str, Tuple[str, str]] = {}
        self._feedback: List[dict] = []

    def set_last_command(
        self,
        user_id: str,
        utterance: str,
        function_name: str,
        ttl_seconds: int = 300,
    ) -> None:
        self._last_command[user_id] = (utterance, function_name)

    def get_last_command(self, user_id: str) -> Optional[Tuple[str, str]]:
        return self._last_command.get(user_id)

    def clear_last_command(self, user_id: str) -> None:
        self._last_command.pop(user_id, None)

    def add_feedback(
        self,
        user_id: str,
        robot_id: str,
        user_utterance: str,
        classified_function: str,
        created_at: float,
        meta: Optional[dict] = None,
    ) -> None:
        record = {
            "user_id": user_id,
            "robot_id": robot_id,
            "user_utterance": user_utterance,
            "classified_function": classified_function,
            "created_at": created_at,
        }
        if meta is not None:
            record["meta"] = meta
        self._feedback.append(record)

    def get_all_feedback(self) -> list:
        return self._feedback.copy()
