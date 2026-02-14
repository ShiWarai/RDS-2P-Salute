"""
Интерфейс подключения к роботу
"""
from abc import ABC, abstractmethod
from typing import Tuple, Optional
from app.domain.value_objects.robot_id import RobotId
from app.domain.value_objects.binding_code import BindingCode


class IRobotConnector(ABC):
    """Интерфейс для подключения и отправки команд роботу"""
    
    @abstractmethod
    def send_command(self, user_id: str, function_name: str) -> Tuple[bool, str]:
        """
        Отправляет команду роботу
        
        Args:
            user_id: ID пользователя
            function_name: Имя функции для выполнения (например, "give_paw")
            
        Returns:
            Tuple (success, message)
        """
        pass
    
    @abstractmethod
    def initiate_binding(
        self,
        user_id: str,
        robot_id: RobotId
    ) -> Tuple[bool, str, Optional[BindingCode], Optional[float]]:
        """
        Инициирует процесс привязки робота
        
        Args:
            user_id: ID пользователя
            robot_id: ID робота для привязки
            
        Returns:
            Tuple (success, message, code, expires_at)
        """
        pass
    
    @abstractmethod
    def complete_binding_with_code(
        self,
        user_id: str,
        robot_id: RobotId
    ) -> Tuple[bool, str]:
        """
        Уведомляет робота об успешном завершении привязки
        
        Args:
            user_id: ID пользователя
            robot_id: ID робота
            
        Returns:
            Tuple (success, message)
        """
        pass
