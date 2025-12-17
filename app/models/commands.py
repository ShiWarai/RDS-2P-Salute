"""
Модели команд для робота
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional


class RobotCommand(Enum):
    """Типы команд для робота"""
    LIE_DOWN = "lie_down"  # Лежать
    STAND_UP = "stand_up"  # Встать
    ATTENTION = "attention"  # Равняйсь/Внимание
    HELP = "help"  # Помощь
    SILENCE = "silence"  # Молчи - завершить прослушивание
    UNKNOWN = "unknown"  # Неизвестная команда


@dataclass
class CommandResult:
    """Результат обработки команды"""
    command: RobotCommand
    text: str  # Текст ответа пользователю
    motor_command: Optional[Dict[str, Any]] = None  # Команда для моторов
    success: bool = True
    error_message: Optional[str] = None
    finished: bool = False  # Флаг завершения сессии


