"""
Реализация ICommandFeedbackRepository через Redis
"""
import json
import logging
import os
from typing import Optional

import redis

from app.domain.repositories.command_feedback_repository import ICommandFeedbackRepository
from app.utils.redis_url import redact_redis_url

logger = logging.getLogger(__name__)

LAST_COMMAND_PREFIX = "last_command:"
FEEDBACK_LIST_KEY = "command_feedback:list"


class RedisCommandFeedbackRepository(ICommandFeedbackRepository):
    """Реализация репозитория обратной связи по командам через Redis"""

    def __init__(self, redis_url: Optional[str] = None, last_command_ttl: int = 300):
        """
        Args:
            redis_url: URL подключения к Redis
            last_command_ttl: TTL для ключа последней команды в секундах
        """
        if redis_url is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._redis_url = redis_url
        self._last_command_ttl = last_command_ttl
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info(
                "RedisCommandFeedbackRepository инициализирован (Redis: %s)",
                redact_redis_url(redis_url),
            )
        except Exception as e:
            logger.error("Ошибка подключения к Redis: %s", e)
            raise

    def set_last_command(
        self,
        user_id: str,
        utterance: str,
        function_name: str,
        ttl_seconds: int = 300,
    ) -> None:
        ttl = ttl_seconds if ttl_seconds > 0 else self._last_command_ttl
        try:
            key = f"{LAST_COMMAND_PREFIX}{user_id}"
            self.redis_client.hset(
                key,
                mapping={"utterance": utterance, "function_name": function_name},
            )
            self.redis_client.expire(key, ttl)
        except Exception as e:
            logger.error("Ошибка set_last_command для user_id=%s: %s", user_id, e)

    def get_last_command(self, user_id: str) -> Optional[tuple[str, str]]:
        try:
            key = f"{LAST_COMMAND_PREFIX}{user_id}"
            data = self.redis_client.hgetall(key)
            if data and "utterance" in data and "function_name" in data:
                return (data["utterance"], data["function_name"])
            return None
        except Exception as e:
            logger.error("Ошибка get_last_command для user_id=%s: %s", user_id, e)
            return None

    def clear_last_command(self, user_id: str) -> None:
        try:
            key = f"{LAST_COMMAND_PREFIX}{user_id}"
            self.redis_client.delete(key)
        except Exception as e:
            logger.error("Ошибка clear_last_command для user_id=%s: %s", user_id, e)

    def add_feedback(
        self,
        user_id: str,
        robot_id: str,
        user_utterance: str,
        classified_function: str,
        created_at: float,
        meta: Optional[dict] = None,
    ) -> None:
        try:
            record = {
                "user_id": user_id,
                "robot_id": robot_id,
                "user_utterance": user_utterance,
                "classified_function": classified_function,
                "created_at": created_at,
            }
            if meta is not None:
                record["meta"] = meta
            self.redis_client.rpush(FEEDBACK_LIST_KEY, json.dumps(record, ensure_ascii=False))
        except Exception as e:
            logger.error("Ошибка add_feedback для user_id=%s: %s", user_id, e)
            raise

    def get_all_feedback(self) -> list[dict]:
        try:
            raw = self.redis_client.lrange(FEEDBACK_LIST_KEY, 0, -1)
            result = []
            for item in raw or []:
                try:
                    result.append(json.loads(item))
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning("Пропуск невалидной записи feedback: %s", e)
            return result
        except Exception as e:
            logger.error("Ошибка get_all_feedback: %s", e)
            raise
