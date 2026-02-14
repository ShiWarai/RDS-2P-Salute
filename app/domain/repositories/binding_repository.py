"""
Интерфейс репозитория привязок
"""
from abc import ABC, abstractmethod
from typing import Optional, Tuple
from app.domain.value_objects.robot_id import RobotId
from app.domain.value_objects.binding_code import BindingCode


class IBindingRepository(ABC):
    """Интерфейс репозитория для работы с привязками пользователей к роботам"""
    
    @abstractmethod
    def has_binding(self, user_id: str) -> bool:
        """
        Проверяет наличие привязки у пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если есть привязка
        """
        pass
    
    @abstractmethod
    def get_robot_id(self, user_id: str) -> Optional[RobotId]:
        """
        Получает ID привязанного робота
        
        Args:
            user_id: ID пользователя
            
        Returns:
            RobotId или None если нет привязки
        """
        pass
    
    @abstractmethod
    def start_binding(
        self,
        user_id: str,
        robot_id: RobotId,
        code: BindingCode,
        expires_at: float
    ) -> bool:
        """
        Начинает процесс привязки
        
        Args:
            user_id: ID пользователя
            robot_id: ID робота для привязки
            code: Код верификации
            expires_at: Unix timestamp истечения кода
            
        Returns:
            True если успешно
        """
        pass
    
    @abstractmethod
    def get_binding_code(self, user_id: str) -> Optional[Tuple[BindingCode, float]]:
        """
        Получает код привязки и время истечения
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Tuple (BindingCode, expires_at) или None если нет активной привязки
        """
        pass
    
    @abstractmethod
    def verify_binding_code(self, user_id: str, code: BindingCode) -> Tuple[bool, str, int]:
        """
        Проверяет код верификации
        
        Args:
            user_id: ID пользователя
            code: Код для проверки
            
        Returns:
            Tuple (success, message, attempts)
        """
        pass
    
    @abstractmethod
    def complete_binding(self, user_id: str) -> bool:
        """
        Завершает привязку - сохраняет постоянную привязку
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если успешно
        """
        pass
    
    @abstractmethod
    def cancel_binding(self, user_id: str) -> bool:
        """
        Отменяет процесс привязки
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если успешно
        """
        pass
    
    @abstractmethod
    def unbind_robot(self, user_id: str) -> bool:
        """
        Отвязывает робота от пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если успешно
        """
        pass
