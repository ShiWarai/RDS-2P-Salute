"""
Модуль для управления роботом-пандой.
Обрабатывает голосовые команды и отправляет их на моторы робота.
"""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)


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


class RobotController:
    """Контроллер для управления роботом-пандой"""
    
    def __init__(self, robot_api_url: Optional[str] = None):
        """
        Инициализация контроллера робота
        
        Args:
            robot_api_url: URL API робота для отправки команд (опционально)
        """
        self.robot_api_url = robot_api_url
        logger.info(f"RobotController initialized. Robot API URL: {robot_api_url or 'Not configured'}")
    
    def parse_command(self, utterance: str) -> RobotCommand:
        """
        Распознает команду из текста пользователя в формате "скажи роботу <действие>"
        
        Args:
            utterance: Текст команды пользователя
            
        Returns:
            RobotCommand: Тип команды
        """
        utterance_lower = utterance.lower().strip()
        
        # Извлекаем действие из фразы "скажи роботу <действие>" или "скажи роботу панде <действие>"
        # Варианты: "скажи роботу", "скажи роботу панде", "скажи панде", "роботу"
        action = utterance_lower
        
        # Убираем префиксы команд
        prefixes = [
            "скажи роботу панде",
            "скажи роботу",
            "скажи панде",
            "скажи роботу панда",
            "скажи панда",
            "роботу панде",
            "роботу панда",
            "роботу",
            "панде",
            "панда"
        ]
        
        for prefix in prefixes:
            if utterance_lower.startswith(prefix):
                action = utterance_lower[len(prefix):].strip()
                break
        
        # Если не нашли префикс, пробуем найти команду напрямую
        if action == utterance_lower:
            # Проверяем, есть ли команда без префикса (для обратной совместимости)
            pass
        
        # Словарь ключевых слов для каждой команды
        command_keywords = {
            RobotCommand.LIE_DOWN: ["лежать", "ляг", "лечь", "приляг", "усни", "ложись"],
            RobotCommand.STAND_UP: ["вставай", "встань", "встать", "поднимайся", "поднимись"],
            RobotCommand.ATTENTION: ["равняйсь", "равняйся", "внимание", "смирно"],
            RobotCommand.HELP: ["помощь", "помоги", "что ты умеешь", "что умеешь", "команды", "список команд", "что можно"],
            RobotCommand.SILENCE: ["молчи", "замолчи", "хватит", "стоп", "прекрати слушать"]
        }
        
        # Ищем команду в извлеченном действии или в исходной фразе
        search_text = action if action != utterance_lower else utterance_lower
        
        for command, keywords in command_keywords.items():
            if any(keyword in search_text for keyword in keywords):
                return command
        
        return RobotCommand.UNKNOWN
    
    def get_motor_command(self, command: RobotCommand) -> Dict[str, Any]:
        """
        Генерирует команду для моторов робота
        
        Args:
            command: Тип команды
            
        Returns:
            Dict с параметрами команды для моторов
        """
        motor_commands = {
            RobotCommand.LIE_DOWN: {
                "action": "lie_down",
                "motors": {
                    "head": {"angle": 0, "speed": 50},
                    "body": {"angle": -90, "speed": 50},
                    "legs": {"angle": 0, "speed": 50}
                },
                "duration": 2000  # миллисекунды
            },
            RobotCommand.STAND_UP: {
                "action": "stand_up",
                "motors": {
                    "head": {"angle": 0, "speed": 50},
                    "body": {"angle": 0, "speed": 50},
                    "legs": {"angle": 0, "speed": 50}
                },
                "duration": 2000
            },
            RobotCommand.ATTENTION: {
                "action": "attention",
                "motors": {
                    "head": {"angle": 0, "speed": 100},
                    "body": {"angle": 0, "speed": 100},
                    "legs": {"angle": 0, "speed": 100}
                },
                "duration": 1000
            }
        }
        
        return motor_commands.get(command, {})
    
    async def send_command_to_robot(self, motor_command: Dict[str, Any]) -> bool:
        """
        Отправляет команду на моторы робота
        
        Args:
            motor_command: Команда для моторов
            
        Returns:
            bool: True если команда успешно отправлена
        """
        if not self.robot_api_url:
            logger.warning("Robot API URL not configured. Command logged but not sent.")
            logger.debug(f"Motor command (not sent): {motor_command}")
            return False
        
        if httpx is None:
            logger.error("httpx not installed. Cannot send command to robot.")
            return False
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.robot_api_url}/motors/command",
                    json=motor_command
                )
                response.raise_for_status()
                logger.info(f"Command sent to robot successfully")
                return True
        except Exception as e:
            logger.error(f"Failed to send command to robot: {e}", exc_info=True)
            return False
    
    def process_command(self, utterance: str) -> CommandResult:
        """
        Обрабатывает команду пользователя
        
        Args:
            utterance: Текст команды пользователя
            
        Returns:
            CommandResult: Результат обработки команды
        """
        command = self.parse_command(utterance)
        
        # Определяем текст ответа пользователю (для робота-панды)
        if command == RobotCommand.HELP:
            text = (
                "Я робот-панда 🐼! Доступные команды:\n"
                "• Скажи роботу лежать, вставай, равняйсь;\n"
                "• Помощь - список команд;\n"
                "• Молчи - прекратить прослушивание."
            )
        elif command == RobotCommand.SILENCE:
            text = "Хорошо, помолчим. 🐼👋"
        else:
            response_texts = {
                RobotCommand.LIE_DOWN: "Панда ложится отдыхать! 🐼💤",
                RobotCommand.STAND_UP: "Панда встаёт! 🐼✨",
                RobotCommand.ATTENTION: "Панда выравнивается по стойке смирно! 🐼🎖️",
                RobotCommand.UNKNOWN: "Хм, панда не поняла команду. Скажите 'помощь' для списка команд."
            }
            text = response_texts.get(command, "Не понял команду.")
        
        # Генерируем команду для моторов (только для команд, требующих движения)
        motor_command = self.get_motor_command(command) if command not in (RobotCommand.UNKNOWN, RobotCommand.HELP, RobotCommand.SILENCE) else None
        
        if motor_command:
            logger.debug(f"Command recognized: {command.value}")
        
        return CommandResult(
            command=command,
            text=text,
            motor_command=motor_command,
            success=command != RobotCommand.UNKNOWN,
            finished=(command == RobotCommand.SILENCE)  # Завершаем сессию только по команде "молчи"
        )
    
    async def execute_command(self, utterance: str) -> CommandResult:
        """
        Выполняет команду: обрабатывает и отправляет на робота
        
        Args:
            utterance: Текст команды пользователя
            
        Returns:
            CommandResult: Результат выполнения команды
        """
        result = self.process_command(utterance)
        
        # Если команда распознана, отправляем на робота
        if result.success and result.motor_command:
            send_success = await self.send_command_to_robot(result.motor_command)
            if not send_success:
                result.error_message = "Не удалось отправить команду роботу"
                logger.warning(f"Command execution failed: {result.error_message}")
        
        return result

