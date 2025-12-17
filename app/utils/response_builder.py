"""
Утилиты для создания ответов SmartApp API
"""
from typing import Dict, Any, List


def create_chatapp_response(
    data: Dict[str, Any],
    text: str,
    finished: bool = False
) -> Dict[str, Any]:
    """Создает ответ в формате ChatApp API с автопрослушиванием"""
    payload = {
        "items": [{
            "bubble": {
                "text": text,
                "expand_policy": "preserve_panel_state"
            }
        }],
        "pronounceText": text,
        "pronounceTextType": "application/text",
        "finished": finished
    }
    
    # Включаем автопрослушивание только если сессия не завершается
    if not finished:
        payload["auto_listening"] = True
    
    return {
        "messageId": data.get("messageId"),
        "sessionId": data.get("sessionId"),
        "uuid": data.get("uuid", {}),
        "messageName": "ANSWER_TO_USER",
        "payload": payload
    }


def create_chatapp_response_multiple(
    data: Dict[str, Any],
    texts: List[str],
    finished: bool = False
) -> Dict[str, Any]:
    """
    Создает ответ в формате ChatApp API с несколькими сообщениями
    
    Args:
        data: Данные входящего запроса
        texts: Список текстов для отправки (каждый будет отдельным сообщением)
        finished: Флаг завершения сессии
    """
    items = []
    all_text = ""
    
    for text in texts:
        items.append({
            "bubble": {
                "text": text,
                "expand_policy": "preserve_panel_state"
            }
        })
        if all_text:
            all_text += " "
        all_text += text
    
    payload = {
        "items": items,
        "pronounceText": all_text,
        "pronounceTextType": "application/text",
        "finished": finished
    }
    
    # Включаем автопрослушивание только если сессия не завершается
    if not finished:
        payload["auto_listening"] = True
    
    return {
        "messageId": data.get("messageId"),
        "sessionId": data.get("sessionId"),
        "uuid": data.get("uuid", {}),
        "messageName": "ANSWER_TO_USER",
        "payload": payload
    }


def create_legacy_response(
    text: str,
    session: Dict[str, Any],
    version: str,
    end_session: bool = False
) -> Dict[str, Any]:
    """Создает ответ в старом формате SmartApp API"""
    return {
        "response": {
            "text": text,
            "end_session": end_session
        },
        "version": version,
        "session": session
    }


