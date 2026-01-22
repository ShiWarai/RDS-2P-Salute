"""
gRPC сервис для работы с роботами
"""
import grpc
from concurrent import futures
import time
import random
import logging
import queue
import uuid
from typing import Optional, Tuple

try:
    from grpc_proto import robot_pb2
    from grpc_proto import robot_pb2_grpc
except ImportError:
    # Для случая, когда файлы еще не сгенерированы
    robot_pb2 = None
    robot_pb2_grpc = None

from app.services.binding_service import BindingService
from app.services.robot_connection_manager import RobotConnectionManager

logger = logging.getLogger(__name__)

# Глобальный экземпляр менеджера соединений
connection_manager: Optional[RobotConnectionManager] = None


def get_connection_manager() -> RobotConnectionManager:
    """Получает глобальный экземпляр менеджера соединений"""
    global connection_manager
    if connection_manager is None:
        connection_manager = RobotConnectionManager()
    return connection_manager


class RobotCommandServiceServicer(robot_pb2_grpc.RobotCommandServiceServicer):
    """Реализация gRPC сервиса для отправки команд роботам"""
    
    def __init__(self, binding_service: BindingService):
        """
        Инициализация сервиса
        
        Args:
            binding_service: Экземпляр BindingService для работы с привязками
        """
        self.binding_service = binding_service
        self.connection_manager = get_connection_manager()
        logger.info("RobotCommandServiceServicer инициализирован")
    
    def StreamCommands(self, request, context):
        """
        Server Streaming RPC - отправка команд роботу
        
        ВАЖНО: Робот подключается БЕЗ user_id. user_id появляется только
        когда пользователь запрашивает подключение через веб-хук колонки.
        
        Args:
            request: RobotConnectRequest с robot_id
            context: gRPC контекст запроса
        
        Yields:
            StreamMessage - сообщения для робота (коды привязки, команды, статусы)
        """
        robot_id = request.robot_id
        
        if not robot_id:
            logger.error("Робот подключился без robot_id")
            yield robot_pb2.StreamMessage(
                error=robot_pb2.ErrorMessage(
                    error_code="INVALID_REQUEST",
                    error_message="robot_id is required"
                )
            )
            return
        
        logger.info(f"Робот {robot_id} подключился")
        
        # Создаем очередь сообщений для этого робота
        message_queue = queue.Queue()
        self.connection_manager.add_connection(robot_id, message_queue)
        
        try:
            # Отправляем начальный статус
            yield robot_pb2.StreamMessage(
                status=robot_pb2.StatusMessage(
                    status="connected",
                    message="Робот подключен, ожидание команд"
                )
            )
            
            # Ожидаем сообщения из очереди и отправляем их роботу
            while context.is_active():
                try:
                    # Получаем сообщение из очереди с таймаутом
                    message = message_queue.get(timeout=1.0)
                    yield message
                except queue.Empty:
                    # Проверяем, не закрыт ли контекст
                    continue
                    
        except Exception as e:
            logger.error(f"Ошибка в stream для робота {robot_id}: {e}", exc_info=True)
            try:
                yield robot_pb2.StreamMessage(
                    error=robot_pb2.ErrorMessage(
                        error_code="STREAM_ERROR",
                        error_message=str(e)
                    )
                )
            except:
                pass
        finally:
            # Удаляем соединение при отключении
            self.connection_manager.remove_connection(robot_id)
            logger.info(f"Робот {robot_id} отключился")


def initiate_binding(user_id: str, robot_id: str, binding_service: BindingService) -> Tuple[bool, str]:
    """
    Инициирует процесс привязки пользователя к роботу.
    Вызывается когда пользователь через колонку запрашивает подключение к роботу.
    
    Args:
        user_id: ID пользователя (из веб-хука колонки)
        robot_id: ID робота (который пользователь выбрал)
        binding_service: Экземпляр BindingService
    
    Returns:
        (success: bool, message: str)
    """
    connection_manager = get_connection_manager()
    
    # Проверяем, подключен ли робот
    if not connection_manager.is_connected(robot_id):
        return False, f"Робот {robot_id} не подключен"
    
    # Проверяем, есть ли уже привязка
    if binding_service.has_binding(user_id):
        bound_robot_id = binding_service.get_robot_id(user_id)
        if bound_robot_id == robot_id:
            return True, "Робот уже привязан к этому пользователю"
        else:
            return False, f"Пользователь уже привязан к другому роботу ({bound_robot_id})"
    
    # Генерируем 4-значный код привязки
    code = str(random.randint(1000, 9999))
    expires_at = time.time() + 300  # 5 минут
    
    # Сохраняем состояние привязки
    binding_service.start_binding(
        user_id=user_id,
        robot_id=robot_id,
        code=code,
        expires_at=expires_at
    )
    
    logger.info(f"Инициация привязки: user_id={user_id}, robot_id={robot_id}, code={code}")
    
    # Отправляем код роботу через активное соединение
    binding_message = robot_pb2.StreamMessage(
        binding_code=robot_pb2.BindingCodeMessage(
            code=code,
            expires_at=expires_at
        )
    )
    
    if connection_manager.send_message(robot_id, binding_message):
        # Отправляем статус
        status_message = robot_pb2.StreamMessage(
            status=robot_pb2.StatusMessage(
                status="binding_required",
                message="Введите код привязки в колонке Сбер"
            )
        )
        connection_manager.send_message(robot_id, status_message)
        return True, f"Код привязки отправлен роботу: {code}"
    else:
        return False, f"Не удалось отправить код."


