"""
API маршруты для SmartApp
"""
import json
import logging
import re
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
import httpx

from app.services.robot_service import RobotService
from app.services.binding_service import BindingService
from app.utils.request_parser import (
    extract_utterance_chatapp,
    extract_utterance_legacy,
    extract_robot_id_from_bind_command,
    extract_code_from_utterance,
    extract_number_tokens_from_tokenized,
    is_bind_command,
    is_unbind_command
)
from app.utils.response_builder import create_chatapp_response, create_chatapp_response_multiple, create_legacy_response
from app.config import get_robot_url

logger = logging.getLogger(__name__)

router = APIRouter()

# Константы
GREETING_MESSAGE = "Привет! Я робот-панда 🐼! Скажите 'скажи роботу лежать', 'вставай' или 'равняйсь'. Для списка команд - 'помощь'."


async def request_binding_code(user_id: str, robot_id: str) -> tuple[bool, str, Optional[str], Optional[float]]:
    """
    Запрашивает код верификации у робота
    
    Returns:
        tuple: (успех, сообщение, код, expires_at)
    """
    robot_url = get_robot_url(robot_id)
    if not robot_url:
        return False, f"Робот с номером {robot_id} не найден.", None, None
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{robot_url}/bind/request",
                json={"user_id": user_id, "robot_id": robot_id}
            )
            response.raise_for_status()
            result = response.json()
            code = result.get("code")
            expires_at = result.get("expires_at")
            
            if code and expires_at:
                return True, "Код запрошен", code, expires_at
            else:
                return False, "Робот не вернул код", None, None
                
    except httpx.ConnectError:
        return False, "Робот временно недоступен. Попробуйте позже.", None, None
    except httpx.TimeoutException:
        return False, "Превышено время ожидания ответа от робота.", None, None
    except Exception as e:
        logger.error(f"Error requesting binding code: {e}", exc_info=True)
        return False, "Ошибка при запросе кода", None, None


async def _handle_cancel_command(
    binding_service: BindingService,
    user_id: str,
    binding_state: Optional[str]
) -> tuple[str, bool]:
    """Обрабатывает команду отмены привязки"""
    if binding_state == "waiting_code":
        binding_service.cancel_binding(user_id)
        return "Привязка отменена. Можете начать заново.", False
    else:
        return "Нет активной операции для отмены.", False


async def _handle_code_input(
    binding_service: BindingService,
    user_id: str,
    utterance: str,
    message: Optional[Dict[str, Any]] = None
) -> tuple[Optional[str | List[str]], bool]:
    """Обрабатывает ввод кода верификации"""
    logger.debug(f"Извлечение кода из utterance: '{utterance}'")
    code = extract_code_from_utterance(utterance)
    
    # Если код не извлечён или выглядит подозрительно (все цифры одинаковые),
    # пробуем извлечь из tokenized_elements_list
    if (not code or (code and len(set(code)) == 1)) and message:
        logger.debug(f"Код не извлечён или подозрителен ({code}), пробуем tokenized_elements_list")
        tokenized = message.get("tokenized_elements_list", [])
        logger.debug(f"Tokenized elements для кода: {json.dumps(tokenized, ensure_ascii=False, indent=2)}")
        
        # Извлекаем все числовые токены используя общую функцию
        number_tokens = extract_number_tokens_from_tokenized(tokenized)
        
        # Если нашли ровно 4 числа, используем их как код
        if len(number_tokens) == 4:
            code = ''.join(number_tokens)
            logger.debug(f"Код извлечён из токенов: {code}")
    
    logger.debug(f"Извлеченный код: {code}")
    if code:
        success, message_text = binding_service.verify_binding_code(user_id, code)
        if success:
            binding_service.complete_binding(user_id)
            robot_id = binding_service.get_robot_id(user_id)
            # Возвращаем список из двух сообщений
            return [
                f"Робот {robot_id} успешно привязан! Теперь вы можете управлять им. 🐼",
                "Привет! Я робот-панда 🐼! Скажите 'скажи роботу лежать', 'вставай' или 'равняйсь'."
            ], False
        else:
            return message_text, False
    else:
        return "Сначала завершите привязку. Введите 4-значный код из логов робота или скажите 'отмена'.", False


