"""
DTO для ответа обработки команды
"""
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class CommandResponseDTO:
    """DTO для ответа обработки команды"""
    text: str
    finished: bool
    response_payload: Dict[str, Any]
