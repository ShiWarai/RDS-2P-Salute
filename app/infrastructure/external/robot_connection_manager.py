"""
Менеджер активных соединений роботов через gRPC
"""
import queue
import logging
import threading
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class RobotConnectionManager:
    """Управление активными gRPC соединениями с роботами (потокобезопасный)"""

    def __init__(self):
        """Инициализация менеджера соединений"""
        self._connections: Dict[str, queue.Queue] = {}
        self._lock = threading.Lock()
        logger.info("RobotConnectionManager инициализирован")

    def get_robot_name(self, robot_id: str) -> str:
        """Возвращает отображаемое имя робота: «Робот {robot_id}»."""
        return f"Робот {robot_id}"

    def get_available_robots_list(self) -> str:
        """
        Возвращает строку со списком доступных роботов
        """
        connected_robots = self.get_connected_robots()

        if not connected_robots:
            return "Нет подключенных роботов"

        robot_list = []
        for robot_id in connected_robots:
            name = self.get_robot_name(robot_id)
            robot_list.append(f"{robot_id} - {name}")

        return ", ".join(robot_list)

    def add_connection(self, robot_id: str, message_queue: queue.Queue) -> None:
        """
        Добавляет активное соединение робота

        Args:
            robot_id: ID робота
            message_queue: Очередь сообщений для отправки роботу
        """
        with self._lock:
            self._connections[robot_id] = message_queue
            count = len(self._connections)
        logger.info(f"Добавлено соединение для робота {robot_id}. Всего соединений: {count}")

    def remove_connection(self, robot_id: str) -> None:
        """
        Удаляет соединение робота

        Args:
            robot_id: ID робота
        """
        with self._lock:
            if robot_id in self._connections:
                del self._connections[robot_id]
                count = len(self._connections)
                logger.info(f"Удалено соединение для робота {robot_id}. Всего соединений: {count}")
            else:
                logger.warning(f"Попытка удалить несуществующее соединение для робота {robot_id}")

    def send_message(self, robot_id: str, message) -> bool:
        """
        Отправляет сообщение роботу через активное соединение

        Args:
            robot_id: ID робота
            message: Сообщение для отправки (StreamMessage)

        Returns:
            bool: True если сообщение успешно добавлено в очередь
        """
        with self._lock:
            if robot_id not in self._connections:
                logger.warning(f"Робот {robot_id} не подключен")
                return False
            message_queue = self._connections[robot_id]
        try:
            message_queue.put(message)
            logger.debug(f"Сообщение отправлено роботу {robot_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения роботу {robot_id}: {e}", exc_info=True)
            return False

    def is_connected(self, robot_id: str) -> bool:
        """
        Проверяет, подключен ли робот

        Args:
            robot_id: ID робота

        Returns:
            bool: True если робот подключен
        """
        with self._lock:
            return robot_id in self._connections

    def get_connected_robots(self) -> list[str]:
        """
        Возвращает список ID подключенных роботов

        Returns:
            list[str]: Список ID роботов
        """
        with self._lock:
            return list(self._connections.keys())

    def get_connection_count(self) -> int:
        """
        Возвращает количество активных соединений

        Returns:
            int: Количество активных соединений
        """
        with self._lock:
            return len(self._connections)


# Глобальный экземпляр менеджера соединений
_connection_manager: Optional[RobotConnectionManager] = None


def get_connection_manager() -> RobotConnectionManager:
    """
    Возвращает глобальный экземпляр менеджера соединений (singleton)
    
    Returns:
        RobotConnectionManager: Экземпляр менеджера соединений
    """
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = RobotConnectionManager()
    return _connection_manager