async def _handle_bind_start(
    binding_service: BindingService,
    user_id: str,
    utterance: str
) -> tuple[str, bool]:
    """Обрабатывает начало процесса привязки"""
    # Проверяем, не привязан ли уже робот
    if binding_service.has_binding(user_id):
        robot_id = binding_service.get_robot_id(user_id)
        return f"У вас уже привязан робот {robot_id}. Для перепривязки скажите 'отвяжи робота', затем привяжите нового.", False
    
    # Извлекаем ID робота
    logger.debug(f"=== ИЗВЛЕЧЕНИЕ ID РОБОТА ===")
    logger.debug(f"utterance для extract_robot_id_from_bind_command: '{utterance}'")
    robot_id = extract_robot_id_from_bind_command(utterance)
    logger.debug(f"Извлеченный robot_id: {robot_id}")
    if not robot_id:
        return "Укажите номер робота. Например: 'привяжи робота один' или 'привяжи робота 1'.", False
    
    # Запрашиваем код у робота
    success, message_text, code, expires_at = await request_binding_code(user_id, robot_id)
    if success and code and expires_at:
        logger.debug(f"Сохранение состояния привязки: user_id={user_id}, robot_id={robot_id}, code={code}")
        binding_service.start_binding(user_id, robot_id, code, expires_at)
        return f"Введите 4-значный код из логов робота {robot_id}. Код действителен 5 минут. Для отмены скажите 'отмена'.", False
    else:
        return message_text, False


def _handle_unbind(
    binding_service: BindingService,
    user_id: str
) -> tuple[str, bool]:
    """Обрабатывает команду отвязки робота"""
    if binding_service.has_binding(user_id):
        robot_id = binding_service.get_robot_id(user_id)
        binding_service.unbind_robot(user_id)
        return f"Робот {robot_id} отвязан. Вы можете привязать другого робота.", False
    else:
        return "У вас нет привязанного робота.", False


async def handle_binding_flow(
    binding_service: BindingService,
    user_id: str,
    utterance: str,
    message: Optional[Dict[str, Any]] = None
) -> tuple[Optional[str | List[str]], bool]:
    """
    Обрабатывает процесс привязки робота
    
    Returns:
        tuple: (текст ответа или список текстов для множественных сообщений, finished) 
               или (None, False) если команда не связана с привязкой
    """
    utterance_lower = utterance.lower().strip()
    
    # Проверяем команду отмены (обрабатываем в любом состоянии)
    binding_state = binding_service.get_binding_state(user_id)
    if any(word in utterance_lower for word in ["отмена", "отменить", "отменить привязку"]):
        return await _handle_cancel_command(binding_service, user_id, binding_state)
    
    # Кэшируем состояние привязки (уже получено выше)
    logger.debug(f"Состояние привязки для user_id={user_id}: {binding_state}, utterance='{utterance}'")
    
    # Если ожидается код - проверяем ввод кода
    if binding_state == "waiting_code":
        return await _handle_code_input(binding_service, user_id, utterance, message)
    
    # Если нет активной привязки, проверяем команду начала привязки
    if is_bind_command(utterance):
        return await _handle_bind_start(binding_service, user_id, utterance)
    
    # Команда отвязки
    if is_unbind_command(utterance):
        return _handle_unbind(binding_service, user_id)
    
    # Команда не связана с привязкой
    return None, False


def get_robot_service() -> RobotService:
    """Dependency для получения RobotService"""
    from app.main import robot_service
    return robot_service


def get_binding_service() -> BindingService:
    """Dependency для получения BindingService"""
    from app.main import binding_service
    return binding_service


