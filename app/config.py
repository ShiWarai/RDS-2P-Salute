"""
Конфигурация приложения
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Определяем корень проекта
PROJECT_ROOT = Path(__file__).parent.parent
ROBOTS_CONFIG_FILE = PROJECT_ROOT / "config" / "robots.json"

robots_config: Dict[str, Dict[str, Any]] = {}


def load_robots_config() -> Dict[str, Dict[str, Any]]:
    """Загружает конфигурацию доступных роботов"""
    global robots_config
    if ROBOTS_CONFIG_FILE.exists():
        try:
            with open(ROBOTS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                robots_config = json.load(f)
            logger.info(f"Loaded {len(robots_config)} robots from config")
        except Exception as e:
            logger.error(f"Error loading robots config: {e}")
            robots_config = {}
    else:
        logger.warning(f"Robots config file not found: {ROBOTS_CONFIG_FILE}")
        robots_config = {}
    
    return robots_config


def get_robot_url(robot_id: str) -> str | None:
    """Получает URL робота по ID"""
    robot_info = robots_config.get(robot_id)
    if not robot_info:
        return None
    return robot_info.get("url")


def get_available_robots_list() -> str:
    """Возвращает строку со списком доступных роботов"""
    if not robots_config:
        return "Роботы не настроены"
    
    robot_list = []
    for robot_id, robot_info in robots_config.items():
        name = robot_info.get("name", f"Робот {robot_id}")
        robot_list.append(f"{robot_id} - {name}")
    
    return ", ".join(robot_list)


