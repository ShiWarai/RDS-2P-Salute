#!/bin/bash
# Скрипт для запуска сервера

cd /root/RDS-2P-Salute

echo "=========================================="
echo "Запуск FastAPI сервера..."
echo "=========================================="
echo ""

# Останавливаем старый сервер (если есть)
pkill -f "uvicorn app:app" 2>/dev/null
sleep 1

# Проверяем, запущен ли ngrok
if ! pgrep ngrok > /dev/null; then
    echo "⚠ Ngrok не запущен!"
    echo ""
    echo "Сначала запустите ngrok в отдельном терминале:"
    echo "  ngrok http 8000"
    echo ""
    echo "Или если настроен именованный туннель:"
    echo "  ngrok start panda-robot"
    echo ""
    read -p "Продолжить запуск сервера? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    # Получаем URL ngrok
    NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null | python3 -c "import sys, json; data = json.load(sys.stdin); print(data['tunnels'][0]['public_url'] if data.get('tunnels') else '')" 2>/dev/null)
    
    if [ -n "$NGROK_URL" ]; then
        echo "✅ Ngrok туннель активен: $NGROK_URL"
        echo "   URL для SmartApp Studio: $NGROK_URL/salute"
        echo ""
    fi
fi

echo "Сервер будет работать в этой консоли."
echo "Для остановки нажмите Ctrl+C"
echo ""

# Активируем виртуальное окружение и запускаем сервер в foreground с автоперезагрузкой
source venv/bin/activate
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
