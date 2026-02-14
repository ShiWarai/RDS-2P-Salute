"""
Реализация IUserRepository через Redis
"""
import os
import logging
import time
from typing import Optional, Set
import redis

from app.domain.entities.user import User
from app.domain.repositories.user_repository import IUserRepository
from app.domain.value_objects.user_state import UserState

logger = logging.getLogger(__name__)

CODE_EXPIRY_SECONDS = 300  # 5 минут
USER_STATES_PREFIX = "user_states:"


class RedisUserRepository(IUserRepository):
    """Реализация репозитория пользователей через Redis"""
    
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
            logger.info(f"RedisUserRepository инициализирован (Redis: {redis_url})")
        except Exception as e:
            logger.error(f"Ошибка подключения к Redis: {e}")
            raise
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Получает пользователя по ID"""
        try:
            states = self.get_user_states(user_id)
            if states or self.redis_client.exists(f"{USER_STATES_PREFIX}{user_id}"):
                return User(user_id, states)
            return None
        except Exception as e:
            logger.error(f"Ошибка получения пользователя user_id={user_id}: {e}")
            return None
    
    def save_user(self, user: User) -> bool:
        """Сохраняет пользователя"""
        try:
            # Сохраняем состояния пользователя
            key = f"{USER_STATES_PREFIX}{user.user_id}"
            
            # Очищаем старые состояния
            self.redis_client.delete(key)
            
            # Добавляем новые состояния
            if user.states:
                for state in user.states:
                    self.redis_client.sadd(key, state.value)
                # Устанавливаем TTL
                self.redis_client.expire(key, CODE_EXPIRY_SECONDS)
            
            logger.debug(f"Сохранён пользователь {user.user_id} с состояниями: {user.states}")
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения пользователя user_id={user.user_id}: {e}")
            return False
    
    def get_user_states(self, user_id: str) -> Set[UserState]:
        """Получает все активные состояния пользователя"""
        try:
            key = f"{USER_STATES_PREFIX}{user_id}"
            if not self.redis_client.exists(key):
                return set()
            
            states_str = self.redis_client.smembers(key)
            states = set()
            for state_str in states_str:
                try:
                    states.add(UserState(state_str))
                except ValueError:
                    logger.warning(f"Неизвестное состояние: {state_str}")
            return states
        except Exception as e:
            logger.error(f"Ошибка получения состояний для user_id={user_id}: {e}")
            return set()
    
    def has_user_state(self, user_id: str, state: UserState) -> bool:
        """Проверяет наличие состояния у пользователя"""
        try:
            key = f"{USER_STATES_PREFIX}{user_id}"
            if not self.redis_client.exists(key):
                return False
            return self.redis_client.sismember(key, state.value)
        except Exception as e:
            logger.error(f"Ошибка проверки состояния {state} для user_id={user_id}: {e}")
            return False
    
    def add_user_state(self, user_id: str, state: UserState, ttl: int = CODE_EXPIRY_SECONDS) -> bool:
        """Добавляет состояние пользователю"""
        try:
            key = f"{USER_STATES_PREFIX}{user_id}"
            self.redis_client.sadd(key, state.value)
            self.redis_client.expire(key, ttl)
            logger.debug(f"Добавлено состояние '{state.value}' для пользователя {user_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления состояния {state} для user_id={user_id}: {e}")
            return False
    
    def remove_user_state(self, user_id: str, state: UserState) -> bool:
        """Удаляет состояние у пользователя"""
        try:
            key = f"{USER_STATES_PREFIX}{user_id}"
            removed = self.redis_client.srem(key, state.value)
            if removed > 0:
                logger.debug(f"Удалено состояние '{state.value}' для пользователя {user_id}")
                if self.redis_client.scard(key) == 0:
                    self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления состояния {state} для user_id={user_id}: {e}")
            return False
    
    def clear_user_states(self, user_id: str) -> bool:
        """Очищает все состояния пользователя"""
        try:
            key = f"{USER_STATES_PREFIX}{user_id}"
            deleted = self.redis_client.delete(key)
            if deleted > 0:
                logger.debug(f"Очищены все состояния для пользователя {user_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка очистки состояний для user_id={user_id}: {e}")
            return False
