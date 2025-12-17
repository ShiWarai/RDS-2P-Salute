"""
Утилиты для парсинга запросов
"""
import re
from typing import Dict, Any, Optional, List

# Предкомпилированные регулярные выражения для производительности

# Паттерны для команд привязки
_BIND_PATTERNS = [
    re.compile(r"привяжи\s+(?:робот|робота|роботу|панду|панда)?"),
    re.compile(r"привязать\s+(?:робот|робота|роботу|панду|панда)?"),
    re.compile(r"привязаться\s+(?:к\s+)?(?:робот|робота|роботу|панду|панда)?"),
    re.compile(r"подключи\s+(?:робот|робота|роботу|панду|панда)?"),
    re.compile(r"подключить\s+(?:робот|робота|роботу|панду|панда)?"),
    re.compile(r"настрой\s+(?:робот|робота|роботу|панду|панда)?"),
    re.compile(r"настроить\s+(?:робот|робота|роботу|панду|панда)?"),
]

# Паттерны для команд отвязки
_UNBIND_PATTERNS = [
    re.compile(r"отвяжи\s+(?:робот|робота|панду|панда)?"),
    re.compile(r"отвязать\s+(?:робот|робота|панду|панда)?"),
    re.compile(r"отвязаться\s*(?:от\s+)?(?:робот|робота|панду|панда)?"),
    re.compile(r"отключи\s+(?:робот|робота|панду|панда)?"),
    re.compile(r"отключить\s+(?:робот|робота|панду|панда)?"),
    re.compile(r"отключиться\s*(?:от\s+)?(?:робот|робота|панду|панда)?"),
]

# Паттерны для извлечения ID робота
_ROBOT_ID_PATTERNS = [
    re.compile(r"привязаться\s+к\s+(?:робот|робота|роботу|панду|панда)\s+(\d+)"),
    re.compile(r"(?:привяжи|привязать|привязаться|подключи|подключить|настрой|настроить)\s+(?:робот|робота|роботу|панду|панда)\s+(\d+)"),
    re.compile(r"(?:привяжи|привязать|привязаться|подключи|подключить|настрой|настроить)\s+(\d+)"),
    re.compile(r"(\d+)\s+(?:робот|робота|роботу|панду|панда)\s+(?:привяжи|привязать|привязаться|подключи|подключить|настрой|настроить)"),
]

# Паттерны для num_token (когда Сбер преобразует число)
_NUM_TOKEN_PATTERNS = [
    re.compile(r"(?:привяжи|привязать|привязаться|подключи|подключить|настрой|настроить)\s+(?:робот|робота|панду|панда)\s+num_token"),
    re.compile(r"привязаться\s+к\s+(?:робот|робота|панду|панда)\s+num_token"),
    re.compile(r"(?:привяжи|привязать|привязать|подключи|подключить|настрой|настроить)\s+num_token"),
]

# Паттерны для извлечения кода
_CODE_PATTERNS = [
    re.compile(r"код\s+(\d{4})"),
    re.compile(r"верификация\s+(\d{4})"),
    re.compile(r"^(\d{4})$"),
]

# Паттерн для поиска всех цифр
_DIGIT_PATTERN = re.compile(r'\d')


def extract_utterance_chatapp(message: Dict[str, Any]) -> str:
    """
    Извлекает текст команды из формата ChatApp API.
    
    Приоритет: human_normalized_text (то, что видит пользователь на экране),
    затем original_text, затем normalized_text (только если нужно преобразование чисел).
    
    Используем human_normalized_text в первую очередь, так как это то, что видит
    пользователь на экране и что он ожидает увидеть в логах.
    """
    # Сначала human_normalized_text - то, что видит пользователь на экране
    human_normalized = message.get("human_normalized_text", "")
    if human_normalized:
        return human_normalized.lower().strip()
    
    # Затем original_text
    original = message.get("original_text", "")
    if original:
        return original.lower().strip()
    
    # В конце normalized_text (может отличаться от того, что видит пользователь)
    normalized = message.get("normalized_text", "")
    if normalized:
        return normalized.lower().strip()
    
    return ""


