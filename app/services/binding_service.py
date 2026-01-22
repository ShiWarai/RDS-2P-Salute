"""
Сервис управления привязками пользователей к роботам
Использует Redis для хранения данных
"""
import os
import logging
import time
from typing import Optional, Dict, Any
import redis

logger = logging.getLogger(__name__)

CODE_EXPIRY_SECONDS = 300  # 5 минут

# Префиксы для ключей Redis
BINDINGS_PREFIX = "bindings:"
STATES_PREFIX = "binding_states:"


class BindingService:
    """Управление привязками пользователей к роботам через Redis"""
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Инициализация сервиса привязок
        
        Args:
            redis_url: URL подключения к Redis (по умолчанию из переменной окружения)
        """
        if redis_url is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            # Проверяем подключение
            self.redis_client.ping()
            logger.info(f"BindingService инициализирован (Redis: {redis_url})")
        except Exception as e:
            logger.error(f"Ошибка подключения к Redis: {e}")
            raise
    
    def get_user_id(self, uuid_data: Dict[str, Any]) -> Optional[str]:
        """
        Извлекает идентификатор пользователя из uuid
        
        Args:
            uuid_data: Объект uuid из запроса SmartApp API
            
        Returns:
            Идентификатор пользователя (sub или userId)
        """
        # Используем sub как основной идентификатор (более стабильный)
        user_id = uuid_data.get("sub") or uuid_data.get("userId")
        return user_id
    
    def has_binding(self, user_id: str) -> bool:
        """Проверяет, есть ли постоянная привязка для пользователя"""
        try:
            key = f"{BINDINGS_PREFIX}{user_id}"
            return self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Ошибка проверки привязки для user_id={user_id}: {e}")
            return False
    
    def get_robot_id(self, user_id: str) -> Optional[str]:
        """Получает ID привязанного робота для пользователя"""
        try:
            key = f"{BINDINGS_PREFIX}{user_id}"
            robot_id = self.redis_client.get(key)
            return robot_id if robot_id else None
        except Exception as e:
            logger.error(f"Ошибка получения robot_id для user_id={user_id}: {e}")
            return None
    
    def get_binding_state(self, user_id: str) -> Optional[str]:
        """Получает текущее состояние процесса привязки"""
        try:
            key = f"{STATES_PREFIX}{user_id}"
            
            # Проверяем существование ключа (TTL может истечь)
            if not self.redis_client.exists(key):
                logger.debug(f"User {user_id} not in binding_states")
                return None
            
            # Получаем expires_at из Hash
            expires_at_str = self.redis_client.hget(key, "expires_at")
            if not expires_at_str:
                return None
            
            expires_at = float(expires_at_str)
            current_time = time.time()
            
            logger.debug(f"Checking binding state for user {user_id}: expires_at={expires_at}, current_time={current_time}, diff={current_time - expires_at}")
            
            # Если TTL еще не истек, но expires_at уже прошел, удаляем вручную
            if current_time > expires_at:
                logger.info(f"Binding code expired for user {user_id}")
                self.cancel_binding(user_id)
                return None
            
            return "waiting_code"
        except Exception as e:
            logger.error(f"Ошибка получения состояния привязки для user_id={user_id}: {e}")
            return None
    
    def start_binding(self, user_id: str, robot_id: str, code: str, expires_at: float) -> bool:
        """Начинает процесс привязки - сохраняет состояние ожидания кода"""
        if not user_id or not robot_id or not code:
            logger.error("User ID, robot ID and code are required for binding")
            return False
        
        # Приводим код к строке и убираем пробелы
        code_str = str(code).strip()
        logger.debug(f"Сохранение кода привязки: '{code_str}' (type: {type(code_str).__name__})")
        
        try:
            key = f"{STATES_PREFIX}{user_id}"
            
            # Удаляем старое состояние, если есть
            self.redis_client.delete(key)
            
            # Сохраняем состояние в Hash
            self.redis_client.hset(key, mapping={
                "robot_id": robot_id,
                "code": code_str,
                "expires_at": str(expires_at),
                "attempts": "0"
            })
            
            # Устанавливаем TTL (expires_at - current_time, минимум 1 секунда)
            ttl = max(1, int(expires_at - time.time()))
            self.redis_client.expire(key, ttl)
            
            logger.info(f"Started binding process for user {user_id} to robot {robot_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка начала привязки для user_id={user_id}, robot_id={robot_id}: {e}")
            return False
    
    def get_binding_code(self, user_id: str) -> tuple[Optional[str], Optional[float]]:
        """
        Получает код и expires_at из состояния привязки
        
        Returns:
            tuple: (code, expires_at) или (None, None) если состояние не найдено или истекло
        """
        try:
            key = f"{STATES_PREFIX}{user_id}"
            
            # Проверяем существование ключа
            if not self.redis_client.exists(key):
                return None, None
            
            # Получаем данные из Hash
            state_data = self.redis_client.hgetall(key)
            if not state_data:
                return None, None
            
            # Проверяем истечение времени
            expires_at_str = state_data.get("expires_at")
            if not expires_at_str:
                return None, None
            
            expires_at = float(expires_at_str)
            if time.time() > expires_at:
                self.cancel_binding(user_id)
                return None, None
            
            code = state_data.get("code")
            return code, expires_at
        except Exception as e:
            logger.error(f"Ошибка получения кода привязки для user_id={user_id}: {e}")
            return None, None
    
    def verify_binding_code(self, user_id: str, code: str) -> tuple[bool, str]:
        """Проверяет код верификации"""
        try:
            key = f"{STATES_PREFIX}{user_id}"
            
            # Проверяем существование ключа
            if not self.redis_client.exists(key):
                return False, "Процесс привязки не начат"
            
            # Получаем данные из Hash
            state_data = self.redis_client.hgetall(key)
            if not state_data:
                return False, "Процесс привязки не начат"
            
            # Проверяем истечение времени
            expires_at_str = state_data.get("expires_at")
            if not expires_at_str:
                return False, "Процесс привязки не начат"
            
            expires_at = float(expires_at_str)
            if time.time() > expires_at:
                self.cancel_binding(user_id)
                return False, "Код истек. Начните привязку заново."
            
            # Проверяем код
            code_str = str(code).strip()
            stored_code_str = str(state_data.get("code", "")).strip()
            logger.debug(f"Проверка кода: введённый='{code_str}' (type: {type(code_str).__name__}), сохранённый='{stored_code_str}' (type: {type(stored_code_str).__name__})")
            
            if code_str != stored_code_str:
                # Увеличиваем счетчик попыток
                attempts = int(state_data.get("attempts", "0")) + 1
                self.redis_client.hset(key, "attempts", str(attempts))
                
                if attempts >= 3:
                    self.cancel_binding(user_id)
                    return False, "Превышено количество попыток. Начните привязку заново."
                else:
                    remaining = 3 - attempts
                    return False, f"Неверный код. Осталось попыток: {remaining}"
            
            # Код верный
            return True, "Код подтвержден"
        except Exception as e:
            logger.error(f"Ошибка проверки кода для user_id={user_id}: {e}")
            return False, "Ошибка проверки кода"
    
    def complete_binding(self, user_id: str) -> bool:
        """Завершает привязку - сохраняет постоянную привязку"""
        try:
            state_key = f"{STATES_PREFIX}{user_id}"
            binding_key = f"{BINDINGS_PREFIX}{user_id}"
            
            # Получаем состояние
            state_data = self.redis_client.hgetall(state_key)
            if not state_data:
                logger.error(f"No binding state found for user {user_id}")
                return False
            
            robot_id = state_data.get("robot_id")
            if not robot_id:
                logger.error(f"No robot_id in binding state for user {user_id}")
                return False
            
            # Сохраняем постоянную привязку (просто строка robot_id)
            self.redis_client.set(binding_key, robot_id)
            
            # Удаляем временное состояние
            self.redis_client.delete(state_key)
            
            logger.info(f"Completed binding: user {user_id} -> robot {robot_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка завершения привязки для user_id={user_id}: {e}")
            return False
    
    def cancel_binding(self, user_id: str) -> bool:
        """Отменяет процесс привязки"""
        try:
            key = f"{STATES_PREFIX}{user_id}"
            deleted = self.redis_client.delete(key)
            if deleted > 0:
                logger.info(f"Cancelled binding for user {user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка отмены привязки для user_id={user_id}: {e}")
            return False
    
    def unbind_robot(self, user_id: str) -> bool:
        """Отвязывает робота от пользователя"""
        try:
            key = f"{BINDINGS_PREFIX}{user_id}"
            deleted = self.redis_client.delete(key)
            if deleted > 0:
                logger.info(f"Unbound robot from user {user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка отвязки робота для user_id={user_id}: {e}")
            return False
    
    def get_binding_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Получает информацию о состоянии привязки для пользователя"""
        try:
            # Проверяем постоянную привязку
            binding_key = f"{BINDINGS_PREFIX}{user_id}"
            robot_id = self.redis_client.get(binding_key)
            
            if robot_id:
                return {
                    "has_binding": True,
                    "robot_id": robot_id,
                    "state": "completed"
                }
            
            # Проверяем временное состояние
            state_key = f"{STATES_PREFIX}{user_id}"
            if not self.redis_client.exists(state_key):
                return {
                    "has_binding": False,
                    "state": None
                }
            
            state_data = self.redis_client.hgetall(state_key)
            if not state_data:
                return {
                    "has_binding": False,
                    "state": None
                }
            
            # Проверяем, не истек ли код
            expires_at_str = state_data.get("expires_at")
            if expires_at_str:
                expires_at = float(expires_at_str)
                if time.time() > expires_at:
                    self.cancel_binding(user_id)
                    return {
                        "has_binding": False,
                        "state": None
                    }
            
            return {
                "has_binding": False,
                "robot_id": state_data.get("robot_id"),
                "state": "waiting_code",
                "attempts": int(state_data.get("attempts", "0"))
            }
        except Exception as e:
            logger.error(f"Ошибка получения информации о привязке для user_id={user_id}: {e}")
            return {
                "has_binding": False,
                "state": None
            }
