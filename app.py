import json
import logging
import os
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn

from robot_controller import RobotController

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

app = FastAPI()

logger = logging.getLogger(__name__)

# Инициализация контроллера робота
# URL робота можно задать через переменную окружения ROBOT_API_URL
robot_api_url = os.getenv("ROBOT_API_URL", None)
robot_controller = RobotController(robot_api_url=robot_api_url)

logger.info("Application started")

# Константы
GREETING_MESSAGE = "Привет! Я робот-панда 🐼! Скажите 'скажи роботу лежать', 'вставай' или 'равняйсь'. Для списка команд - 'помощь'."


def extract_utterance_chatapp(message: Dict[str, Any]) -> str:
    """Извлекает текст команды из формата ChatApp API"""
    return (
        message.get("original_text", "") or
        message.get("normalized_text", "") or
        message.get("human_normalized_text", "") or
        ""
    ).lower()


def extract_utterance_legacy(data: Dict[str, Any], req: Dict[str, Any]) -> str:
    """Извлекает текст команды из старого формата SmartApp API"""
    return (
        req.get("original_utterance", "") or
        req.get("command", "") or
        data.get("original_utterance", "") or
        data.get("command", "") or
        ""
    ).lower()


async def process_command_with_logging(utterance: str) -> tuple[str, bool]:
    """
    Обрабатывает команду через RobotController и логирует результат
    
    Returns:
        tuple: (текст ответа, флаг завершения сессии)
    """
    command_result = await robot_controller.execute_command(utterance)
    
    if command_result.success:
        logger.info(f"Command executed: {command_result.command.value}")
        if command_result.motor_command:
            logger.info(f"Motor command: {command_result.motor_command}")
        if command_result.finished:
            logger.info("Session will be finished")
    else:
        logger.warning(f"Command not recognized: '{utterance}'")
    
    return command_result.text, command_result.finished


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


@app.post("/salute")
async def webhook(request: Request) -> JSONResponse:
    try:
        # Получаем данные запроса
        data: Dict[str, Any] = await request.json()
        logger.info(f"Received request data: {data}")
        
    except Exception as e:
        logger.error(f"Error parsing JSON: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid JSON")

    try:
        message_name = data.get("messageName", "")
        logger.info(f"Message name: {message_name}")
        
        # Определяем формат запроса: новый ChatApp API или старый SmartApp API
        if message_name == "MESSAGE_TO_SKILL":
            # Новый формат ChatApp API
            payload = data.get("payload", {})
            message = payload.get("message", {})
            is_new_session = payload.get("new_session", False)
            intent = payload.get("intent", "")
            utterance = extract_utterance_chatapp(message)
            
            logger.info(f"ChatApp API: new_session={is_new_session}, intent={intent}, utterance='{utterance}'")
            
            # Определяем ответ
            if is_new_session or (intent == "run_app" and not utterance):
                text = GREETING_MESSAGE
                finished = False
            elif utterance:
                text, finished = await process_command_with_logging(utterance)
            else:
                text = GREETING_MESSAGE
                finished = False
            
            response_payload = create_chatapp_response(data, text, finished)
            
        else:
            # Старый формат SmartApp API (для обратной совместимости)
            session = data.get("session", {})
            req = data.get("request", {})
            version = data.get("version", "1.0")
            is_new_session = session.get("new", False)
            utterance = extract_utterance_legacy(data, req)
            
            logger.info(f"Legacy API: new_session={is_new_session}, utterance='{utterance}'")
            
            if is_new_session:
                text = GREETING_MESSAGE
                end_session = False
            elif utterance:
                text, _ = await process_command_with_logging(utterance)
                end_session = False
            else:
                text = "Не понял команду."
                end_session = False
            
            response_payload = create_legacy_response(text, session, version, end_session)

        logger.debug(f"Response: {json.dumps(response_payload, ensure_ascii=False)}")
        return JSONResponse(
            content=response_payload,
            media_type="application/json",
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
        
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/")
async def root():
    return {"status": "ok", "message": "SmartApp API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/robot/command")
async def robot_command(request: Request) -> Dict[str, Any]:
    """
    Endpoint для тестирования команд робота.
    Принимает JSON с полем 'utterance' (текст команды).
    """
    try:
        data = await request.json()
        utterance = data.get("utterance", "")
        
        if not utterance:
            raise HTTPException(status_code=400, detail="Field 'utterance' is required")
        
        result = await robot_controller.execute_command(utterance)
        
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)