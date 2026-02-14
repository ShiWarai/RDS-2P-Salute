"""
Мок классификатора команд (без CVC) для тестов.
"""
from typing import Optional, Dict, Any

from app.domain.services.command_classifier import ICommandClassifier

DEFAULT_MAPPING = {
    "лапу": "give_paw",
    "помощь": "help",
    "молчи": "silence",
    "привяжи": "bind",
    "привязать": "bind",
    "отвяжи": "unbind",
    "отвязать": "unbind",
    "отмена": "cancel",
    "исправить": "report_command",
    "лежать": "lie_down",
    "вставай": "dismiss",
    "отставить": "dismiss",
    "равняйсь": "stand_at_attention",
    "кувырок": "rotate",
    "вращайся": "rotate",
    "бегать": "run",
    "пошли": "run",
    "смирно": "stop_running",
}


class MockClassifier(ICommandClassifier):
    """Заглушка ICommandClassifier для тестов. Не требует CVC."""

    def __init__(self, available: bool = True, mapping: Optional[Dict[str, str]] = None):
        self._available = available
        self._mapping = mapping or DEFAULT_MAPPING.copy()

    def is_available(self) -> bool:
        return self._available

    def classify(self, utterance: str) -> Optional[Dict[str, Any]]:
        if not self._available:
            return None
        u = utterance.lower().strip()
        for keyword, function in self._mapping.items():
            if keyword in u:
                return {"function": function, "confidence": 0.9}
        return None
