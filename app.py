import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI()

logger = logging.getLogger(__name__)

@app.post("/salute")
async def webhook(request: Request) -> JSONResponse:
    try:
        data: Dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    logger.info(f"Received request: {data}")

    session: Dict[str, Any] = data.get("session", {})
    req: Dict[str, Any] = data.get("request", {})
    version: str = data.get("version", "1.0")

    if session.get("new", False):
        text = "Привет! Я могу реагировать на команды: лежать, вставай, равняйсь."
        end_session = False
    else:
        utterance = req.get("original_utterance", "").lower()
        if "лежать" in utterance:
            text = "Лежу!"
        elif "вставай" in utterance:
            text = "Встаю!"
        elif "равняйсь" in utterance:
            text = "Равняюсь!"
        else:
            text = "Не понял команду."
        end_session = False

    response_payload: Dict[str, Any] = {
        "session": session,
        "version": version,
        "response": {
            "text": text,
            "end_session": end_session
        }
    }

    return JSONResponse(content=response_payload)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8000)