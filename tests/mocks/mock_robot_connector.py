"""
Мок IRobotConnector для тестов.
"""
import random
import time
from typing import List, Optional, Tuple

from app.domain.services.robot_connector import IRobotConnector
from app.domain.value_objects.robot_id import RobotId
from app.domain.value_objects.binding_code import BindingCode


class MockRobotConnector(IRobotConnector):
    """Заглушка IRobotConnector для тестов. Записывает отправленные команды."""

    def __init__(
        self,
        connected_robot_ids: Optional[List[str]] = None,
        binding_success: bool = True,
        fixed_code: Optional[str] = None,
    ):
        self.sent_commands: List[Tuple[str, str]] = []  # [(user_id, function_name), ...]
        self._connected = set(connected_robot_ids or [])
        self._binding_success = binding_success
        self._fixed_code = fixed_code

    def add_connected_robot(self, robot_id: str) -> None:
        self._connected.add(robot_id)

    def remove_connected_robot(self, robot_id: str) -> None:
        self._connected.discard(robot_id)

    def send_command(self, user_id: str, function_name: str) -> Tuple[bool, str]:
        self.sent_commands.append((user_id, function_name))
        return True, "Команда отправлена"

    def initiate_binding(
        self,
        user_id: str,
        robot_id: RobotId
    ) -> Tuple[bool, str, Optional[BindingCode], Optional[float]]:
        if not self._binding_success:
            return False, "Робот не подключен.", None, None
        if robot_id.value not in self._connected:
            return False, f"Робот {robot_id.value} не подключен.", None, None
        code_value = self._fixed_code or str(random.randint(1000, 9999))
        code = BindingCode(code_value)
        expires_at = time.time() + 300
        return True, f"Введите код для робота {robot_id.value}.", code, expires_at

    def complete_binding_with_code(
        self,
        user_id: str,
        robot_id: RobotId
    ) -> Tuple[bool, str]:
        return True, "Привязка завершена"
