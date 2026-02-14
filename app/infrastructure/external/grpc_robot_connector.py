"""
Реализация IRobotConnector через gRPC
"""
import logging
import time
import uuid
import random
from typing import Tuple, Optional

try:
    from grpc_proto import robot_pb2
except ImportError:
    robot_pb2 = None

from app.domain.services.robot_connector import IRobotConnector
from app.domain.value_objects.robot_id import RobotId
from app.domain.value_objects.binding_code import BindingCode
from app.infrastructure.external.robot_connection_manager import get_connection_manager

logger = logging.getLogger(__name__)


class GrpcRobotConnector(IRobotConnector):
    """Реализация подключения к роботу через gRPC"""
    
    def __init__(self, binding_repository):
        """
        Инициализация коннектора
        
        Args:
            binding_repository: Репозиторий привязок для получения robot_id по user_id
        """
        self.binding_repository = binding_repository
        self.connection_manager = get_connection_manager()
        logger.info("GrpcRobotConnector инициализирован")
    
    def send_command(self, user_id: str, function_name: str) -> Tuple[bool, str]:
        """Отправляет команду роботу"""
        if robot_pb2 is None:
            return False, "gRPC протобуфы не загружены"
        
        # Получаем robot_id из привязки
        robot_id = self.binding_repository.get_robot_id(user_id)
        if not robot_id:
            return False, "Нет привязки для этого пользователя"
        
        robot_id_str = robot_id.value
        logger.debug(f"Проверка подключения робота: robot_id={robot_id_str}, подключенных роботов: {self.connection_manager.get_connected_robots()}")
        
        # Проверяем активное соединение
        if not self.connection_manager.is_connected(robot_id_str):
            logger.warning(f"Робот {robot_id_str} не найден в connection_manager. Подключенные роботы: {self.connection_manager.get_connected_robots()}")
            return False, "Робот не подключен."
        
        # Создаем команду
        command_message = robot_pb2.StreamMessage(
            command=robot_pb2.Command(
                command_text=function_name,
                timestamp=int(time.time()),
                command_id=str(uuid.uuid4())
            )
        )
        
        # Отправляем команду через очередь
        if self.connection_manager.send_message(robot_id.value, command_message):
            logger.info(f"Команда отправлена: user_id={user_id}, robot_id={robot_id.value}, command={function_name}")
            return True, "Команда отправлена"
        else:
            logger.error(f"Ошибка отправки команды: user_id={user_id}, robot_id={robot_id.value}")
            return False, "Не удалось отправить команду."
    
    def initiate_binding(
        self,
        user_id: str,
        robot_id: RobotId
    ) -> Tuple[bool, str, Optional[BindingCode], Optional[float]]:
        """Инициирует процесс привязки робота"""
        if robot_pb2 is None:
            return False, "gRPC протобуфы не загружены", None, None
        
        # Проверяем подключение робота
        if not self.connection_manager.is_connected(robot_id.value):
            return False, f"Робот {robot_id.value} не подключен.", None, None
        
        # Генерируем код
        import random
        code_value = str(random.randint(1000, 9999))
        code = BindingCode(code_value)
        
        # Вычисляем время истечения
        expires_at_float = time.time() + 300  # 5 минут
        expires_at_int = int(expires_at_float)
        
        # Создаем сообщение с кодом привязки
        binding_code_message = robot_pb2.StreamMessage(
            binding_code=robot_pb2.BindingCodeMessage(
                code=code.value,
                expires_at=expires_at_int
            )
        )
        
        # Отправляем код роботу
        if self.connection_manager.send_message(robot_id.value, binding_code_message):
            # Отправляем статус
            status_message = robot_pb2.StreamMessage(
                status=robot_pb2.StatusMessage(
                    status="binding_required",
                    message="Введите код привязки в колонке Сбер"
                )
            )
            self.connection_manager.send_message(robot_id.value, status_message)
            logger.info(f"[КОД ПРИВЯЗКИ] Пользователь {user_id} привязывается к роботу {robot_id.value}. Код: {code.value}")
            # Не показываем код пользователю - он должен посмотреть его в логах робота
            return True, f"Введите код для робота {robot_id.value}. Код отображается в логах робота.", code, expires_at_float
        else:
            return False, f"Не удалось отправить код роботу {robot_id.value}.", None, None
    
    def complete_binding_with_code(
        self,
        user_id: str,
        robot_id: RobotId
    ) -> Tuple[bool, str]:
        """Уведомляет робота об успешном завершении привязки"""
        if robot_pb2 is None:
            return False, "gRPC протобуфы не загружены"
            
        # Проверяем активное соединение
        if not self.connection_manager.is_connected(robot_id.value):
            logger.warning(f"Робот {robot_id.value} не подключен для отправки статуса завершения привязки")
            return True, "Привязка завершена (робот не в сети для получения уведомления)"
            
        # Отправляем статус роботу
        status_message = robot_pb2.StreamMessage(
            status=robot_pb2.StatusMessage(
                status="binding_completed",
                message=f"Пользователь {user_id} успешно привязан"
            )
        )
        
        if self.connection_manager.send_message(robot_id.value, status_message):
            logger.info(f"Уведомление о завершении привязки отправлено роботу: user_id={user_id}, robot_id={robot_id.value}")
            return True, "Уведомление отправлено роботу"
        else:
            return False, "Не удалось отправить уведомление роботу"
