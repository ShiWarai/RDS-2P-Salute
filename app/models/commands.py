"""
Модели команд для робота
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional


class RobotCommand(Enum):
    """
    Типы команд для робота.
    
    Используется только для специальных команд, которые обрабатываются внутри системы.
    Реальные команды робота (give_paw, lie_down, rotate и т.д.) возвращаются как строки
    через CVC классификатор и не используют этот enum.
    """
    HELP = "help"  # Помощь
    SILENCE = "silence"  # Молчи - завершить прослушивание
    UNKNOWN = "unknown"  # Неизвестная команда (также используется для всех распознанных команд)
    ERROR = "error"  # Ошибка (например, CVC недоступен)


@dataclass
class CommandResult:
    """Результат обработки команды"""
    command: RobotCommand
    text: str  # Текст ответа пользователю
    motor_command: Optional[Dict[str, Any]] = None  # Команда для моторов
    success: bool = True
    error_message: Optional[str] = None
    finished: bool = False  # Флаг завершения сессии


