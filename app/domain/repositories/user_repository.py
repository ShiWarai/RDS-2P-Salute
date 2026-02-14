"""
Интерфейс репозитория пользователей
"""
from abc import ABC, abstractmethod
from typing import Optional, Set
from app.domain.entities.user import User
from app.domain.value_objects.user_state import UserState


class IUserRepository(ABC):
    """Интерфейс репозитория для работы с пользователями"""
    
    @abstractmethod
    def get_user(self, user_id: str) -> Optional[User]:
        """
        Получает пользователя по ID
        
        Args:
            user_id: ID пользователя
            
        Returns:
            User или None если не найден
        """
        pass
    
    @abstractmethod
    def save_user(self, user: User) -> bool:
        """
        Сохраняет пользователя
        
        Args:
            user: Пользователь для сохранения
            
        Returns:
            True если успешно
        """
        pass
    
    @abstractmethod
    def get_user_states(self, user_id: str) -> Set[UserState]:
        """
        Получает все активные состояния пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Множество активных состояний
        """
        pass
    
    @abstractmethod
    def has_user_state(self, user_id: str, state: UserState) -> bool:
        """
        Проверяет наличие состояния у пользователя
        
        Args:
            user_id: ID пользователя
            state: Состояние для проверки
            
        Returns:
            True если состояние активно
        """
        pass
    
    @abstractmethod
    def add_user_state(self, user_id: str, state: UserState, ttl: int = 300) -> bool:
        """
        Добавляет состояние пользователю
        
        Args:
            user_id: ID пользователя
            state: Состояние для добавления
            ttl: Время жизни в секундах
            
        Returns:
            True если успешно
        """
        pass
    
    @abstractmethod
    def remove_user_state(self, user_id: str, state: UserState) -> bool:
        """
        Удаляет состояние у пользователя
        
        Args:
            user_id: ID пользователя
            state: Состояние для удаления
            
        Returns:
            True если успешно
        """
        pass
    
    @abstractmethod
    def clear_user_states(self, user_id: str) -> bool:
        """
        Очищает все состояния пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если успешно
        """
        pass
