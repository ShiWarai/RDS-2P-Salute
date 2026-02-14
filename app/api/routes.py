"""
API маршруты для SmartApp
"""
import ipaddress
import json
import logging
import re
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse

from app.utils.request_parser import (
    extract_utterance_chatapp,
    extract_utterance_legacy,
    extract_robot_id_from_bind_command,
    extract_code_from_utterance,
    extract_number_tokens_from_tokenized,
    is_bind_command,
    is_unbind_command,
    extract_user_id
)
from app.utils.response_builder import create_chatapp_response, create_chatapp_response_multiple, create_legacy_response
from app.application.use_cases.process_command import ProcessCommandUseCase
from app.application.dto.command_request import CommandRequestDTO

logger = logging.getLogger(__name__)

router = APIRouter()


def get_process_command_use_case() -> ProcessCommandUseCase:
    """Dependency для получения ProcessCommandUseCase"""
    try:
        from app.infrastructure.persistence.redis_user_repository import RedisUserRepository
        from app.infrastructure.persistence.redis_binding_repository import RedisBindingRepository
        from app.infrastructure.persistence.redis_command_feedback_repository import RedisCommandFeedbackRepository
        from app.infrastructure.external.cvc_classifier import CVCCClassifier
        from app.infrastructure.external.grpc_robot_connector import GrpcRobotConnector
        from app.application.use_cases.bind_robot import BindRobotUseCase
        from app.application.use_cases.unbind_robot import UnbindRobotUseCase
        from app.application.use_cases.get_help import GetHelpUseCase
        from app.application.use_cases.handle_binding_flow import HandleBindingFlowUseCase
        from app.infrastructure.config.settings import settings

        # Создаём репозитории
        user_repository = RedisUserRepository(settings.REDIS_URL)
        binding_repository = RedisBindingRepository(settings.REDIS_URL)
        command_feedback_repository = RedisCommandFeedbackRepository(
            settings.REDIS_URL,
            last_command_ttl=settings.LAST_COMMAND_TTL_SECONDS,
        )
        
        # Создаём внешние сервисы
        command_classifier = CVCCClassifier(settings.CVC_SERVICE_URL, settings.CVC_TIMEOUT)
        robot_connector = GrpcRobotConnector(binding_repository)
        
        # Создаём use cases
        bind_robot_uc = BindRobotUseCase(binding_repository, user_repository, robot_connector)
        unbind_robot_uc = UnbindRobotUseCase(binding_repository)
        get_help_uc = GetHelpUseCase(user_repository)
        handle_binding_flow_uc = HandleBindingFlowUseCase(binding_repository, user_repository, bind_robot_uc)
        
        # Создаём главный use case
        process_command_uc = ProcessCommandUseCase(
            user_repository=user_repository,
            binding_repository=binding_repository,
            command_classifier=command_classifier,
            robot_connector=robot_connector,
            bind_robot_uc=bind_robot_uc,
            unbind_robot_uc=unbind_robot_uc,
            get_help_uc=get_help_uc,
            handle_binding_flow_uc=handle_binding_flow_uc,
            command_feedback_repository=command_feedback_repository,
        )

        return process_command_uc
    except Exception as e:
        logger.error(f"Ошибка создания ProcessCommandUseCase: {e}", exc_info=True)
        raise


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


@router.post("/v1/webhook")
async def webhook(
    request: Request,
    process_command_uc: ProcessCommandUseCase = Depends(get_process_command_use_case)
) -> JSONResponse:
    """Основной endpoint для обработки запросов от SmartApp API"""
    try:
        data: Dict[str, Any] = await request.json()
        logger.debug(f"=== ПОЛНЫЙ ВХОДЯЩИЙ JSON ===")
        logger.debug(json.dumps(data, ensure_ascii=False, indent=2))
        
    except Exception as e:
        logger.error(f"Ошибка парсинга JSON: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid JSON")

    try:
        message_name = data.get("messageName", "")
        logger.debug(f"Message name: {message_name}")
        
        # Извлекаем user_id
        user_id = extract_user_id(data.get("uuid", {}))
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
            logger.debug(f"Варианты текста: original='{message.get('original_text', '')}', "
                        f"human_normalized='{message.get('human_normalized_text', '')}', "
                        f"normalized='{message.get('normalized_text', '')}', "
                        f"utterance для обработки='{utterance}'")
            
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
            
            # Создаём DTO запроса
            command_request = CommandRequestDTO(
                user_id=user_id,
                utterance=utterance,
                is_new_session=is_new_session,
                intent=intent,
                data=data,
                message=message,
                is_chatapp=True
            )
            
            # Обрабатываем команду через use case
            command_response = await process_command_uc.execute(command_request)
            text = command_response.text
            finished = command_response.finished
            response_payload = command_response.response_payload
            
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
            
            # Создаём DTO запроса
            command_request = CommandRequestDTO(
                user_id=user_id,
                utterance=utterance,
                is_new_session=is_new_session,
                intent="",
                data=data,
                message=None,
                is_chatapp=False,
                session=session,
                version=version
            )
            
            # Обрабатываем команду через use case
            command_response = await process_command_uc.execute(command_request)
            text = command_response.text
            end_session = command_response.finished
            response_payload = command_response.response_payload
            
            # Логируем ответ бота
            logger.info(f"Ответ: '{text}'")

        return JSONResponse(
            content=response_payload,
            media_type="application/json",
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки запроса: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/v1/")
async def root():
    """Корень API (v1)."""
    return {"status": "ok", "message": "SmartApp API is running"}


@router.get("/v1/health")
async def health():
    """Проверка состояния сервера."""
    return {"status": "healthy"}


def _is_private_client_ip(request: Request) -> bool:
    """Проверяет, что запрос пришёл с частного/локального IP (доступ только из локальной сети)."""
    host = request.client.host if request.client else None
    if not host:
        return False
    if host == "::1":
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback
    except ValueError:
        return False


def require_local_network(request: Request) -> None:
    """Зависимость: разрешает доступ только с частных IP. Иначе 403."""
    if not _is_private_client_ip(request):
        logger.warning("Отклонён доступ к /v1/admin/* с IP: %s", getattr(request.client, "host", None))
        raise HTTPException(status_code=403, detail="Access allowed only from local network")


def get_binding_repository(request: Request):
    """Возвращает репозиторий привязок из app.state (один экземпляр на приложение)."""
    return request.app.state.binding_repository


def get_command_feedback_repository():
    """Dependency для получения репозитория обратной связи по командам."""
    from app.infrastructure.persistence.redis_command_feedback_repository import (
        RedisCommandFeedbackRepository,
    )
    from app.infrastructure.config.settings import settings

    return RedisCommandFeedbackRepository(
        settings.REDIS_URL,
        last_command_ttl=settings.LAST_COMMAND_TTL_SECONDS,
    )


@router.get("/v1/admin/command-feedback")
async def export_command_feedback(
    request: Request,
    _: None = Depends(require_local_network),
    repo=Depends(get_command_feedback_repository),
) -> JSONResponse:
    """
    Выгрузка записей обратной связи по командам («исправить команду»).

    Доступ только из локальной сети (частные IP). В Docker — из сети robot-services-network:
    http://rds-2p-salute-app:8000/v1/admin/command-feedback
    """
    try:
        items = repo.get_all_feedback()
        return JSONResponse(
            content=items,
            media_type="application/json",
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
    except Exception as e:
        logger.error("Ошибка выгрузки command-feedback: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
