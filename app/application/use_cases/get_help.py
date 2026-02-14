"""
Use Case для получения справки
"""
import logging
from typing import Dict, List

from app.domain.value_objects.user_state import UserState
from app.domain.repositories.user_repository import IUserRepository

logger = logging.getLogger(__name__)

# Список команд с полной информацией (из robot_service, будет мигрирован)
COMMANDS = [
    {
        'trigger': 'лапу',
        'function': 'give_paw',
        'description': 'робот поднимет лапу',
        'response_text': "Робот поднимает лапу! 🐾"
    },
    {
        'trigger': 'равняйсь',
        'function': 'stand_at_attention',
        'description': 'робот выровняется по стойке смирно',
        'response_text': "Робот равняется! 🎖️"
    },
    {
        'trigger': 'отставить',
        'function': 'dismiss',
        'description': 'робот встанет',
        'response_text': "Робот встаёт! ✨"
    },
    {
        'trigger': 'вставай',
        'function': 'dismiss',
        'description': 'робот встанет',
        'response_text': "Робот встаёт! ✨"
    },
    {
        'trigger': 'лежать',
        'function': 'lie_down',
        'description': 'робот ляжет',
        'response_text': "Робот ложится! 💤"
    },
    {
        'trigger': ['кувырок', 'вращайся'],
        'function': 'rotate',
        'description': 'робот сделает кувырок',
        'response_text': "Робот делает кувырок! 🤸"
    },
    {
        'trigger': ['бегать', 'пошли'],
        'function': 'run',
        'description': 'робот начнет бегать',
        'response_text': "Робот начинает бегать! 🏃"
    },
    {
        'trigger': 'смирно',
        'function': 'stop_running',
        'description': 'робот остановится',
        'response_text': "Робот останавливается! 🛑"
    },
    {
        'trigger': ['держи джойстик', 'возьми джойстик', 'подключись к джойстику'],
        'function': 'reconnect_joystick',
        'description': 'робот подключится к джойстику',
        'response_text': "Робот подключается к джойстику! 🎮"
    }
]


class GetHelpUseCase:
    """Use Case для получения справки"""
    
    def __init__(self, user_repository: IUserRepository):
        """
        Инициализация use case
        
        Args:
            user_repository: Репозиторий пользователей
        """
        self.user_repository = user_repository
    
    def get_help_menu(self) -> str:
        """Возвращает меню выбора раздела помощи"""
        return "Выберите раздел: 'служебные' или 'исполняемые'."
    
    def get_service_commands_help(self) -> str:
        """Возвращает список служебных команд"""
        help_lines = ["Служебные команды:"]
        help_lines.extend([
            "'Привяжи робота 1' или 'Привяжи панду 2' - привязать робота;",
            "'Отвяжи робота' - отвязать робота;",
            "'Молчи' - временно остановить общение."
        ])
        return "\n".join(help_lines)
    
    def get_robot_commands_help(self, user_id: str = None) -> str:
        """Возвращает список команд управления роботом"""
        help_lines = ["Команды управления роботом:"]
        for cmd in COMMANDS:
            triggers = cmd['trigger'] if isinstance(cmd['trigger'], list) else [cmd['trigger']]
            # Показываем только первый вариант
            help_lines.append(f"• '{triggers[0]}'")
        
        help_lines.append("\nДля подробного описания скажите 'расскажи про \"название команды\"'.")
        
        # Устанавливаем состояние ожидания выбора команды для подробного описания
        if user_id:
            from app.domain.value_objects.user_state import UserState
            self.user_repository.add_user_state(user_id, UserState.WAITING_COMMAND_DETAIL)
        
        return "\n".join(help_lines)
    
    def get_command_description(self, command_name: str) -> str:
        """
        Возвращает подробное описание команды по названию
        
        Args:
            command_name: Название команды (триггер)
        
        Returns:
            Описание команды или None если команда не найдена
        """
        command_name_lower = command_name.lower().strip()
        
        # Ищем команду по триггеру
        for cmd in COMMANDS:
            triggers = cmd['trigger'] if isinstance(cmd['trigger'], list) else [cmd['trigger']]
            # Проверяем все варианты триггеров
            for trigger in triggers:
                if trigger.lower() == command_name_lower:
                    description = cmd.get('description', '')
                    if description:
                        return f"Команда '{trigger}':\n{description.capitalize()}."
                    else:
                        return f"Команда '{trigger}'"
        
        return None
