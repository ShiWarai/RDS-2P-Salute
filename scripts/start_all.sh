#!/bin/bash

# Скрипт для запуска всех роботов и главного приложения

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

echo "🚀 Запуск всех сервисов Robot Panda..."

# Проверяем наличие виртуального окружения
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Виртуальное окружение не найдено в $VENV_DIR"
    echo "Создайте виртуальное окружение: python3 -m venv .venv"
    exit 1
fi

# Активируем виртуальное окружение
source "$VENV_DIR/bin/activate"

# Функция для запуска робота в фоне
start_robot() {
    local robot_id=$1
    local port=$2
    local pid_file="$PROJECT_DIR/data/robot_${robot_id}.pid"
    
    if [ -f "$pid_file" ]; then
        old_pid=$(cat "$pid_file")
        if ps -p "$old_pid" > /dev/null 2>&1; then
            echo "⚠️  Робот $robot_id уже запущен (PID: $old_pid)"
            return 0
        else
            rm -f "$pid_file"
        fi
    fi
    
    echo "🤖 Запуск робота $robot_id на порту $port..."
    nohup python3 -m robot_stub.main "$port" > "$PROJECT_DIR/data/robot_${robot_id}.log" 2>&1 &
    robot_pid=$!
    echo $robot_pid > "$pid_file"
    sleep 1
    if ps -p "$robot_pid" > /dev/null 2>&1; then
        echo "✅ Робот $robot_id запущен (PID: $robot_pid)"
    else
        echo "❌ Ошибка запуска робота $robot_id"
        rm -f "$pid_file"
        return 1
    fi
}

# Запускаем роботов
start_robot 1 8081
sleep 1
start_robot 2 8082
sleep 1
start_robot 3 8083
sleep 1

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
echo "✅ Все сервисы запущены!"
echo ""
echo "📊 Статус:"
echo "  Робот 1: http://localhost:8081"
echo "  Робот 2: http://localhost:8082"
echo "  Робот 3: http://localhost:8083"
echo "  Главное приложение: http://localhost:8000"
echo ""
echo "📋 Полезные команды:"
echo "  Остановка всех: ./scripts/stop_all.sh"
echo "  Статус: ./scripts/status_all.sh"
echo "  Логи робота 1: tail -f data/robot_1.log"
echo "  Логи главного: tail -f data/main_app.log"

