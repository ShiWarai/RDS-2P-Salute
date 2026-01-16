#!/bin/bash

# Скрипт для запуска главного приложения

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

echo "🚀 Запуск сервиса Robot Panda..."

# Проверяем наличие виртуального окружения
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Виртуальное окружение не найдено в $VENV_DIR"
    echo "Создайте виртуальное окружение: python3 -m venv .venv"
    exit 1
fi

# Активируем виртуальное окружение
source "$VENV_DIR/bin/activate"

# Запускаем главное приложение
MAIN_PID_FILE="$PROJECT_DIR/data/main_app.pid"

if [ -f "$MAIN_PID_FILE" ]; then
    old_pid=$(cat "$MAIN_PID_FILE")
    if ps -p "$old_pid" > /dev/null 2>&1; then
        echo "⚠️  Главное приложение уже запущено (PID: $old_pid)"
    else
        rm -f "$MAIN_PID_FILE"
    fi
fi

if [ ! -f "$MAIN_PID_FILE" ] || ! ps -p "$(cat "$MAIN_PID_FILE")" > /dev/null 2>&1; then
    echo "🌐 Запуск главного приложения на порту 8000..."
    echo "📡 gRPC сервер будет доступен на порту 50051..."
    nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$PROJECT_DIR/data/main_app.log" 2>&1 &
    main_pid=$!
    echo $main_pid > "$MAIN_PID_FILE"
    sleep 1
    if ps -p "$main_pid" > /dev/null 2>&1; then
        echo "✅ Главное приложение запущено (PID: $main_pid)"
    else
        echo "❌ Ошибка запуска главного приложения"
        rm -f "$MAIN_PID_FILE"
        exit 1
    fi
fi

echo ""
echo "✅ Сервис запущен!"
echo ""
echo "📊 Статус:"
echo "  Главное приложение: http://localhost:8000"
echo "  gRPC сервер: localhost:50051"
echo ""
echo "📋 Полезные команды:"
echo "  Остановка: ./scripts/stop_all.sh"
echo "  Статус: ./scripts/status_all.sh"
echo "  Логи главного: tail -f data/main_app.log"
echo ""
echo "💡 Примечание: Роботы теперь подключаются через gRPC на порту 50051"
