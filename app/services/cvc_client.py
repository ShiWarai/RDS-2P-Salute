"""
Клиент для работы с CVC API сервисом классификации команд.
"""
import logging
import os
from typing import Optional, Dict, Any
import httpx

logger = logging.getLogger(__name__)


class CVCClient:
    """Клиент для работы с CVC API сервером классификации команд."""
    
    def __init__(self, base_url: Optional[str] = None, timeout: float = 2.0):
        """
        Инициализирует клиент.
        
        Args:
            base_url: Базовый URL API сервера. Если не указан, берется из CVC_SERVICE_URL или используется http://localhost:20001
            timeout: Таймаут запроса в секундах (по умолчанию: 2.0)
        """
        if base_url is None:
            base_url = os.getenv("CVC_SERVICE_URL", "http://localhost:20001")
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        logger.info(f"CVCClient инициализирован с base_url={self.base_url}, timeout={timeout}")
    
    def predict(self, text: str, return_confidence: bool = False) -> Optional[Dict[str, Any]]:
        """
        Классифицирует текст команды через CVC API.
        
        Args:
            text: Текст команды для классификации
            return_confidence: Возвращать ли уверенность
            
        Returns:
            Результат классификации с полями:
            - command: str - название команды (например, "give_paw", "stand_at_attention", "unknown")
            - confidence: Optional[float] - уверенность (если запрошено)
            None если сервис недоступен
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/predict",
                    json={"text": text, "return_confidence": return_confidence}
                )
                response.raise_for_status()
                result = response.json()
                logger.debug(f"Предсказание CVC для '{text}': {result}")
                return result
        except httpx.TimeoutException:
            logger.warning(f"Таймаут CVC сервиса для текста '{text}'")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP ошибка CVC сервиса для текста '{text}': {e}")
            return None
        except Exception as e:
            logger.error(f"Ошибка CVC сервиса для текста '{text}': {e}", exc_info=True)
            return None
    
    def is_available(self) -> bool:
        """
        Проверяет доступность CVC сервиса.
        
        Returns:
            True если сервис доступен, False иначе
        """
        try:
            with httpx.Client(timeout=1.0) as client:
                response = client.get(f"{self.base_url}/health")
                response.raise_for_status()
                health = response.json()
                return health.get("status") == "healthy" and health.get("model_loaded", False)
        except Exception as e:
            logger.debug(f"Проверка здоровья CVC сервиса не удалась: {e}")
            return False
