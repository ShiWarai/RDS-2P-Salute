"""
Доменная сущность User
"""
from typing import Set
from app.domain.value_objects.user_state import UserState


class User:
    """Пользователь системы"""
    
    def __init__(self, user_id: str, states: Set[UserState] = None):
        """
        Создает пользователя
        
        Args:
            user_id: Уникальный идентификатор пользователя
            states: Множество активных состояний пользователя
        """
        if not user_id:
            raise ValueError("user_id не может быть пустым")
        self._user_id = user_id
        self._states = states or set()
    
    @property
    def user_id(self) -> str:
        """Возвращает ID пользователя"""
        return self._user_id
    
    @property
    def states(self) -> Set[UserState]:
        """Возвращает множество активных состояний"""
        return self._states.copy()
    
    def has_state(self, state: UserState) -> bool:
        """Проверяет наличие состояния"""
        return state in self._states
    
    def add_state(self, state: UserState) -> None:
        """Добавляет состояние"""
        self._states.add(state)
    
    def remove_state(self, state: UserState) -> None:
        """Удаляет состояние"""
        self._states.discard(state)
    
    def clear_states(self) -> None:
        """Очищает все состояния"""
        self._states.clear()
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, User):
            return False
        return self._user_id == other._user_id
    
    def __hash__(self) -> int:
        return hash(self._user_id)
    
    def __repr__(self) -> str:
        return f"User(user_id='{self._user_id}', states={self._states})"
