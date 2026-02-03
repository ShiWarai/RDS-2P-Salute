"""
Главный файл приложения FastAPI
"""
import logging
import threading
import uvicorn
from fastapi import FastAPI

from app.api.routes import router
from app.infrastructure.external.grpc_server import serve_grpc

# Настройка логирования
import os
from pathlib import Path

# Создаем директорию для логов
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

# Настраиваем логирование: все логи в файл, только важные в консоль
file_handler = logging.FileHandler(log_dir / "app.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)  # Все логи в файл
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # Только важные в консоль
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

logging.basicConfig(
    level=logging.DEBUG,  # Минимальный уровень для всех обработчиков
    handlers=[file_handler, console_handler]
)

logger = logging.getLogger(__name__)

# Создание приложения FastAPI
app = FastAPI(title="Robot Panda SmartApp API", version="1.0.0")

# Создаём binding_repository для нового gRPC сервера
from app.infrastructure.persistence.redis_binding_repository import RedisBindingRepository
from app.infrastructure.config.settings import settings

binding_repository = RedisBindingRepository(settings.REDIS_URL)

# Запуск gRPC сервера в отдельном потоке
grpc_port = 50051
grpc_thread = threading.Thread(
    target=serve_grpc,
    args=(binding_repository, grpc_port),
    daemon=True,
    name="gRPC-Server"
)
grpc_thread.start()
logger.info(f"gRPC server thread started on port {grpc_port}")

# Подключение роутеров (версия в пути: /v1/...)
app.include_router(router)

logger.info("Application started")


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

