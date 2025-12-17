#!/bin/bash

# Скрипт для перезапуска всех сервисов

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔄 Перезапуск всех сервисов Robot Panda..."
echo ""

# Останавливаем все
"$SCRIPT_DIR/stop_all.sh"

echo ""
sleep 2

# Запускаем все
"$SCRIPT_DIR/start_all.sh"

