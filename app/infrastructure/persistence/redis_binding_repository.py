"""
Реализация IBindingRepository через Redis
"""
import os
import logging
import time
from typing import Optional, Tuple
import redis

from app.domain.repositories.binding_repository import IBindingRepository
from app.domain.value_objects.robot_id import RobotId
from app.domain.value_objects.binding_code import BindingCode
from app.domain.value_objects.user_state import UserState
from app.utils.redis_url import redact_redis_url

logger = logging.getLogger(__name__)

CODE_EXPIRY_SECONDS = 300  # 5 минут
BINDINGS_PREFIX = "bindings:"
BINDING_DATA_PREFIX = "binding_data:"
USER_STATES_PREFIX = "user_states:"


def _binding_key_to_user_id(key: str) -> str:
    """Из ключа bindings:user_id возвращает user_id."""
    if key.startswith(BINDINGS_PREFIX):
        return key[len(BINDINGS_PREFIX) :]
    return key


class RedisBindingRepository(IBindingRepository):
    """Реализация репозитория привязок через Redis"""
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Инициализация репозитория
        
        Args:
            redis_url: URL подключения к Redis (по умолчанию из переменной окружения)
        """
        if redis_url is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info(
                "RedisBindingRepository инициализирован (Redis: %s)",
                redact_redis_url(redis_url),
            )
        except Exception as e:
            logger.error(f"Ошибка подключения к Redis: {e}")
            raise
    
    def has_binding(self, user_id: str) -> bool:
        """Проверяет наличие привязки у пользователя"""
        try:
            key = f"{BINDINGS_PREFIX}{user_id}"
            return self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Ошибка проверки привязки для user_id={user_id}: {e}")
            return False
    
    def get_robot_id(self, user_id: str) -> Optional[RobotId]:
        """Получает ID привязанного робота"""
        try:
            key = f"{BINDINGS_PREFIX}{user_id}"
            robot_id_str = self.redis_client.get(key)
            if robot_id_str:
                return RobotId(robot_id_str)
            return None
        except Exception as e:
            logger.error(f"Ошибка получения robot_id для user_id={user_id}: {e}")
            return None
    
    def start_binding(
        self,
        user_id: str,
        robot_id: RobotId,
        code: BindingCode,
        expires_at: float
    ) -> bool:
        """Начинает процесс привязки"""
        try:
            # Удаляем старые данные привязки, если есть
            binding_data_key = f"{BINDING_DATA_PREFIX}{user_id}"
            self.redis_client.delete(binding_data_key)
            
            # Сохраняем данные привязки в Hash
            self.redis_client.hset(binding_data_key, mapping={
                "robot_id": robot_id.value,
                "code": code.value,
                "expires_at": str(expires_at),
                "attempts": "0"
            })
            
            # Добавляем состояние "waiting_code" через user_repository
            # Но здесь мы работаем напрямую с Redis для состояний
            states_key = f"{USER_STATES_PREFIX}{user_id}"
            self.redis_client.sadd(states_key, UserState.WAITING_CODE.value)
            
            # Устанавливаем TTL
            ttl = max(1, int(expires_at - time.time()))
            self.redis_client.expire(binding_data_key, ttl)
            self.redis_client.expire(states_key, ttl)
            
            logger.info(f"Начат процесс привязки пользователя {user_id} к роботу {robot_id.value}")
            return True
        except Exception as e:
            logger.error(f"Ошибка начала привязки для user_id={user_id}, robot_id={robot_id.value}: {e}")
            return False
    
    def get_binding_code(self, user_id: str) -> Optional[Tuple[BindingCode, float]]:
        """Получает код привязки и время истечения"""
        try:
            binding_data_key = f"{BINDING_DATA_PREFIX}{user_id}"
            if not self.redis_client.exists(binding_data_key):
                return None
            
            state_data = self.redis_client.hgetall(binding_data_key)
            if not state_data:
                return None
            
            expires_at_str = state_data.get("expires_at")
            if not expires_at_str:
                return None
            
            expires_at = float(expires_at_str)
            if time.time() > expires_at:
                self.cancel_binding(user_id)
                return None
            
            code_str = state_data.get("code")
            if code_str:
                code = BindingCode(code_str)
                return code, expires_at
            
            return None
        except Exception as e:
            logger.error(f"Ошибка получения кода привязки для user_id={user_id}: {e}")
            return None
    
    def verify_binding_code(self, user_id: str, code: BindingCode) -> Tuple[bool, str, int]:
        """Проверяет код верификации"""
        try:
            binding_data_key = f"{BINDING_DATA_PREFIX}{user_id}"
            if not self.redis_client.exists(binding_data_key):
                return False, "Процесс привязки не начат", 0
            
            state_data = self.redis_client.hgetall(binding_data_key)
            if not state_data:
                return False, "Процесс привязки не начат", 0
            
            # Проверяем истечение времени
            expires_at_str = state_data.get("expires_at")
            if not expires_at_str:
                return False, "Процесс привязки не начат", 0
            
            expires_at = float(expires_at_str)
            if time.time() > expires_at:
                self.cancel_binding(user_id)
                return False, "Код истек. Начните привязку заново.", 0
            
            # Проверяем код
            stored_code_str = str(state_data.get("code", "")).strip()
            if code.value != stored_code_str:
                # Увеличиваем счетчик попыток
                attempts = int(state_data.get("attempts", "0")) + 1
                self.redis_client.hset(binding_data_key, "attempts", str(attempts))
                
                if attempts >= 3:
                    self.cancel_binding(user_id)
                    return False, "Превышено количество попыток. Начните привязку заново.", attempts
                else:
                    remaining = 3 - attempts
                    return False, f"Неверный код. Осталось попыток: {remaining}", attempts
            
            # Код верный
            return True, "Код подтвержден", int(state_data.get("attempts", "0"))
        except Exception as e:
            logger.error(f"Ошибка проверки кода для user_id={user_id}: {e}")
            return False, "Ошибка проверки кода", 0
    
    def complete_binding(self, user_id: str) -> bool:
        """Завершает привязку - сохраняет постоянную привязку"""
        try:
            binding_data_key = f"{BINDING_DATA_PREFIX}{user_id}"
            state_data = self.redis_client.hgetall(binding_data_key)
            
            if not state_data:
                logger.error(f"Не найдено состояние привязки для пользователя {user_id}")
                return False
            
            robot_id_str = state_data.get("robot_id")
            if not robot_id_str:
                logger.error(f"Нет robot_id в состоянии привязки для пользователя {user_id}")
                return False
            
            # Сохраняем постоянную привязку
            binding_key = f"{BINDINGS_PREFIX}{user_id}"
            self.redis_client.set(binding_key, robot_id_str)
            
            # Удаляем временное состояние
            self.cancel_binding(user_id)
            
            logger.info(f"Привязка завершена: пользователь {user_id} -> робот {robot_id_str}")
            return True
        except Exception as e:
            logger.error(f"Ошибка завершения привязки для user_id={user_id}: {e}")
            return False
    
    def cancel_binding(self, user_id: str) -> bool:
        """Отменяет процесс привязки"""
        try:
            # Удаляем состояние из состояний пользователя
            states_key = f"{USER_STATES_PREFIX}{user_id}"
            self.redis_client.srem(states_key, UserState.WAITING_CODE.value)
            
            # Удаляем данные привязки
            binding_data_key = f"{BINDING_DATA_PREFIX}{user_id}"
            self.redis_client.delete(binding_data_key)
            
            logger.info(f"Привязка отменена для пользователя {user_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка отмены привязки для user_id={user_id}: {e}")
            return False
    
    def unbind_robot(self, user_id: str) -> bool:
        """Отвязывает робота от пользователя"""
        try:
            key = f"{BINDINGS_PREFIX}{user_id}"
            deleted = self.redis_client.delete(key)
            if deleted > 0:
                logger.info(f"Робот отвязан от пользователя {user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка отвязки робота для user_id={user_id}: {e}")
            return False

    def get_all_bindings(self) -> list[dict]:
        """
        Возвращает все постоянные привязки (для админ-просмотра).
        Ключи Redis: bindings:* без TTL — хранятся до явной отвязки или перезапуска без volume.
        """
        try:
            pattern = f"{BINDINGS_PREFIX}*"
            keys = self.redis_client.keys(pattern)
            out = []
            for key in keys:
                user_id = _binding_key_to_user_id(key)
                robot_id = self.redis_client.get(key)
                if robot_id:
                    out.append({"user_id": user_id, "robot_id": robot_id})
            return out
        except Exception as e:
            logger.error("Ошибка get_all_bindings: %s", e, exc_info=True)
            return []
