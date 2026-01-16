#!/bin/bash

# Скрипт для проверки статуса сервиса

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "📊 Статус сервиса Robot Panda:"
echo ""

# Функция для проверки статуса процесса
check_status() {
    local service_name=$1
    local port=$2
    local pid_file="$PROJECT_DIR/data/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            # Проверяем доступность порта
            if command -v netstat > /dev/null 2>&1; then
                if netstat -tuln 2>/dev/null | grep -q ":$port "; then
                    status="✅ Запущен"
                else
                    status="⚠️  Запущен, но порт недоступен"
                fi
            elif command -v ss > /dev/null 2>&1; then
                if ss -tuln 2>/dev/null | grep -q ":$port "; then
                    status="✅ Запущен"
                else
                    status="⚠️  Запущен, но порт недоступен"
                fi
            else
                status="✅ Запущен (PID: $pid)"
            fi
            echo "  $service_name: $status (PID: $pid, порт: $port)"
        else
            echo "  $service_name: ❌ Не запущен (PID файл существует, но процесс не найден)"
            rm -f "$pid_file"
        fi
    else
        echo "  $service_name: ❌ Не запущен"
    fi
}

check_status "main_app" "8000"
echo ""
echo "💡 gRPC сервер работает на порту 50051 (внутри процесса main_app)"
echo ""
