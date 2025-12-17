"""
Сервис управления роботом-пандой.
Обрабатывает голосовые команды и отправляет их на моторы робота.
"""
import logging
import re
from typing import Dict, Any, Optional

try:
    import httpx
except ImportError:
    httpx = None

from app.models.commands import RobotCommand, CommandResult

logger = logging.getLogger(__name__)

# Предкомпилированные регулярные выражения для команд (для производительности)
_COMMAND_PATTERNS = {
    RobotCommand.LIE_DOWN: re.compile(r"(?:лежать|ляг|лечь|приляг|усни|ложись)"),
    RobotCommand.STAND_UP: re.compile(r"(?:вставай|встань|встать|вставать|поднимайся|поднимись)"),
    RobotCommand.ATTENTION: re.compile(r"(?:равняйсь|равняйся|равняться|внимание|смирно)"),
    RobotCommand.HELP: re.compile(r"(?:помощь|помоги|что\s+ты\s+умеешь|что\s+умеешь|команды|список\s+команд|что\s+можно)"),
    RobotCommand.SILENCE: re.compile(r"(?:молчи|молчать|замолчи|хватит|стоп|прекрати\s+слушать)")
}


class RobotService:
    """Сервис для управления роботом-пандой"""
    
    def __init__(self, robot_api_url: Optional[str] = None):
        """
        Инициализация сервиса робота
        
        Args:
            robot_api_url: URL API робота для отправки команд (опционально)
        """
        self.robot_api_url = robot_api_url
        logger.info(f"RobotService initialized. Robot API URL: {robot_api_url or 'Not configured'}")
    
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
        
        # Ищем команду в извлеченном действии или в исходной фразе
        search_text = action if action != utterance_lower else utterance_lower
        
        # Проверяем предкомпилированные паттерны (более эффективно, чем any() с циклом)
        for command, pattern in _COMMAND_PATTERNS.items():
            if pattern.search(search_text):
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
    
    async def send_command_to_robot(self, motor_command: Dict[str, Any], robot_url: Optional[str] = None) -> bool:
        """
        Отправляет команду на моторы робота
        
        Args:
            motor_command: Команда для моторов
            robot_url: URL робота (если не указан, используется self.robot_api_url)
            
        Returns:
            bool: True если команда успешно отправлена
        """
        # Используем переданный URL или URL по умолчанию
        url = robot_url or self.robot_api_url
        
        if not url:
            logger.warning("Robot API URL not configured. Command logged but not sent.")
            logger.debug(f"Motor command (not sent): {motor_command}")
            return False
        
        if httpx is None:
            logger.error("httpx not installed. Cannot send command to robot.")
            return False
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{url}/motors/command",
                    json=motor_command
                )
                response.raise_for_status()
                logger.info(f"Command sent to robot successfully")
                return True
        except httpx.ConnectError:
            logger.error(f"Failed to connect to robot at {url}")
            return False
        except httpx.TimeoutException:
            logger.error(f"Timeout while connecting to robot at {url}")
            return False
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
                "Доступные команды:\n"
                "• Команда \"Скажи роботу лежать\";\n"
                "• Команда \"Скажи роботу вставай\";\n"
                "• Команда \"Скажи роботу равняйсь\";\n"
                "• Команда \"Привяжи робота один\" (или два, три и т.д.);\n"
                "• Команда \"Отвяжи робота\";\n"
                "• Команда \"Помощь\";\n"
                "• Команда \"Молчи\"."
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
    
    async def execute_command(self, utterance: str, robot_url: Optional[str] = None) -> CommandResult:
        """
        Выполняет команду: обрабатывает и отправляет на робота
        
        Args:
            utterance: Текст команды пользователя
            robot_url: URL робота конкретного пользователя (опционально)
            
        Returns:
            CommandResult: Результат выполнения команды
        """
        result = self.process_command(utterance)
        
        # Если команда распознана, отправляем на робота
        if result.success and result.motor_command:
            send_success = await self.send_command_to_robot(result.motor_command, robot_url)
            if not send_success:
                result.error_message = "Не удалось отправить команду роботу"
                logger.warning(f"Command execution failed: {result.error_message}")
        
        return result


