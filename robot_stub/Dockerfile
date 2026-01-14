FROM python:3.10-slim

WORKDIR /app

# Установка системных зависимостей (curl для healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Установка только необходимых зависимостей для заглушки
RUN pip install --no-cache-dir fastapi uvicorn

# Копирование модуля robot_stub
COPY robot_stub/ ./robot_stub/

# Переменная окружения для ID робота (по умолчанию 1)
ENV ROBOT_ID=1
ENV PYTHONPATH=/app

# Expose порт (будет вычисляться динамически: 8080 + ROBOT_ID)
EXPOSE 8081

# Entrypoint скрипт для вычисления порта и запуска
ENTRYPOINT ["sh", "-c", "PORT=$((8080 + ${ROBOT_ID})) && python -m robot_stub.main $PORT"]
