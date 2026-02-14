"""
Value Object для ID робота
"""
from typing import Optional


class RobotId:
    """ID робота"""
    
    def __init__(self, robot_id: str):
        """
        Создает ID робота с валидацией
        
        Args:
            robot_id: ID робота (непустая строка)
            
        Raises:
            ValueError: Если ID пустой
        """
        if not robot_id or not str(robot_id).strip():
            raise ValueError("ID робота не может быть пустым")
        self._value = str(robot_id).strip()
    
    @property
    def value(self) -> str:
        """Возвращает значение ID"""
        return self._value
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, RobotId):
            return False
        return self._value == other._value
    
    def __hash__(self) -> int:
        return hash(self._value)
    
    def __str__(self) -> str:
        return self._value
    
    def __repr__(self) -> str:
        return f"RobotId('{self._value}')"
    
    @classmethod
    def from_string(cls, robot_id: str) -> Optional['RobotId']:
        """
        Создает RobotId из строки, возвращает None если невалидно
        
        Args:
            robot_id: Строка с ID
            
        Returns:
            RobotId или None если невалидно
        """
        try:
            return cls(robot_id)
        except ValueError:
            return None
