"""
Use Case для обработки потока привязки
"""
import logging
import re
from typing import Optional, List, Tuple

from app.domain.repositories.binding_repository import IBindingRepository
from app.domain.repositories.user_repository import IUserRepository
from app.domain.value_objects.user_state import UserState
from app.domain.value_objects.binding_code import BindingCode
from app.utils.request_parser import extract_code_from_utterance, extract_number_tokens_from_tokenized
from app.application.use_cases.bind_robot import BindRobotUseCase

logger = logging.getLogger(__name__)


class HandleBindingFlowUseCase:
    """Use Case для обработки потока привязки (ввод кода, отмена)"""
    
    def __init__(
        self,
        binding_repository: IBindingRepository,
        user_repository: IUserRepository,
        bind_robot_uc: BindRobotUseCase
    ):
        """
        Инициализация use case
        
        Args:
            binding_repository: Репозиторий привязок
            user_repository: Репозиторий пользователей
            bind_robot_uc: Use case для привязки робота
        """
        self.binding_repository = binding_repository
        self.user_repository = user_repository
        self.bind_robot_uc = bind_robot_uc
    
    async def process(
        self,
        user_id: str,
        utterance: str,
        message: Optional[dict] = None
    ) -> Tuple[Optional[str | List[str]], bool]:
        """
        Обрабатывает команду в режиме привязки
        
        Args:
            user_id: ID пользователя
            utterance: Текст команды
            message: Дополнительные данные сообщения (для извлечения кода из tokenized)
            
        Returns:
            Tuple (текст ответа или список текстов, finished)
        """
        utterance_lower = utterance.lower().strip()
        
        # Проверяем команду отмены
        if any(word in utterance_lower for word in ["отмена", "отменить", "отменить привязку"]):
            success, message_text = await self.bind_robot_uc.cancel_binding(user_id)
            return message_text, False
        
        # Пытаемся извлечь код
        code = extract_code_from_utterance(utterance)
        
        # Если код не извлечён или выглядит подозрительно, пробуем извлечь из tokenized
        if (not code or (code and len(set(code)) == 1)) and message:
            logger.debug(f"Код не извлечён или подозрителен ({code}), пробуем tokenized_elements_list")
            tokenized = message.get("tokenized_elements_list", [])
            logger.debug(f"Tokenized elements для кода: {tokenized}")
            
            number_tokens = extract_number_tokens_from_tokenized(tokenized)
            
            if len(number_tokens) == 4:
                code = ''.join(number_tokens)
                logger.debug(f"Код извлечён из токенов: {code}")
        
        logger.debug(f"Извлеченный код: {code}")
        
        if code:
            # Проверяем код
            success, message_text = await self.bind_robot_uc.verify_code(user_id, code)
            if success:
                robot_id = self.binding_repository.get_robot_id(user_id)
                robot_id_str = robot_id.value if robot_id else "неизвестно"
                # Объединяем сообщения в одно, чтобы избежать проблем с форматом API
                combined_text = f"Робот {robot_id_str} привязан! 🐼\nПривет! Я робот-панда 🐼! Скажите команду для управления."
                return combined_text, False
            else:
                return message_text, False
        
        # Код не найден
        return None, False
