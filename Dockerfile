FROM python:3.10-slim

WORKDIR /app

# Установка системных зависимостей (curl для healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копирование файла зависимостей
COPY requirements.txt .

# Установка Python зависимостей (включая grpcio-tools для генерации proto)
RUN pip install --no-cache-dir -r requirements.txt && \
    pip list | grep grpc || echo "Warning: grpc packages not found"

# Копирование proto файлов и генерация Python кода
COPY grpc_proto/ ./grpc_proto/
RUN python3 -m grpc_tools.protoc -I./grpc_proto --python_out=./grpc_proto --grpc_python_out=./grpc_proto ./grpc_proto/robot.proto && \
    ls -la ./grpc_proto/ && \
    test -f ./grpc_proto/robot_pb2.py && test -f ./grpc_proto/robot_pb2_grpc.py && \
    sed -i 's/^import robot_pb2/from . import robot_pb2/' ./grpc_proto/robot_pb2_grpc.py || \
    (echo "ERROR: proto files not generated!" && exit 1)

# Копирование кода приложения
COPY app/ ./app/

# Создание директории для логов
RUN mkdir -p /app/logs

# Expose порты приложения
EXPOSE 8000
EXPOSE 50051

# Команда запуска
CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
