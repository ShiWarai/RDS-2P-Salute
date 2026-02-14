"""
Интерфейс классификатора команд
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class ICommandClassifier(ABC):
    """Интерфейс для классификации команд пользователя"""
    
    @abstractmethod
    def classify(self, utterance: str) -> Optional[Dict[str, Any]]:
        """
        Классифицирует команду пользователя
        
        Args:
            utterance: Текст команды
            
        Returns:
            Словарь с результатами классификации:
            - function: str - имя функции (например, "give_paw", "help")
            - confidence: Optional[float] - уверенность классификации
            или None если сервис недоступен
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Проверяет доступность сервиса классификации
        
        Returns:
            True если сервис доступен
        """
        pass
