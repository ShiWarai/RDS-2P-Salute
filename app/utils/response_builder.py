"""
Утилиты для создания ответов SmartApp API
"""
from typing import Dict, Any, List, Optional


def create_chatapp_response(
    data: Dict[str, Any],
    text: str,
    finished: bool = False,
    auto_listening: Optional[bool] = None,
    show_suggestions: bool = True
) -> Dict[str, Any]:
    """
    Создает ответ в формате ChatApp API с автопрослушиванием
    
    Args:
        data: Данные входящего запроса
        text: Текст ответа
        finished: Флаг завершения сессии (если True, сессия полностью завершается)
        auto_listening: Флаг автопрослушивания (если None, определяется автоматически:
                       True если finished=False, False если finished=True)
    
    Примечание: SmartApp API имеет встроенный таймаут сессии (обычно 30-60 секунд).
    Мы не можем продлить сессию программно, так как сервер не может инициировать запросы.
    Единственный способ поддерживать сессию - чтобы пользователь периодически что-то говорил.
    """
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
    
    # Определяем автопрослушивание
    if auto_listening is None:
        # По умолчанию: включаем автопрослушивание только если сессия не завершается
        auto_listening = not finished
    else:
        # Явно заданное значение (для команды "молчи" можно установить False)
        pass
    
    # Устанавливаем автопрослушивание только если сессия не завершена
    # ВАЖНО: auto_listening=True не предотвращает таймаут сессии!
    # Таймаут контролируется платформой SmartApp API и обычно составляет 30-60 секунд
    if not finished:
        payload["auto_listening"] = auto_listening
        
        # Добавляем визуальные подсказки для напоминания пользователю о навыке
        # Это не решает проблему таймаута, но улучшает UX и может помочь
        # пользователю понять, что навык активен и готов к командам
        if show_suggestions:
            payload["suggestions"] = {
                "buttons": [
                    {
                        "title": "Помощь",
                        "action": {
                            "text": "помощь",
                            "type": "text"
                        }
                    }
                ]
            }
    
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


