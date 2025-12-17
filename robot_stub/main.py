"""
Скрипт-заглушка робота для тестирования системы привязки
Имитирует API робота: генерация кодов верификации и обработка команд
"""
import logging
import random
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any
import uvicorn

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

app = FastAPI()

# Хранилище активных кодов (в реальности это должно быть в БД или кэше)
_active_codes: Dict[str, Dict[str, Any]] = {}


@app.post("/bind/request")
async def bind_request(request: Request) -> JSONResponse:
    """
    Запрос на генерацию кода верификации для привязки робота
    
    Body:
        {
            "user_id": "user123",
            "robot_id": "1"
        }
    
    Response:
        {
            "code": "1234",
            "expires_at": 1702834567
        }
    """
    try:
        data: Dict[str, Any] = await request.json()
        user_id = data.get("user_id")
        robot_id = data.get("robot_id")
        
        if not user_id or not robot_id:
            raise HTTPException(status_code=400, detail="Fields 'user_id' and 'robot_id' are required")
        
        # Генерируем 4-значный код
        code = f"{random.randint(1000, 9999)}"
        
        # Время истечения (5 минут)
        expires_at = time.time() + 300
        
        # Сохраняем код (в реальности это должно быть в БД)
        _active_codes[f"{user_id}_{robot_id}"] = {
            "code": code,
            "expires_at": expires_at,
            "user_id": user_id,
            "robot_id": robot_id
        }
        
        # Логируем код (это ключевой момент - код должен быть виден в логах)
        logger.info(f"[BIND CODE] User {user_id} binding to robot {robot_id}. Code: {code}")
        logger.info(f"[BIND CODE] Code expires at: {time.ctime(expires_at)}")
        
        return JSONResponse(
            content={
                "code": code,
                "expires_at": expires_at
            },
            media_type="application/json"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bind_request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/motors/command")
async def motors_command(request: Request) -> JSONResponse:
    """
    Обработка команд управления моторами робота
    
    Body:
        {
            "action": "lie_down",
            "motors": {
                "head": {"angle": 0, "speed": 50},
                "body": {"angle": -90, "speed": 50},
                "legs": {"angle": 0, "speed": 50}
            },
            "duration": 2000
        }
    
    Response:
        {
            "success": true
        }
    """
    try:
        data: Dict[str, Any] = await request.json()
        action = data.get("action")
        motors = data.get("motors", {})
        duration = data.get("duration", 0)
        
        # Логируем команду
        logger.info(f"[COMMAND] Received action: {action}")
        logger.info(f"[COMMAND] Motors: {motors}")
        logger.info(f"[COMMAND] Duration: {duration}ms")
        
        # В реальности здесь была бы отправка команды на физические моторы
        # Для заглушки просто возвращаем успех
        
        return JSONResponse(
            content={"success": True},
            media_type="application/json"
        )
        
    except Exception as e:
        logger.error(f"Error in motors_command: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "robot_stub"}


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    # Запуск на разных портах для разных роботов
    # В реальности каждый робот будет иметь свой IP/порт
    import sys
    
    port = 8081
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            logger.warning(f"Invalid port {sys.argv[1]}, using default 8081")
    
    logger.info(f"Starting robot stub on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)