def complete_binding_with_code(user_id: str, code: str, binding_service: BindingService) -> Tuple[bool, str]:
    """
    Завершает процесс привязки после ввода кода пользователем.
    Вызывается когда пользователь вводит код в колонке.
    
    Args:
        user_id: ID пользователя (из веб-хука колонки)
        code: Код, введенный пользователем
        binding_service: Экземпляр BindingService
    
    Returns:
        (success: bool, message: str)
    """
    connection_manager = get_connection_manager()
    
    # Проверяем код
    is_valid, message = binding_service.verify_binding_code(user_id, code)
    
    if not is_valid:
        return False, message
    
    # Завершаем привязку
    binding_service.complete_binding(user_id)
    
    # Получаем robot_id
    robot_id = binding_service.get_robot_id(user_id)
    
    if not robot_id:
        return False, "Ошибка: не удалось получить robot_id после привязки"
    
    # Отправляем статус завершения привязки роботу
    if connection_manager.is_connected(robot_id):
        status_message = robot_pb2.StreamMessage(
            status=robot_pb2.StatusMessage(
                status="binding_completed",
                message="Привязка завершена успешно"
            )
        )
        connection_manager.send_message(robot_id, status_message)
    
    logger.info(f"Привязка завершена: user_id={user_id}, robot_id={robot_id}")
    return True, "Привязка завершена успешно"


def send_command_to_robot(user_id: str, command_text: str, binding_service: BindingService) -> Tuple[bool, str]:
    """
    Отправляет команду роботу, привязанному к пользователю.
    Вызывается когда пользователь отправляет команду через колонку.
    
    Args:
        user_id: ID пользователя (из веб-хука колонки)
        command_text: Текст команды
        binding_service: Экземпляр BindingService
    
    Returns:
        (success: bool, message: str)
    """
    connection_manager = get_connection_manager()
    
    # Получаем robot_id из привязки
    robot_id = binding_service.get_robot_id(user_id)
    if not robot_id:
        return False, "Нет привязки для этого пользователя"
    
    # Проверяем активное соединение
    if not connection_manager.is_connected(robot_id):
        return False, "Робот не подключен."
    
    # Создаем команду
    command_message = robot_pb2.StreamMessage(
        command=robot_pb2.Command(
            command_text=command_text,
            timestamp=int(time.time()),
            command_id=str(uuid.uuid4())
        )
    )
    
    # Отправляем команду через очередь
    if connection_manager.send_message(robot_id, command_message):
        logger.info(f"Команда отправлена: user_id={user_id}, robot_id={robot_id}, command={command_text}")
        return True, "Команда отправлена"
    else:
        logger.error(f"Ошибка отправки команды: user_id={user_id}, robot_id={robot_id}")
        return False, "Не удалось отправить команду."


def serve_grpc(binding_service: BindingService, port: int = 50051):
    """
    Запускает gRPC сервер
    
    Args:
        binding_service: Экземпляр BindingService
        port: Порт для gRPC сервера
    """
    if robot_pb2 is None or robot_pb2_grpc is None:
        logger.error("gRPC proto files not generated. Please run: python -m grpc_tools.protoc -I./grpc_proto --python_out=./grpc_proto --grpc_python_out=./grpc_proto ./grpc_proto/robot.proto")
        return
    
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    robot_pb2_grpc.add_RobotCommandServiceServicer_to_server(
        RobotCommandServiceServicer(binding_service),
        server
    )
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    logger.info(f"gRPC сервер запущен на порту {port}")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Остановка gRPC сервера...")
        server.stop(0)
