"""
Главный файл приложения FastAPI
"""
import logging
import uvicorn
from fastapi import FastAPI

from app.api.routes import router
from app.services.robot_service import RobotService
from app.services.binding_service import BindingService
from app.config import load_robots_config

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

# Загрузка конфигурации
load_robots_config()

# Инициализация сервисов (глобальные экземпляры)
robot_service = RobotService()
binding_service = BindingService()

# Подключение роутеров
app.include_router(router)

logger.info("Application started")


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

