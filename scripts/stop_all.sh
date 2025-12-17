#!/bin/bash

# Скрипт для остановки всех роботов и главного приложения

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🛑 Остановка всех сервисов Robot Panda..."

# Функция для остановки процесса по PID файлу
stop_service() {
    local service_name=$1
    local pid_file="$PROJECT_DIR/data/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "⏹️  Остановка $service_name (PID: $pid)..."
            kill "$pid" 2>/dev/null || true
            sleep 1
            # Если процесс еще работает, принудительно завершаем
            if ps -p "$pid" > /dev/null 2>&1; then
                kill -9 "$pid" 2>/dev/null || true
            fi
            rm -f "$pid_file"
            echo "✅ $service_name остановлен"
        else
            echo "⚠️  $service_name не запущен (PID файл существует, но процесс не найден)"
            rm -f "$pid_file"
        fi
    else
        echo "⚠️  $service_name не запущен (PID файл не найден)"
    fi
}

# Останавливаем роботов
stop_service "robot_1"
stop_service "robot_2"
stop_service "robot_3"

# Останавливаем главное приложение
stop_service "main_app"

echo ""
echo "✅ Все сервисы остановлены!"

