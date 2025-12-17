"""Утилиты"""

from app.utils.request_parser import extract_utterance_chatapp, extract_utterance_legacy, extract_robot_id_from_bind_command, extract_code_from_utterance
from app.utils.response_builder import create_chatapp_response, create_chatapp_response_multiple, create_legacy_response

__all__ = [
    "extract_utterance_chatapp",
    "extract_utterance_legacy",
    "extract_robot_id_from_bind_command",
    "extract_code_from_utterance",
    "create_chatapp_response",
    "create_chatapp_response_multiple",
    "create_legacy_response",
]


