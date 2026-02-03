"""
Настройки приложения
"""
import os
from typing import Optional


class Settings:
    """Настройки приложения"""
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # CVC Service
    CVC_SERVICE_URL: str = os.getenv("CVC_SERVICE_URL", "http://localhost:20001")
    CVC_TIMEOUT: float = 2.0
    
    # gRPC
    GRPC_PORT: int = int(os.getenv("GRPC_PORT", "50051"))
    
    # Binding
    CODE_EXPIRY_SECONDS: int = 300  # 5 минут
    MAX_BINDING_ATTEMPTS: int = 3

    # Command feedback («исправить команду»)
    LAST_COMMAND_TTL_SECONDS: int = int(os.getenv("LAST_COMMAND_TTL_SECONDS", "300"))


# Глобальный экземпляр настроек
settings = Settings()
