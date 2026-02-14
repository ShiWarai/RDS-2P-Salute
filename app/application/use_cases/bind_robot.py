"""
Use Case для привязки робота
"""
import logging
from typing import Tuple, Optional

from app.domain.repositories.binding_repository import IBindingRepository
from app.domain.repositories.user_repository import IUserRepository
from app.domain.services.robot_connector import IRobotConnector
from app.domain.value_objects.robot_id import RobotId
from app.domain.value_objects.binding_code import BindingCode
from app.domain.value_objects.user_state import UserState

logger = logging.getLogger(__name__)


class BindRobotUseCase:
    """Use Case для привязки робота к пользователю"""
    
    def __init__(
        self,
        binding_repository: IBindingRepository,
        user_repository: IUserRepository,
        robot_connector: IRobotConnector
    ):
        """
        Инициализация use case
        
        Args:
            binding_repository: Репозиторий привязок
            user_repository: Репозиторий пользователей
            robot_connector: Коннектор для связи с роботом
        """
        self.binding_repository = binding_repository
        self.user_repository = user_repository
        self.robot_connector = robot_connector
    
    async def start_binding(self, user_id: str, robot_id_str: str) -> Tuple[bool, str]:
        """
        Начинает процесс привязки робота
        
        Args:
            user_id: ID пользователя
            robot_id_str: ID робота (строка)
            
        Returns:
            Tuple (success, message)
        """
        try:
            robot_id = RobotId(robot_id_str)
        except ValueError as e:
            return False, f"Неверный ID робота: {e}"
        
        # Проверяем, не привязан ли уже пользователь к какому-либо роботу
        if self.binding_repository.has_binding(user_id):
            bound_robot_id = self.binding_repository.get_robot_id(user_id)
            if bound_robot_id and bound_robot_id.value == robot_id.value:
                return True, f"Робот {robot_id.value} уже привязан к вашему аккаунту. Вы можете сразу управлять им."
            else:
                return False, f"К вашему аккаунту уже привязан другой робот ({bound_robot_id.value if bound_robot_id else 'неизвестно'}). Чтобы привязать нового, сначала скажите 'отвяжи робота'."
        
        # Инициируем привязку через коннектор
        success, message, code, expires_at = self.robot_connector.initiate_binding(user_id, robot_id)
        
        if success and code and expires_at:
            # Сохраняем состояние привязки
            if self.binding_repository.start_binding(user_id, robot_id, code, expires_at):
                # Добавляем состояние waiting_code пользователю
                self.user_repository.add_user_state(user_id, UserState.WAITING_CODE)
                logger.info(f"Инициация привязки: user_id={user_id}, robot_id={robot_id.value}, code={code.value}")
                return True, message
        
        return False, message or "Не удалось начать привязку"
    
    async def verify_code(self, user_id: str, code_str: str) -> Tuple[bool, str]:
        """
        Проверяет код верификации
        
        Args:
            user_id: ID пользователя
            code_str: Код верификации (строка)
            
        Returns:
            Tuple (success, message)
        """
        try:
            code = BindingCode(code_str)
        except ValueError:
            return False, "Код должен состоять из 4 цифр"
        
        # 1. Проверяем код в репозитории
        success, message, attempts = self.binding_repository.verify_binding_code(user_id, code)
        
        if success:
            # 2. Получаем ID робота из временных данных привязки
            # Нам нужно сделать это ДО завершения привязки, так как завершение удалит временные данные
            # Но подождите, у нас нет прямого метода получить robot_id из временных данных в репозитории.
            # Нам нужно добавить метод get_pending_robot_id или использовать существующий.
            
            # В текущей реализации RedisBindingRepository.get_robot_id(user_id) ищет в постоянных привязках.
            # Нам нужно получить робота, который СЕЙЧАС привязывается.
            # Для этого заглянем в данные привязки вручную или добавим метод.
            
            # Давайте посмотрим, что делает get_robot_id в репозитории.
            robot_id = self.binding_repository.get_robot_id(user_id)
            
            # Если робот еще не в постоянных привязках, попробуем достать его из временных
            if not robot_id:
                # Временно используем прямое знание о том, как лежат данные,
                # но правильнее было бы иметь метод в репозитории.
                # Однако, мы можем вызвать complete_binding ПЕРВЫМ, но тогда коннектор не должен зависеть от временных данных.
                pass

            # На самом деле, GrpcRobotConnector теперь не зависит от репозитория! 
            # Он просто принимает robot_id.
            
            # Давайте сначала завершим привязку в БД
            if self.binding_repository.complete_binding(user_id):
                # Теперь робот точно есть в постоянных привязках
                robot_id = self.binding_repository.get_robot_id(user_id)
                if robot_id:
                    # Уведомляем робота
                    self.robot_connector.complete_binding_with_code(user_id, robot_id)
                    
                    return True, f"Робот {robot_id.value} привязан! 🐼"
            
            return False, "Ошибка при завершении привязки"
        
        return False, message
    
    async def cancel_binding(self, user_id: str) -> Tuple[bool, str]:
        """
        Отменяет процесс привязки
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Tuple (success, message)
        """
        if self.binding_repository.cancel_binding(user_id):
            self.user_repository.remove_user_state(user_id, UserState.WAITING_CODE)
            return True, "Привязка отменена."
        return False, "Нет активной операции для отмены."
