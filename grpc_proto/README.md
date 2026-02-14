# gRPC Server Files

Эта директория содержит файлы для gRPC сервера для коммуникации с роботами.

## Генерация Python кода из .proto

После установки зависимостей (`pip install grpcio grpcio-tools`), выполните:

```bash
python3 -m grpc_tools.protoc -I./grpc_proto --python_out=./grpc_proto --grpc_python_out=./grpc_proto ./grpc_proto/robot.proto
```

Это создаст файлы:
- `grpc_proto/robot_pb2.py` - определения сообщений
- `grpc_proto/robot_pb2_grpc.py` - определения сервисов

## Автоматическая генерация

При сборке Docker образа файлы генерируются автоматически в Dockerfile.

## Структура

- `robot.proto` - определение gRPC сервиса и сообщений
- `robot_pb2.py` - сгенерированный код (не редактировать вручную)
- `robot_pb2_grpc.py` - сгенерированный код (не редактировать вручную)
