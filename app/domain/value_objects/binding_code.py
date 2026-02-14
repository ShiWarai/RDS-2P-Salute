"""
Value Object для кода привязки
"""
import re
from typing import Optional


class BindingCode:
    """Код привязки робота (4 цифры)"""
    
    CODE_PATTERN = re.compile(r'^\d{4}$')
    
    def __init__(self, code: str):
        """
        Создает код привязки с валидацией
        
        Args:
            code: Код из 4 цифр
            
        Raises:
            ValueError: Если код невалидный
        """
        code_str = str(code).strip()
        if not self.CODE_PATTERN.match(code_str):
            raise ValueError(f"Код привязки должен состоять из 4 цифр, получено: {code_str}")
        self._value = code_str
    
    @property
    def value(self) -> str:
        """Возвращает значение кода"""
        return self._value
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, BindingCode):
            return False
        return self._value == other._value
    
    def __hash__(self) -> int:
        return hash(self._value)
    
    def __str__(self) -> str:
        return self._value
    
    def __repr__(self) -> str:
        return f"BindingCode('{self._value}')"
    
    @classmethod
    def from_string(cls, code: str) -> Optional['BindingCode']:
        """
        Создает BindingCode из строки, возвращает None если невалидно
        
        Args:
            code: Строка с кодом
            
        Returns:
            BindingCode или None если невалидно
        """
        try:
            return cls(code)
        except ValueError:
            return None
