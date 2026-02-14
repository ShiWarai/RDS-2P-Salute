"""
Value Object для состояний пользователя
"""
from enum import Enum


class UserState(str, Enum):
    """Состояния пользователя в системе"""
    WAITING_CODE = "waiting_code"  # Ожидание кода привязки
    WAITING_HELP_SECTION = "waiting_help_section"  # Ожидание выбора раздела помощи
    WAITING_COMMAND_DETAIL = "waiting_command_detail"  # Ожидание выбора команды для описания
