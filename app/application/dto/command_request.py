"""
DTO для запроса обработки команды
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class CommandRequestDTO:
    """DTO для запроса обработки команды"""
    user_id: Optional[str]
    utterance: str
    is_new_session: bool
    intent: str
    data: Dict[str, Any]  # Полные данные запроса для создания ответа
    message: Optional[Dict[str, Any]] = None
    is_chatapp: bool = True
    session: Optional[Dict[str, Any]] = None
    version: str = "1.0"
