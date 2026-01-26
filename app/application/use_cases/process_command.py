"""
Use Case для обработки команд пользователя
"""
import logging
from typing import Optional, List, Union

from app.domain.repositories.binding_repository import IBindingRepository
from app.domain.repositories.user_repository import IUserRepository
from app.domain.services.command_classifier import ICommandClassifier
from app.domain.services.robot_connector import IRobotConnector
from app.domain.value_objects.user_state import UserState
from app.application.dto.command_request import CommandRequestDTO
from app.application.dto.command_response import CommandResponseDTO
from app.application.use_cases.bind_robot import BindRobotUseCase
from app.application.use_cases.unbind_robot import UnbindRobotUseCase
from app.application.use_cases.get_help import GetHelpUseCase
from app.application.use_cases.handle_binding_flow import HandleBindingFlowUseCase
from app.utils.response_builder import create_chatapp_response, create_chatapp_response_multiple, create_legacy_response

logger = logging.getLogger(__name__)

# Список команд с полной информацией (из robot_service)
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


class ProcessCommandUseCase:
    """Use Case для обработки команд пользователя"""
    
    def __init__(
        self,
        user_repository: IUserRepository,
        binding_repository: IBindingRepository,
        command_classifier: ICommandClassifier,
        robot_connector: IRobotConnector,
        bind_robot_uc: BindRobotUseCase,
        unbind_robot_uc: UnbindRobotUseCase,
        get_help_uc: GetHelpUseCase,
        handle_binding_flow_uc: HandleBindingFlowUseCase
    ):
        """
        Инициализация use case
        
        Args:
            user_repository: Репозиторий пользователей
            binding_repository: Репозиторий привязок
            command_classifier: Классификатор команд
            robot_connector: Коннектор для связи с роботом
            bind_robot_uc: Use case для привязки робота
            unbind_robot_uc: Use case для отвязки робота
            get_help_uc: Use case для получения справки
            handle_binding_flow_uc: Use case для обработки потока привязки
        """
        self.user_repository = user_repository
        self.binding_repository = binding_repository
        self.command_classifier = command_classifier
        self.robot_connector = robot_connector
        self.bind_robot_uc = bind_robot_uc
        self.unbind_robot_uc = unbind_robot_uc
        self.get_help_uc = get_help_uc
        self.handle_binding_flow_uc = handle_binding_flow_uc
    
    async def execute(self, request: CommandRequestDTO) -> CommandResponseDTO:
        """
        Обрабатывает команду пользователя
        
        Args:
            request: Запрос на обработку команды
            
        Returns:
            Ответ с текстом и метаданными
        """
        finished = False
        text_or_messages: Union[str, List[str]] = ""
        
        # Определяем состояния пользователя заранее, чтобы использовать их при формировании ответа
        has_binding_state = False
        has_help_state = False
        has_command_detail_state = False
        
        if request.user_id:
            has_binding_state = self.user_repository.has_user_state(request.user_id, UserState.WAITING_CODE)
            has_help_state = self.user_repository.has_user_state(request.user_id, UserState.WAITING_HELP_SECTION)
            has_command_detail_state = self.user_repository.has_user_state(request.user_id, UserState.WAITING_COMMAND_DETAIL)
        
        if request.is_new_session or (request.is_chatapp and request.intent == "run_app" and not request.utterance):
            # Новая сессия - проверяем привязку
            if request.user_id and self.binding_repository.has_binding(request.user_id):
                robot_id = self.binding_repository.get_robot_id(request.user_id)
                text_or_messages = f"Привет! Ваш робот {robot_id.value if robot_id else 'неизвестно'} готов к управлению."
            else:
                text_or_messages = "Привяжите робота. Скажите 'привяжи робота 1' или 'привяжи панду 2'."
        elif request.utterance:
            # Если в режиме привязки (waiting_code) - обрабатываем с поддержкой помощи
            if has_binding_state:
                text_or_messages, finished = await self._handle_binding_mode(
                    request, has_help_state, has_command_detail_state
                )
            else:
                # Не в режиме привязки
                text_or_messages, finished = await self._handle_normal_mode(
                    request, has_help_state, has_command_detail_state
                )
        else:
            # Пустая команда
            if request.is_chatapp:
                if request.user_id and self.binding_repository.has_binding(request.user_id):
                    text_or_messages = "Скажите команду для робота. Для списка команд - 'помощь'."
                else:
                    text_or_messages = "Привяжите робота. Скажите 'привяжи робота 1' или 'привяжи панду 2'."
            else:
                text_or_messages = "Не понял команду."
        
        # Обрабатываем результат: может быть строка или список строк
        if isinstance(text_or_messages, list):
            # Множественные сообщения
            if request.is_chatapp:
                # Для ChatApp пытаемся использовать множественный формат, 
                # но для надежности логируем объединение
                response_payload = create_chatapp_response_multiple(request.data, text_or_messages, finished)
                text = "\n".join(text_or_messages)
            else:
                # Для legacy API объединяем сообщения
                text = " ".join(text_or_messages)
                response_payload = create_legacy_response(text, request.session or {}, request.version, finished)
        else:
            # Одно сообщение
            text = text_or_messages
            if request.is_chatapp:
                # Для команды "молчи" отключаем автопрослушивание (пауза диалога)
                auto_listening = None
                show_suggestions = False
                
                if "помолчим" in text.lower() and not finished:
                    auto_listening = False
                # Не показываем подсказки в режиме помощи или привязки
                elif has_help_state or has_command_detail_state or has_binding_state:
                    pass  # show_suggestions уже False
                # Показываем подсказки только после успешных команд робота
                # (определяем по тексту ответа из COMMANDS - содержит эмодзи и описание действия)
                elif any(emoji in text for emoji in ["🐾", "🎖️", "✨", "💤", "🤸", "🏃", "🛑", "🎮"]) and not finished:
                    show_suggestions = True
                
                response_payload = create_chatapp_response(request.data, text, finished, auto_listening, show_suggestions)
            else:
                response_payload = create_legacy_response(text, request.session or {}, request.version, finished)
        
        return CommandResponseDTO(
            text=text,
            finished=finished,
            response_payload=response_payload
        )
    
    async def _handle_binding_mode(
        self,
        request: CommandRequestDTO,
        has_help_state: bool,
        has_command_detail_state: bool
    ) -> tuple[Union[str, List[str]], bool]:
        """Обрабатывает команду в режиме привязки"""
        utterance_lower = request.utterance.lower().strip()
        
        if has_help_state:
            if "служеб" in utterance_lower:
                text = self.get_help_uc.get_service_commands_help()
                if request.user_id:
                    self.user_repository.remove_user_state(request.user_id, UserState.WAITING_HELP_SECTION)
                return text, False
            elif "исполняем" in utterance_lower:
                text = self.get_help_uc.get_robot_commands_help(request.user_id)
                if request.user_id:
                    self.user_repository.remove_user_state(request.user_id, UserState.WAITING_HELP_SECTION)
                return text, False
            else:
                # Не выбор раздела - обрабатываем через handle_binding_flow
                binding_text, binding_finished = await self.handle_binding_flow_uc.process(
                    request.user_id, request.utterance, request.message
                )
                if binding_text is not None:
                    # Возвращаем как есть (может быть список или строка)
                    return binding_text, binding_finished
                else:
                    return "Введите код привязки или скажите 'отмена'.", False
        
        elif has_command_detail_state:
            # Обработка выбора команды для описания
            command_name = self._extract_command_name(utterance_lower)
            description = self.get_help_uc.get_command_description(command_name)
            if description:
                if request.user_id:
                    self.user_repository.remove_user_state(request.user_id, UserState.WAITING_COMMAND_DETAIL)
                return description, False
            else:
                # Не удалось найти команду - обрабатываем через handle_binding_flow
                binding_text, binding_finished = await self.handle_binding_flow_uc.process(
                    request.user_id, request.utterance, request.message
                )
                if binding_text is not None:
                    # Возвращаем как есть (может быть список или строка)
                    return binding_text, binding_finished
                else:
                    if request.user_id:
                        self.user_repository.remove_user_state(request.user_id, UserState.WAITING_COMMAND_DETAIL)
                    return "Введите код привязки или скажите 'отмена'.", False
        
        else:
            # Проверяем, не запросил ли пользователь помощь (через классификатор)
            classification_result = self._classify_command(request.utterance)
            function_name = classification_result.get("function") if classification_result else None
            
            if function_name == "help" and "служебн" not in utterance_lower and "исполняем" not in utterance_lower:
                # Пользователь запросил помощь в режиме привязки
                if request.user_id:
                    self.user_repository.add_user_state(request.user_id, UserState.WAITING_HELP_SECTION)
                return self.get_help_uc.get_help_menu(), False
            else:
                # Обрабатываем через handle_binding_flow
                binding_text, binding_finished = await self.handle_binding_flow_uc.process(
                    request.user_id, request.utterance, request.message
                )
                if binding_text is not None:
                    # Возвращаем как есть (может быть список или строка)
                    return binding_text, binding_finished
                else:
                    return "Введите код привязки или скажите 'отмена'.", False
    
    async def _handle_normal_mode(
        self,
        request: CommandRequestDTO,
        has_help_state: bool,
        has_command_detail_state: bool
    ) -> tuple[Union[str, List[str]], bool]:
        """Обрабатывает команду в обычном режиме"""
        utterance_lower = request.utterance.lower().strip()
        
        # Проверяем команду отмены вне режима привязки
        if any(word in utterance_lower for word in ["отмена", "отменить", "отменить привязку"]):
            return "Нет активной операции для отмены.", False
        
        if has_help_state:
            if "служеб" in utterance_lower:
                text = self.get_help_uc.get_service_commands_help()
                if request.user_id:
                    self.user_repository.remove_user_state(request.user_id, UserState.WAITING_HELP_SECTION)
                return text, False
            elif "исполняем" in utterance_lower:
                text = self.get_help_uc.get_robot_commands_help(request.user_id)
                if request.user_id:
                    self.user_repository.remove_user_state(request.user_id, UserState.WAITING_HELP_SECTION)
                return text, False
            else:
                # Не выбор раздела - очищаем состояние и обрабатываем как обычную команду
                if request.user_id:
                    self.user_repository.remove_user_state(request.user_id, UserState.WAITING_HELP_SECTION)
                has_help_state = False
        
        elif has_command_detail_state:
            # Обработка выбора команды для описания
            command_name = self._extract_command_name(utterance_lower)
            description = self.get_help_uc.get_command_description(command_name)
            if description:
                if request.user_id:
                    self.user_repository.remove_user_state(request.user_id, UserState.WAITING_COMMAND_DETAIL)
                return description, False
            else:
                # Не удалось найти команду - очищаем состояние и обрабатываем как обычную команду
                if request.user_id:
                    self.user_repository.remove_user_state(request.user_id, UserState.WAITING_COMMAND_DETAIL)
                has_command_detail_state = False
        
        # Обрабатываем команду (если не было выбора раздела помощи и не было выбора команды)
        if not has_help_state and not has_command_detail_state:
            return await self._process_normal_command(request)
        
        return "Не понял команду.", False
    
    async def _process_normal_command(self, request: CommandRequestDTO) -> tuple[str, bool]:
        """Обрабатывает обычную команду (не привязка, не помощь)"""
        # Классифицируем команду
        classification_result = self._classify_command(request.utterance)
        
        if not classification_result:
            if not self.command_classifier.is_available():
                return "Извините, сервис классификации команд временно недоступен. Пожалуйста, попробуйте позже.", False
            return "Скажите 'помощь' для списка команд.", False
        
        function_name = classification_result.get("function")
        utterance_lower = request.utterance.lower().strip()
        
        # Обрабатываем служебные команды
        if function_name == "help":
            if "служебн" not in utterance_lower and "исполняем" not in utterance_lower:
                if request.user_id:
                    self.user_repository.add_user_state(request.user_id, UserState.WAITING_HELP_SECTION)
                return self.get_help_uc.get_help_menu(), False
        
        if function_name == "silence":
            # Команда "молчи" ставит диалог на паузу (finished=False, но auto_listening=False)
            # Это позволяет навыку остаться активным, но не слушать дальше
            return "Хорошо, помолчим. 🐼👋", False
        
        # Обрабатываем команды привязки/отвязки
        if function_name == "bind":
            # Извлекаем номер робота из utterance
            from app.utils.request_parser import extract_robot_id_from_bind_command
            robot_id_str = extract_robot_id_from_bind_command(request.utterance)
            if robot_id_str:
                success, message = await self.bind_robot_uc.start_binding(request.user_id, robot_id_str)
                return message, False
            else:
                from app.infrastructure.external.robot_connection_manager import get_connection_manager
                robots_list = get_connection_manager().get_available_robots_list()
                return f"Укажите номер робота. Доступные роботы: {robots_list}", False
        
        if function_name == "unbind":
            success, message = await self.unbind_robot_uc.execute(request.user_id)
            return message, False
        
        # Обрабатываем команды для робота
        if request.user_id and self.binding_repository.has_binding(request.user_id):
            if function_name and function_name not in ["help", "silence", "bind", "unbind"]:
                # Отправляем команду роботу
                success, message = self.robot_connector.send_command(request.user_id, function_name)
                if success:
                    # Используем текст ответа из COMMANDS
                    for cmd in COMMANDS:
                        if cmd['function'] == function_name:
                            return cmd['response_text'], False
                    return f"Команда '{function_name}' отправлена роботу.", False
                else:
                    return message, False
            else:
                return "Скажите 'помощь' для списка команд.", False
        else:
            return "Привяжите робота. Скажите 'привяжи робота 1' или 'привяжи панду 2'.", False
    
    def _classify_command(self, utterance: str) -> Optional[dict]:
        """
        Классифицирует команду через классификатор
        
        Returns:
            Словарь с результатами классификации или None
        """
        utterance_lower = utterance.lower().strip()
        
        if not self.command_classifier.is_available():
            logger.error(f"CVC сервис недоступен, невозможно классифицировать команду: '{utterance_lower}'")
            return None
        
        try:
            result = self.command_classifier.classify(utterance_lower)
            if result and result.get("function"):
                function = result.get("function")
                confidence = result.get("confidence", 0.0)
                
                # Обрабатываем служебные команды
                if function == "help":
                    logger.info(f"CVC классифицировал '{utterance_lower}' -> 'help' (уверенность: {confidence:.3f})")
                    return {"function": "help"}
                
                if function == "silence":
                    logger.info(f"CVC классифицировал '{utterance_lower}' -> 'silence' (уверенность: {confidence:.3f})")
                    return {"function": "silence"}
                
                # Команды привязки возвращаем как function_name
                if function in ["bind", "unbind", "cancel"]:
                    logger.info(f"CVC классифицировал '{utterance_lower}' -> '{function}' (уверенность: {confidence:.3f})")
                    return {"function": function}
                
                # Игнорируем "unknown" команды от CVC
                if function != "unknown":
                    logger.info(f"CVC классифицировал '{utterance_lower}' -> '{function}' (уверенность: {confidence:.3f})")
                    return {"function": function}
                else:
                    logger.warning(f"CVC классифицировал '{utterance_lower}' как 'unknown'")
                    return None
            else:
                logger.warning(f"CVC вернул пустой результат для '{utterance_lower}': {result}")
                return None
        except Exception as e:
            logger.error(f"Ошибка классификации CVC для '{utterance_lower}': {e}")
            return None
    
    def _extract_command_name(self, utterance_lower: str) -> str:
        """Извлекает название команды из utterance"""
        command_name = utterance_lower
        
        # Убираем префиксы типа "расскажи про", "про команду" и т.д.
        for prefix in ["расскажи про", "про команду", "про", "команда", "команду"]:
            if utterance_lower.startswith(prefix):
                command_name = utterance_lower[len(prefix):].strip()
                command_name = command_name.strip('"\'')
                break
        
        # Убираем кавычки если они есть
        command_name = command_name.strip('"\'')
        return command_name
