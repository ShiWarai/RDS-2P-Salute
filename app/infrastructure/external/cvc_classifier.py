"""
Реализация ICommandClassifier через CVC API
"""
import logging
import os
from typing import Optional, Dict, Any
import httpx

from app.domain.services.command_classifier import ICommandClassifier

logger = logging.getLogger(__name__)


class CVCCClassifier(ICommandClassifier):
    """Реализация классификатора команд через CVC API"""
    
    def __init__(self, base_url: Optional[str] = None, timeout: float = 2.0):
        """
        Инициализирует классификатор
        
        Args:
            base_url: Базовый URL CVC API сервера
            timeout: Таймаут запроса в секундах
        """
        if base_url is None:
            base_url = os.getenv("CVC_SERVICE_URL", "http://localhost:20001")
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self._available = None  # Кэш для проверки доступности
        logger.info(f"CVCCClassifier инициализирован с base_url={self.base_url}, timeout={timeout}")
    
    def classify(self, utterance: str) -> Optional[Dict[str, Any]]:
        """Классифицирует команду пользователя"""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/v1/predict",
                    json={"text": utterance, "return_confidence": True}
                )
                response.raise_for_status()
                result = response.json()
                
                command = result.get("command")
                if command:
                    return {
                        "function": command,
                        "confidence": result.get("confidence")
                    }
                return None
        except Exception as e:
            logger.error(f"Ошибка классификации CVC для '{utterance}': {e}")
            return None
    
    def is_available(self) -> bool:
        """Проверяет доступность сервиса классификации"""
        if self._available is None:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(f"{self.base_url}/v1/health")
                    self._available = response.status_code == 200
                    if self._available:
                        logger.info("CVC сервис доступен, будет использоваться для классификации команд")
                    else:
                        logger.warning("CVC сервис недоступен - система будет сообщать об ошибках подключения")
            except Exception:
                self._available = False
                logger.warning("CVC сервис недоступен - система будет сообщать об ошибках подключения")
        return self._available