def extract_utterance_legacy(data: Dict[str, Any], req: Dict[str, Any]) -> str:
    """Извлекает текст команды из старого формата SmartApp API"""
    return (
        req.get("original_utterance", "") or
        req.get("command", "") or
        data.get("original_utterance", "") or
        data.get("command", "") or
        ""
    ).lower()


def is_bind_command(utterance: str) -> bool:
    """
    Проверяет, является ли команда командой привязки робота.
    
    Поддерживает формы: привяжи, привязать, привязаться, подключи, подключить, настрой, настроить
    """
    utterance_lower = utterance.lower().strip()
    
    for pattern in _BIND_PATTERNS:
        if pattern.search(utterance_lower):
            return True
    
    return False


def is_unbind_command(utterance: str) -> bool:
    """
    Проверяет, является ли команда командой отвязки робота.
    
    Поддерживает формы: отвяжи, отвязать, отвязаться, отключи, отключить, отключиться
    """
    utterance_lower = utterance.lower().strip()
    
    for pattern in _UNBIND_PATTERNS:
        if pattern.search(utterance_lower):
            return True
    
    return False


def extract_robot_id_from_bind_command(utterance: str) -> Optional[str]:
    """
    Извлекает ID робота из команды привязки.
    Сбер может преобразовать числа в "num_token", поэтому обрабатываем оба случая.
    Поддерживает различные формы глаголов: привяжи, привязать, привязаться, подключи, подключить, настрой, настроить
    """
    utterance_lower = utterance.lower().strip()
    
    # Сначала проверяем паттерны с числами
    for pattern in _ROBOT_ID_PATTERNS:
        match = pattern.search(utterance_lower)
        if match:
            return match.group(1)
    
    # Затем проверяем паттерны с num_token
    for pattern in _NUM_TOKEN_PATTERNS:
        if pattern.search(utterance_lower):
            # Если num_token не был заменен в routes.py, возвращаем None
            # чтобы пользователь получил подсказку
            return None
    
    return None


def extract_code_from_utterance(utterance: str) -> Optional[str]:
    """
    Извлекает 4-значный код из команды.
    Сбер автоматически преобразует слова в цифры, поэтому ищем только цифры.
    Поддерживает как "1234", так и "1 2 3 4" (с пробелами).
    """
    utterance_lower = utterance.lower().strip()
    
    # Сначала пробуем извлечь все цифры из utterance
    all_digits = _DIGIT_PATTERN.findall(utterance_lower)
    
    # Если нашли ровно 4 цифры, объединяем их
    if len(all_digits) == 4:
        code = ''.join(all_digits)
        return code
    
    # Проверяем паттерны: "код 1234", "1234", "верификация 1234" (без пробелов)
    for pattern in _CODE_PATTERNS:
        match = pattern.search(utterance_lower)
        if match:
            code = match.group(1)
            if len(code) == 4:
                return code
    
    return None


def extract_number_tokens_from_tokenized(tokenized_elements_list: List[Dict[str, Any]]) -> List[str]:
    """
    Извлекает все числовые токены из tokenized_elements_list.
    
    Args:
        tokenized_elements_list: Список токенизированных элементов от Сбера
        
    Returns:
        Список строк с числовыми значениями
    """
    number_tokens = []
    for token in tokenized_elements_list:
        token_type = token.get("token_type", "")
        token_value = token.get("token_value", {})
        
        if isinstance(token_value, dict) and "value" in token_value:
            value = token_value["value"]
            # Проверяем, что значение - число (может быть int или str с цифрами)
            if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
                number_tokens.append(str(value))
            # Также проверяем token_type
            elif "NUM" in token_type.upper():
                number_tokens.append(str(value))
    
    return number_tokens
