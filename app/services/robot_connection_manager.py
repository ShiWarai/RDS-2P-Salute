"""
Менеджер активных соединений роботов через gRPC
"""
import queue
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class RobotConnectionManager:
    """Управление активными gRPC соединениями с роботами"""
    
    def __init__(self):
        """Инициализация менеджера соединений"""
        self._connections: Dict[str, queue.Queue] = {}
        logger.info("RobotConnectionManager initialized")
    
    def add_connection(self, robot_id: str, message_queue: queue.Queue) -> None:
        """
        Добавляет активное соединение робота
        
        Args:
            robot_id: ID робота
            message_queue: Очередь сообщений для отправки роботу
        """
        self._connections[robot_id] = message_queue
        logger.info(f"Added connection for robot {robot_id}. Total connections: {len(self._connections)}")
    
    def remove_connection(self, robot_id: str) -> None:
        """
        Удаляет соединение робота
        
        Args:
            robot_id: ID робота
        """
        if robot_id in self._connections:
            del self._connections[robot_id]
            logger.info(f"Removed connection for robot {robot_id}. Total connections: {len(self._connections)}")
        else:
            logger.warning(f"Attempted to remove non-existent connection for robot {robot_id}")
    
    def send_message(self, robot_id: str, message) -> bool:
        """
        Отправляет сообщение роботу через активное соединение
        
        Args:
            robot_id: ID робота
            message: Сообщение для отправки (StreamMessage)
            
        Returns:
            bool: True если сообщение успешно добавлено в очередь
        """
        if robot_id not in self._connections:
            logger.warning(f"Robot {robot_id} is not connected")
            return False
        
        try:
            message_queue = self._connections[robot_id]
            message_queue.put(message)
            logger.debug(f"Message sent to robot {robot_id}")
            return True
        except Exception as e:
            logger.error(f"Error sending message to robot {robot_id}: {e}", exc_info=True)
            return False
    
    def is_connected(self, robot_id: str) -> bool:
        """
        Проверяет, подключен ли робот
        
        Args:
            robot_id: ID робота
            
        Returns:
            bool: True если робот подключен
        """
        return robot_id in self._connections
    
    def get_connected_robots(self) -> list[str]:
        """
        Возвращает список ID подключенных роботов
        
        Returns:
            list[str]: Список ID роботов
        """
        return list(self._connections.keys())
    
    def get_connection_count(self) -> int:
        """
        Возвращает количество активных соединений
        
        Returns:
            int: Количество активных соединений
        """
        return len(self._connections)
