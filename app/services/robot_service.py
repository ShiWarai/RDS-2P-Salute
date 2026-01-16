"""
Сервис управления роботом-пандой.
Обрабатывает голосовые команды и отправляет их на моторы робота.
"""
import logging
import re
from typing import Dict, Any, Optional

from app.models.commands import RobotCommand, CommandResult
from app.config import CVC_SERVICE_URL
from app.services.cvc_client import CVCClient

logger = logging.getLogger(__name__)

# Список команд для отображения в справке
COMMANDS_FOR_HELP = [
    {'trigger': 'лапу', 'function': 'give_paw'},
    {'trigger': 'равняйсь', 'function': 'stand_at_attention'},
    {'trigger': 'отставить', 'function': 'dismiss'},
    {'trigger': 'вставай', 'function': 'dismiss'},
    {'trigger': 'лежать', 'function': 'lie_down'},
    {'trigger': ['кувырок', 'вращайся'], 'function': 'rotate'},
    {'trigger': ['бегать', 'пошли'], 'function': 'run'},
    {'trigger': 'смирно', 'function': 'stop_running'},
    {'trigger': ['держи джойстик', 'возьми джойстик', 'подключись к джойстику'], 'function': 'reconnect_joystick'}
]

# Специальные команды
_HELP_PATTERN = re.compile(r"(?:помощь|помоги|что\s+ты\s+умеешь|что\s+умеешь|команды|список\s+команд|что\s+можно)", re.IGNORECASE)
_SILENCE_PATTERN = re.compile(r"(?:молчи|молчать|замолчи|хватит|стоп|прекрати\s+слушать)", re.IGNORECASE)


class RobotService:
    """Сервис для управления роботом-пандой"""
    
    def __init__(self, robot_api_url: Optional[str] = None, cvc_service_url: Optional[str] = None):
        """
        Инициализация сервиса робота
        
        Args:
            robot_api_url: URL API робота для отправки команд (опционально, не используется с gRPC)
            cvc_service_url: URL CVC сервиса для классификации команд (по умолчанию из конфига)
        """
        self.robot_api_url = robot_api_url
        cvc_url = cvc_service_url or CVC_SERVICE_URL
        self.cvc_client = CVCClient(base_url=cvc_url)
        self._cvc_available = None  # Кэш для проверки доступности
        logger.info(f"RobotService инициализирован. Robot API URL: {robot_api_url or 'Не настроен (используется gRPC)'}, CVC URL: {cvc_url}")
    
    def _is_cvc_available(self) -> bool:
        """
        Проверяет доступность CVC сервиса (с кэшированием).
        
        Returns:
            True если CVC доступен, False иначе
        """
        if self._cvc_available is None:
            self._cvc_available = self.cvc_client.is_available()
            if self._cvc_available:
                logger.info("CVC сервис доступен, будет использоваться для классификации команд")
            else:
                logger.warning("CVC сервис недоступен - система будет сообщать об ошибках подключения")
        return self._cvc_available
    
    def parse_command(self, utterance: str) -> tuple[Optional[str], RobotCommand]:
        """
        Распознает команду из текста пользователя через CVC сервис.
        Если CVC недоступен, возвращает ошибку.
        
        Args:
            utterance: Текст команды пользователя
            
        Returns:
            tuple: (function_name или None, RobotCommand)
                   function_name - имя функции для отправки роботу (например, "dismiss")
                   RobotCommand - тип команды для внутренней обработки
        """
        utterance_lower = utterance.lower().strip()
        
        # Проверяем специальные команды (работают без CVC)
        if _HELP_PATTERN.search(utterance_lower):
            return None, RobotCommand.HELP
        
        if _SILENCE_PATTERN.search(utterance_lower):
            return None, RobotCommand.SILENCE
        
        # Проверяем доступность CVC сервиса
        if not self._is_cvc_available():
            logger.error(f"CVC сервис недоступен, невозможно классифицировать команду: '{utterance_lower}'")
            return None, RobotCommand.ERROR
        
        # Используем CVC сервис для классификации (передаем полный текст, CVC сам обработает префиксы)
        try:
            result = self.cvc_client.predict(utterance_lower, return_confidence=True)
            if result and result.get("command"):
                command = result.get("command")
                confidence = result.get("confidence", 0.0)
                
                # Игнорируем "unknown" команды от CVC
                if command != "unknown":
                    logger.debug(f"CVC классифицировал '{utterance_lower}' -> '{command}' (уверенность: {confidence:.3f})")
                    return command, RobotCommand.UNKNOWN
                else:
                    logger.debug(f"CVC классифицировал '{utterance_lower}' как 'unknown'")
                    return None, RobotCommand.UNKNOWN
            else:
                logger.warning(f"CVC вернул пустой результат для '{utterance_lower}'")
                return None, RobotCommand.ERROR
        except Exception as e:
            logger.error(f"Ошибка классификации CVC для '{utterance_lower}': {e}")
            return None, RobotCommand.ERROR
    
    def process_command(self, utterance: str) -> CommandResult:
        """
        Обрабатывает команду пользователя
        
        Args:
            utterance: Текст команды пользователя
            
        Returns:
            CommandResult: Результат обработки команды
        """
        function_name, command_type = self.parse_command(utterance)
        
        # Определяем текст ответа пользователю
        if command_type == RobotCommand.HELP:
            # Формируем список команд из единого хранилища
            help_lines = ["Доступные команды:"]
            for cmd in COMMANDS_FOR_HELP:
                triggers = cmd['trigger'] if isinstance(cmd['trigger'], list) else [cmd['trigger']]
                if len(triggers) > 1:
                    triggers_str = " или ".join([f"'{t}'" for t in triggers])
                    help_lines.append(f"• Скажи роботу {triggers_str};")
                else:
                    help_lines.append(f"• Скажи роботу '{triggers[0]}';")
            help_lines.extend([
                "• Команда 'Привяжи робота один' (или два, три и т.д.);",
                "• Команда 'Отвяжи робота';",
                "• Команда 'Помощь';",
                "• Команда 'Молчи'."
            ])
            text = "\n".join(help_lines)
        elif command_type == RobotCommand.SILENCE:
            text = "Хорошо, помолчим. 🐼👋"
        elif command_type == RobotCommand.ERROR:
            text = "Извините, сервис классификации команд временно недоступен. Пожалуйста, попробуйте позже."
        elif function_name:
            # Команда распознана - определяем ответ пользователю по function
            response_texts = {
                'give_paw': "Робот поднимает лапу! 🐾",
                'stand_at_attention': "Робот равняется! 🎖️",
                'dismiss': "Робот встаёт! ✨",
                'lie_down': "Робот ложится! 💤",
                'rotate': "Робот делает кувырок! 🤸",
                'run': "Робот начинает бегать! 🏃",
                'stop_running': "Робот останавливается! 🛑",
                'reconnect_joystick': "Робот подключается к джойстику! 🎮"
            }
            text = response_texts.get(function_name, f"Команда '{function_name}' отправлена роботу.")
        else:
            text = "Хм, робот не понял команду. Скажите 'помощь' для списка команд."
        
        # Генерируем команду для отправки роботу (function на английском)
        command_text = function_name if function_name else None
        
        return CommandResult(
            command=command_type,
            text=text,
            motor_command={"function": command_text} if command_text else None,
            success=function_name is not None or command_type in (RobotCommand.HELP, RobotCommand.SILENCE),
            finished=(command_type == RobotCommand.SILENCE),
            error_message=text if command_type == RobotCommand.ERROR else None
        )
