"""
Имитатор робота (gRPC-клиент) для проверки работы приложения без реального робота.
Подключается к серверу приложения, получает поток сообщений: статусы, код привязки, команды.
Запуск из корня проекта: python fake_robot/main.py
"""
import argparse
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Подключаем grpc_proto из корня проекта
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import grpc
from grpc_proto import robot_pb2, robot_pb2_grpc

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("fake_robot")

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 50051
DEFAULT_ROBOT_ID = "0"
RECONNECT_DELAY = 5


def get_config():
    """Хост, порт и robot_id: argparse с fallback на переменные окружения и значения по умолчанию."""
    parser = argparse.ArgumentParser(description="Fake robot gRPC client (id=0 by default)")
    parser.add_argument("--host", default=os.environ.get("FAKE_ROBOT_HOST", DEFAULT_HOST), help="Server host")
    parser.add_argument("--port", type=int, default=int(os.environ.get("FAKE_ROBOT_PORT", str(DEFAULT_PORT))), help="Server gRPC port")
    parser.add_argument("--robot-id", dest="robot_id", default=os.environ.get("FAKE_ROBOT_ID", DEFAULT_ROBOT_ID), help="Robot ID")
    args = parser.parse_args()
    return args.host, args.port, args.robot_id


def run_stream(host: str, port: int, robot_id: str) -> None:
    """
    Один цикл: подключение к серверу, вызов StreamCommands, обработка потока до обрыва или завершения.
    """
    address = f"{host}:{port}"
    channel = grpc.insecure_channel(address)
    stub = robot_pb2_grpc.RobotCommandServiceStub(channel)

    try:
        request = robot_pb2.RobotConnectRequest(robot_id=robot_id)
        stream = stub.StreamCommands(request)

        for msg in stream:
            which = msg.WhichOneof("message")
            if which == "status":
                s = msg.status
                logger.info("[Статус] %s: %s", s.status, s.message or "")
            elif which == "binding_code":
                bc = msg.binding_code
                code = bc.code or "????"
                expires_at = bc.expires_at
                expires_str = datetime.fromtimestamp(expires_at).strftime("%H:%M:%S") if expires_at else "?"
                logger.info("")
                logger.info("  >>> КОД ПРИВЯЗКИ: %s (действует до %s) <<<  ", code, expires_str)
                logger.info("")
            elif which == "command":
                c = msg.command
                logger.info("Команда: %s (id=%s)", c.command_text or "", c.command_id or "")
            elif which == "error":
                e = msg.error
                logger.error("[Ошибка] %s: %s", e.error_code or "", e.error_message or "")
    finally:
        channel.close()


def main() -> None:
    host, port, robot_id = get_config()
    logger.info("Fake robot id=%s, подключаюсь к %s:%s", robot_id, host, port)

    while True:
        try:
            run_stream(host, port, robot_id)
        except KeyboardInterrupt:
            logger.info("Выход по Ctrl+C")
            break
        except grpc.RpcError as e:
            logger.warning("Ошибка gRPC: %s. Переподключение через %s с...", e, RECONNECT_DELAY)
        except Exception as e:
            logger.exception("Ошибка: %s. Переподключение через %s с...", e, RECONNECT_DELAY)
        else:
            logger.info("Поток завершён. Переподключение через %s с...", RECONNECT_DELAY)

        time.sleep(RECONNECT_DELAY)


if __name__ == "__main__":
    main()
