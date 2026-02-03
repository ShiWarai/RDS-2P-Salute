"""
Интерфейс репозитория обратной связи по командам (жалобы «исправить команду»)
"""
from abc import ABC, abstractmethod
from typing import Optional


class ICommandFeedbackRepository(ABC):
    """Интерфейс репозитория для хранения последней команды и жалоб пользователей"""

    @abstractmethod
    def set_last_command(
        self,
        user_id: str,
        utterance: str,
        function_name: str,
        ttl_seconds: int = 300,
    ) -> None:
        """
        Сохраняет последнюю выполненную команду пользователя (для контекста «исправить команду»).

        Args:
            user_id: ID пользователя
            utterance: Текст, который сказал пользователь
            function_name: Имя функции, которую выполнила система
            ttl_seconds: Время жизни записи в секундах
        """
        pass

    @abstractmethod
    def get_last_command(self, user_id: str) -> Optional[tuple[str, str]]:
        """
        Возвращает последнюю выполненную команду пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            (utterance, function_name) или None
        """
        pass

    @abstractmethod
    def clear_last_command(self, user_id: str) -> None:
        """
        Очищает последнюю команду пользователя после сохранения жалобы.

        Args:
            user_id: ID пользователя
        """
        pass

    @abstractmethod
    def add_feedback(
        self,
        user_id: str,
        robot_id: str,
        user_utterance: str,
        classified_function: str,
        created_at: float,
        meta: Optional[dict] = None,
    ) -> None:
        """
        Добавляет запись жалобы (команда сработала неправильно).

        Args:
            user_id: ID пользователя
            robot_id: ID робота
            user_utterance: Что сказал пользователь
            classified_function: Какую функцию выполнила система
            created_at: Unix timestamp
            meta: Дополнительные данные (session_id, device_id и т.д.)
        """
        pass

    @abstractmethod
    def get_all_feedback(self) -> list[dict]:
        """
        Возвращает все записи жалоб для выгрузки.

        Returns:
            Список словарей с полями: user_id, robot_id, user_utterance,
            classified_function, created_at, meta (опционально)
        """
        pass
