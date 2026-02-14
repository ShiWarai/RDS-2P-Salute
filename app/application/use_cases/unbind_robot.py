"""
Use Case для отвязки робота
"""
import logging

from app.domain.repositories.binding_repository import IBindingRepository

logger = logging.getLogger(__name__)


class UnbindRobotUseCase:
    """Use Case для отвязки робота от пользователя"""
    
    def __init__(self, binding_repository: IBindingRepository):
        """
        Инициализация use case
        
        Args:
            binding_repository: Репозиторий привязок
        """
        self.binding_repository = binding_repository
    
    async def execute(self, user_id: str) -> tuple[bool, str]:
        """
        Отвязывает робота от пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Tuple (success, message)
        """
        if not self.binding_repository.has_binding(user_id):
            return False, "У вас нет привязанного робота."
        
        # Получаем robot_id перед отвязкой
        robot_id = self.binding_repository.get_robot_id(user_id)
        
        if self.binding_repository.unbind_robot(user_id):
            robot_id_str = robot_id.value if robot_id else "неизвестно"
            return True, f"Робот {robot_id_str} отвязан."
        else:
            return False, "Не удалось отвязать робота."