async def _process_command(
    binding_service: BindingService,
    robot_service: RobotService,
    user_id: Optional[str],
    utterance: str,
    message: Optional[Dict[str, Any]],
    is_new_session: bool,
    intent: str,
    data: Dict[str, Any],
    is_chatapp: bool = True,
    session: Optional[Dict[str, Any]] = None,
    version: str = "1.0"
) -> tuple[str, bool, Dict[str, Any]]:
    """
    Общая функция обработки команд для ChatApp и Legacy API
    
    Returns:
        tuple: (текст ответа, finished/end_session, response_payload)
    """
    finished = False
    
    if is_new_session or (is_chatapp and intent == "run_app" and not utterance):
        # Новая сессия - проверяем привязку
        if user_id and binding_service.has_binding(user_id):
            robot_id = binding_service.get_robot_id(user_id)
            if is_chatapp:
                text = f"Привет! Ваш робот {robot_id} готов к управлению. Скажите 'скажи роботу лежать', 'вставай' или 'равняйсь'."
            else:
                text = f"Привет! Ваш робот {robot_id} готов к управлению."
        else:
            text = "Привет! Для управления роботом сначала привяжите его. Скажите 'привяжи робота один' или 'привяжи робота 1'."
    elif utterance:
        # Обрабатываем команду
        logger.debug(f"=== ПЕРЕДАЧА В handle_binding_flow ===")
        logger.debug(f"utterance: '{utterance}'")
        binding_text, binding_finished = await handle_binding_flow(binding_service, user_id, utterance, message)
        logger.debug(f"Результат handle_binding_flow: text='{binding_text}', finished={binding_finished}")
        
        if binding_text is not None:
            # Для ChatApp API множественные сообщения отправляем отдельно
            if is_chatapp and isinstance(binding_text, list):
                response_payload = create_chatapp_response_multiple(data, binding_text, binding_finished)
                logger.info(f"Ответ: '{binding_text[0]}'")
                return binding_text[0], binding_finished, response_payload
            
            # Для Legacy API множественные сообщения объединяем
            if isinstance(binding_text, list):
                text = " ".join(binding_text)
            else:
                text = binding_text
            finished = binding_finished
        else:
            # Проверяем, есть ли привязка для обычных команд
            if user_id and binding_service.has_binding(user_id):
                robot_id = binding_service.get_robot_id(user_id)
                robot_url = get_robot_url(robot_id)
                result = await robot_service.execute_command(utterance, robot_url)
                text = result.text
                if result.error_message:
                    text = f"{text} {result.error_message}"
                finished = result.finished
            else:
                text = "Сначала привяжите робота. Скажите 'привяжи робота один' или 'привяжи робота 1'."
    else:
        if is_chatapp:
            if user_id and binding_service.has_binding(user_id):
                text = "Скажите команду для робота: 'скажи роботу лежать', 'вставай' или 'равняйсь'."
            else:
                text = "Для управления роботом привяжите его. Скажите 'привяжи робота один' или 'привяжи робота 1'."
        else:
            text = "Не понял команду."
    
    # Создаём response payload в зависимости от формата API
    if is_chatapp:
        response_payload = create_chatapp_response(data, text, finished)
    else:
        response_payload = create_legacy_response(text, session or {}, version, finished)
    
    return text, finished, response_payload


def log_user_command(user_visible_text: str, utterance: str, user_id: Optional[str] = None) -> None:
    """
    Единообразное логирование команд пользователя с контекстом
    
    Args:
        user_visible_text: Текст, который видит пользователь на экране
        utterance: Текст, используемый для обработки
        user_id: ID пользователя (опционально)
    """
    context = {}
    if user_id:
        context["user_id"] = user_id[:20] + "..." if len(user_id) > 20 else user_id
    
    if user_visible_text:
        log_msg = f"Команда (видимая пользователю): '{user_visible_text}'"
        if context:
            log_msg += f" | Контекст: {context}"
        logger.info(log_msg)
    
    if utterance != user_visible_text:
        logger.debug(f"Команда (для обработки): '{utterance}'")


