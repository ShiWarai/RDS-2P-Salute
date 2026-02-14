"""
gRPC сервер для приема подключений от роботов
"""
import grpc
from concurrent import futures
import logging
import queue
from typing import Optional

try:
    from grpc_proto import robot_pb2
    from grpc_proto import robot_pb2_grpc
except ImportError:
    robot_pb2 = None
    robot_pb2_grpc = None

from app.domain.repositories.binding_repository import IBindingRepository
from app.infrastructure.external.robot_connection_manager import get_connection_manager

logger = logging.getLogger(__name__)


class RobotCommandServiceServicer(robot_pb2_grpc.RobotCommandServiceServicer):
    """Реализация gRPC сервиса для отправки команд роботам"""
    
    def __init__(self, binding_repository: IBindingRepository):
        """
        Инициализация сервиса
        
        Args:
            binding_repository: Репозиторий привязок
        """
        self.binding_repository = binding_repository
        self.connection_manager = get_connection_manager()
        logger.info("RobotCommandServiceServicer инициализирован")
    
    def StreamCommands(self, request, context):
        """
        Server Streaming RPC - отправка команд роботу
        
        Args:
            request: RobotConnectRequest с robot_id
            context: gRPC контекст запроса
            
        Yields:
            StreamMessage - сообщения для робота (коды привязки, команды, статусы)
        """
        robot_id = str(request.robot_id).strip() if request.robot_id else None
        
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
        logger.debug(f"Добавлено соединение для робота {robot_id} в connection_manager. Всего соединений: {self.connection_manager.get_connection_count()}")
        
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
                    # Проверяем, не закрыт ли контекст - продолжаем цикл
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


def serve_grpc(binding_repository: IBindingRepository, port: int = 50051):
    """
    Запускает gRPC сервер
    
    Args:
        binding_repository: Репозиторий привязок
        port: Порт для gRPC сервера
    """
    if robot_pb2 is None or robot_pb2_grpc is None:
        logger.error("gRPC протобуфы не загружены, сервер не запущен")
        return
    
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    robot_pb2_grpc.add_RobotCommandServiceServicer_to_server(
        RobotCommandServiceServicer(binding_repository),
        server
    )
    
    listen_addr = f'[::]:{port}'
    server.add_insecure_port(listen_addr)
    server.start()
    logger.info(f"gRPC сервер запущен на порту {port}")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Остановка gRPC сервера...")
        server.stop(0)
