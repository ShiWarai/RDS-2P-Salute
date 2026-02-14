# Тестовая нода: имитатор робота (gRPC-клиент).
# Сборка из корня проекта: docker build -f fake_robot/Dockerfile .
FROM python:3.10-slim

WORKDIR /app

# Зависимости для gRPC и генерации proto
RUN pip install --no-cache-dir grpcio grpcio-tools protobuf

# Proto и генерация (контекст сборки — корень репозитория)
COPY grpc_proto/ ./grpc_proto/
RUN python3 -m grpc_tools.protoc -I./grpc_proto --python_out=./grpc_proto --grpc_python_out=./grpc_proto ./grpc_proto/robot.proto && \
    sed -i 's/^import robot_pb2/from . import robot_pb2/' ./grpc_proto/robot_pb2_grpc.py

# Код fake_robot
COPY fake_robot/main.py ./fake_robot/

ENV PYTHONPATH=/app
ENV FAKE_ROBOT_HOST=app
ENV FAKE_ROBOT_PORT=50051
ENV FAKE_ROBOT_ID=0

CMD ["python", "fake_robot/main.py"]
