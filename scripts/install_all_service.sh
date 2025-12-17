#!/bin/bash

# Скрипт для установки systemd service для всех компонентов

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVICE_NAME="robot-panda-all.service"
SERVICE_FILE="$PROJECT_DIR/$SERVICE_NAME"

echo "📝 Установка systemd service для всех компонентов Robot Panda..."

if [ ! -f "$SERVICE_FILE" ]; then
    echo "❌ Файл сервиса не найден: $SERVICE_FILE"
    exit 1
fi

# Копируем service файл в systemd
echo "📋 Копирование service файла..."
sudo cp "$SERVICE_FILE" /etc/systemd/system/

# Перезагружаем systemd
echo "🔄 Перезагрузка systemd daemon..."
sudo systemctl daemon-reload

# Включаем автозапуск
echo "✅ Включение автозапуска..."
sudo systemctl enable "$SERVICE_NAME"

echo ""
echo "✅ Service установлен и включен для автозапуска!"
echo ""
echo "📋 Полезные команды:"
echo "  Запуск: sudo systemctl start $SERVICE_NAME"
echo "  Остановка: sudo systemctl stop $SERVICE_NAME"
echo "  Статус: sudo systemctl status $SERVICE_NAME"
echo "  Логи: sudo journalctl -u $SERVICE_NAME -f"
echo "  Перезапуск: sudo systemctl restart $SERVICE_NAME"