@router.post("/salute")
async def webhook(
    request: Request,
    robot_service: RobotService = Depends(get_robot_service),
    binding_service: BindingService = Depends(get_binding_service)
) -> JSONResponse:
    """Основной endpoint для обработки запросов от SmartApp API"""
    try:
        data: Dict[str, Any] = await request.json()
        logger.debug(f"=== ПОЛНЫЙ ВХОДЯЩИЙ JSON ===")
        logger.debug(json.dumps(data, ensure_ascii=False, indent=2))
        
    except Exception as e:
        logger.error(f"Error parsing JSON: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid JSON")

    try:
        message_name = data.get("messageName", "")
        logger.debug(f"Message name: {message_name}")
        
        # Извлекаем user_id
        user_id = binding_service.get_user_id(data.get("uuid", {}))
        logger.debug(f"User ID: {user_id}")
        
        # Определяем формат запроса: новый ChatApp API или старый SmartApp API
        if message_name == "MESSAGE_TO_SKILL":
            # Новый формат ChatApp API
            payload = data.get("payload", {})
            message = payload.get("message", {})
            is_new_session = payload.get("new_session", False)
            intent = payload.get("intent", "")
            
            logger.debug(f"=== MESSAGE DATA ===")
            logger.debug(json.dumps(message, ensure_ascii=False, indent=2))
            logger.debug(f"is_new_session: {is_new_session}, intent: {intent}")
            
            # Логируем команду пользователя единообразно
            user_visible_text = message.get("human_normalized_text") or message.get("original_text", "")
            utterance = extract_utterance_chatapp(message)
            log_user_command(user_visible_text, utterance, user_id)
            
            # Детальная информация только в DEBUG режиме
            logger.debug(f"Все варианты текста: original='{message.get('original_text', '')}', "
                        f"human_normalized='{message.get('human_normalized_text', '')}', "
                        f"normalized='{message.get('normalized_text', '')}'")
            
            # Если в utterance есть num_token, заменяем на число из токенов
            # Это нужно сделать ПЕРВЫМ, до других обработок
            if "num_token" in utterance.lower():
                logger.debug(f"Обнаружен num_token в utterance")
                tokenized = message.get("tokenized_elements_list", [])
                logger.debug(f"=== TOKENIZED ELEMENTS (для num_token) ===")
                logger.debug(f"Tokenized JSON: {json.dumps(tokenized, ensure_ascii=False, indent=2)}")
                
                # Извлекаем числовые токены используя общую функцию
                number_tokens = extract_number_tokens_from_tokenized(tokenized)
                
                if number_tokens:
                    # Берём первое найденное число для замены num_token
                    value = number_tokens[0]
                    utterance = utterance.replace("num_token", str(value)).replace("NUM_TOKEN", str(value))
                    logger.debug(f"Заменен num_token на {value}")
                else:
                    logger.debug(f"Числовой токен не найден для num_token")
            
            # Извлекаем число из tokenized_elements_list для команд привязки
            # Это нужно, даже если normalized_text неправильно преобразовал число
            if any(word in utterance.lower() for word in ["привяжи", "привязать", "подключи", "настрой"]):
                # Проверяем, есть ли уже число в utterance
                if not re.search(r"(привяжи|привязать|подключи|настрой)\s+(робот|робота|панду)\s+\d+", utterance.lower()):
                    logger.debug(f"Числа нет в utterance, ищем в токенах")
                    tokenized = message.get("tokenized_elements_list", [])
                    logger.debug(f"=== TOKENIZED ELEMENTS (для извлечения числа) ===")
                    logger.debug(f"Tokenized JSON: {json.dumps(tokenized, ensure_ascii=False, indent=2)}")
                    
                    # Извлекаем числовые токены используя общую функцию
                    number_tokens = extract_number_tokens_from_tokenized(tokenized)
                    
                    if number_tokens:
                        # Берём первое найденное число
                        value = number_tokens[0]
                        logger.debug(f"Извлеченное число из токена: {value}")
                        # Заменяем последнее слово после "робот/робота" на число
                        old_utterance = utterance
                        utterance = re.sub(
                            r"(привяжи\s+робот|привязать\s+робот|привяжи\s+робота|привязать\s+робота|привяжи\s+панду|привязать\s+панду)\s+\w+",
                            rf"\1 {value}",
                            utterance.lower()
                        )
                        logger.debug(f"Utterance до замены: '{old_utterance}'")
                        logger.debug(f"Utterance после замены: '{utterance}'")
                    else:
                        logger.debug(f"Числовой токен не найден")
                else:
                    logger.debug(f"Число уже есть в utterance, замена не требуется")
            
            logger.debug(f"Финальный utterance для обработки: '{utterance}'")
            
            # Обрабатываем команду (общая логика для ChatApp API)
            text, finished, response_payload = await _process_command(
                binding_service, robot_service, user_id, utterance, message,
                is_new_session, intent, data, is_chatapp=True
            )
            
            # Логируем ответ бота
            logger.info(f"Ответ: '{text}'")
            
        else:
            # Старый формат SmartApp API (для обратной совместимости)
            session = data.get("session", {})
            req = data.get("request", {})
            version = data.get("version", "1.0")
            is_new_session = session.get("new", False)
            utterance = extract_utterance_legacy(data, req)
            
            # Логируем команду пользователя (для legacy API нет отдельного user_visible_text)
            if utterance:
                log_user_command(utterance, utterance, user_id)
            
            # Обрабатываем команду (общая логика для Legacy API)
            text, end_session, response_payload = await _process_command(
                binding_service, robot_service, user_id, utterance, None,
                is_new_session, "", data, is_chatapp=False, session=session, version=version
            )
            
            # Логируем ответ бота
            logger.info(f"Ответ: '{text}'")

        return JSONResponse(
            content=response_payload,
            media_type="application/json",
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
        
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "SmartApp API is running"}


@router.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@router.post("/robot/command")
async def robot_command(
    request: Request,
    robot_service: RobotService = Depends(get_robot_service)
) -> Dict[str, Any]:
    """
    Endpoint для тестирования команд робота.
    Принимает JSON с полем 'utterance' (текст команды).
    """
    try:
        data = await request.json()
        utterance = data.get("utterance", "")
        
        if not utterance:
            raise HTTPException(status_code=400, detail="Field 'utterance' is required")
        
        result = await robot_service.execute_command(utterance)
        
        return {
            "success": result.success,
            "command": result.command.value,
            "text": result.text,
            "motor_command": result.motor_command,
            "error_message": result.error_message
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in robot command endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

