"""
Конфигурация приложения
"""
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Определяем корень проекта
PROJECT_ROOT = Path(__file__).parent.parent
ROBOTS_CONFIG_FILE = PROJECT_ROOT / "config" / "robots.json"

# URL CVC сервиса для классификации команд (можно переопределить через переменную окружения)
CVC_SERVICE_URL = os.getenv("CVC_SERVICE_URL", "http://localhost:20001")

# Кэш конфигурации роботов (опционально, для отображения имен)
_robots_config_cache: Optional[Dict[str, Dict[str, Any]]] = None


def get_robot_name(robot_id: str) -> str:
    """
    Получает имя робота по ID (опционально из конфига, если он существует)
    
    Args:
        robot_id: ID робота
        
    Returns:
        str: Имя робота или "Робот {robot_id}" по умолчанию
    """
    global _robots_config_cache
    
    # Загружаем конфиг только если он существует и еще не загружен
    if _robots_config_cache is None and ROBOTS_CONFIG_FILE.exists():
        try:
            import json
            with open(ROBOTS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                _robots_config_cache = json.load(f)
            logger.debug(f"Loaded robot names from config: {len(_robots_config_cache)} robots")
        except Exception as e:
            logger.debug(f"Could not load robots config: {e}")
            _robots_config_cache = {}
    
    if _robots_config_cache and robot_id in _robots_config_cache:
        return _robots_config_cache[robot_id].get("name", f"Робот {robot_id}")
    
    return f"Робот {robot_id}"


def get_available_robots_list() -> str:
    """
    Возвращает строку со списком доступных роботов (из подключенных через gRPC)
    
    Note: С gRPC роботы определяются динамически при подключении.
    Эта функция может использовать конфиг для отображения имен, если он существует.
    """
    from app.services.robot_connection_manager import get_connection_manager
    
    connection_manager = get_connection_manager()
    connected_robots = connection_manager.get_connected_robots()
    
    if not connected_robots:
        return "Нет подключенных роботов"
    
    robot_list = []
    for robot_id in connected_robots:
        name = get_robot_name(robot_id)
        robot_list.append(f"{robot_id} - {name}")
    
    return ", ".join(robot_list)
