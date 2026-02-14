"""
Главный файл приложения FastAPI
"""
import logging
import threading
import uvicorn
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.api.routes import router
from app.infrastructure.config.settings import settings
from app.infrastructure.external.grpc_server import serve_grpc
from app.infrastructure.persistence.redis_binding_repository import RedisBindingRepository

# Создаем директорию для логов
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

# Настраиваем логирование: все логи в файл, только важные в консоль
file_handler = logging.FileHandler(log_dir / "app.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[file_handler, console_handler],
)

logger = logging.getLogger(__name__)

GRPC_PORT = 50051


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Запуск gRPC и инициализация app.state при старте приложения (не при импорте)."""
    binding_repository = RedisBindingRepository(settings.REDIS_URL)
    app.state.binding_repository = binding_repository

    grpc_thread = threading.Thread(
        target=serve_grpc,
        args=(binding_repository, GRPC_PORT),
        daemon=True,
        name="gRPC-Server",
    )
    grpc_thread.start()
    logger.info("gRPC server thread started on port %s", GRPC_PORT)
    yield


app = FastAPI(title="Robot Panda SmartApp API", version="1.0.0", lifespan=lifespan)

# Подключение роутеров (версия в пути: /v1/...)
app.include_router(router)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
