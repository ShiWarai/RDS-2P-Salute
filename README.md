# RDS-2P-Salute - Управление роботом-пандой через Сбер Салют

Этот проект создан для работы с [SmartApp API от Сбера](https://developers.sber.ru/docs/ru/va/api/overview).

## Описание

Python сервер на FastAPI для обработки голосовых команд робота-панды через виртуального ассистента Сбер Салют. Сервер принимает POST запросы от SmartApp API, распознает команды и логирует их. Пока физического робота нет - все команды выводятся в логи.

## Команды управления

Сервер распознает следующие голосовые команды:

- **"вставай"** (также: "встань", "поднимайся", "поднимись", "встать") → Ответ: "Панда встала"
- **"равняйсь"** (также: "равняйся", "внимание", "смирно") → Ответ: "Панда выровнялась"
- **"лежать"** (также: "ляг", "лечь", "приляг", "усни") → Ответ: "Панда уснула"

## Установка и запуск

### 1. Создание виртуального окружения (рекомендуется)

```bash
# Создание виртуального окружения
python3 -m venv venv

# Активация виртуального окружения
# На Linux/Mac:
source venv/bin/activate
# На Windows:
# venv\Scripts\activate
```

**Примечание:** Если команда `python3 -m venv` не работает, установите пакет `python3-venv`:
```bash
# На Debian/Ubuntu:
sudo apt install python3-venv

# На CentOS/RHEL:
sudo yum install python3-venv
```

Альтернативно можно использовать `virtualenv`:
```bash
pip install virtualenv
virtualenv venv
source venv/bin/activate
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Запуск

**Шаг 1: Запустите ngrok один раз (в отдельном терминале)**

```bash
./start_ngrok.sh
```

Или вручную:
```bash
ngrok http 8000
```

Скопируйте полученный HTTPS URL (например: `https://abc123.ngrok-free.app`)

**Шаг 2: Запустите сервер**

```bash
./start_all.sh
```

Скрипт проверит, что ngrok запущен, покажет URL и запустит сервер в текущей консоли с автоперезагрузкой (--reload).

**Примечание:** Сервер автоматически перезагружается при изменении файлов - не нужно вручную останавливать и запускать заново!

**Остановка:**
- Сервер: нажмите `Ctrl+C` в терминале где запущен сервер
- Ngrok: нажмите `Ctrl+C` в терминале где запущен ngrok, или `./stop_all.sh`

**Примечание:** 
- Ngrok нужно запускать один раз и оставлять работать
- URL будет постоянным пока ngrok не перезапустится
- Для постоянного домена используйте реальный домен (см. `DOMAIN_ROBOT_PANDA_SETUP.md`)

Сервер будет доступен по адресу `http://0.0.0.0:8000`

### 4. Проверка работы

Проверить, что сервер работает, можно через:

```bash
curl http://localhost:8000/
```

Или откройте в браузере: `http://localhost:8000/docs` для просмотра автоматической документации API.

## Настройка в SmartApp Studio

**Важно:** SmartApp API требует доменное имя с HTTPS, а не IP-адрес!

### Варианты решения:

#### 1. Быстрый старт (для тестирования) - Ngrok или Cloudflare Tunnel

**Ngrok:**
```bash
# Установите ngrok с https://ngrok.com
ngrok http 8000
# Используйте полученный HTTPS URL (может быть .ngrok-free.app или .ngrok-free.dev):
# https://abc123.ngrok-free.app/salute
# или
# https://bonniest-ricky-uninertly.ngrok-free.dev/salute
```

**Cloudflare Tunnel:**
```bash
# Установите cloudflared
cloudflared tunnel --url http://localhost:8000
# Используйте полученный HTTPS URL: https://random-name.trycloudflare.com/salute
```

Подробнее см. файлы `NGROK_SETUP.md` и `CLOUDFLARE_TUNNEL_SETUP.md`

#### 2. Постоянное решение - Реальный домен

**Для домена robot-panda.tech:**

1. Настройте DNS записи в панели .tech domains:
   - Тип: A
   - Имя: @
   - Значение: 147.45.132.160

2. Автоматическая настройка:
   ```bash
   sudo ./setup_domain.sh
   ```

3. Или следуйте инструкциям в `DOMAIN_ROBOT_PANDA_SETUP.md`

Подробнее см. файлы:
- `QUICK_START_DOMAIN.md` - быстрый старт
- `DOMAIN_ROBOT_PANDA_SETUP.md` - подробная инструкция

#### 3. В SmartApp Studio укажите:

```
https://your-domain.com/salute
```

**Не используйте:** `http://IP:PORT` - это не поддерживается!

## Структура проекта

- `app.py` - основной FastAPI сервер с обработкой команд
- `requirements.txt` - зависимости Python
- `.gitignore` - файлы для исключения из git
- `README.md` - документация проекта
- `venv/` - виртуальное окружение (создается при установке, не коммитится в git)

## Формат запросов и ответов

### Запрос от SmartApp API

Сервер принимает POST запросы на `/salute` в формате JSON. Структура может варьироваться, но сервер адаптивно извлекает текст команды из различных полей:
- `message.original_text`
- `message.text`
- `original_utterance`
- `request.original_utterance`
- `request.command`
- `command`
- `message` (если строка)

### Ответ сервера

Сервер возвращает ответ в формате SmartApp API:

```json
{
  "response": {
    "text": "Панда уснула",
    "end_session": false
  },
  "version": "1.0",
  "session": { ... }
}
```

## Логирование

Все команды логируются в консоль в формате:
```
[2024-01-01 12:00:00] [INFO] Получен запрос: {...}
[2024-01-01 12:00:00] [INFO] Получена команда: лежать (распознано как: lie_down)
[2024-01-01 12:00:00] [INFO] Отправлен ответ: Панда уснула
```

## API Endpoints

- `GET /` - Проверка работы сервера
- `POST /salute` - Основной endpoint для обработки команд от SmartApp API
- `GET /health` - Health check endpoint
- `GET /docs` - Автоматическая документация API (Swagger UI)

## Разработка

Проект использует:
- **FastAPI** - современный веб-фреймворк для создания API
- **Uvicorn** - ASGI сервер для запуска FastAPI приложения
- **SmartApp API** - API для интеграции с виртуальным ассистентом Сбер Салют

## Тестирование

Для тестирования можно использовать curl:

```bash
# Тест команды "лежать"
curl -X POST http://localhost:8000/salute \
  -H "Content-Type: application/json" \
  -d '{"message": {"original_text": "лежать"}, "session": {}}'

# Тест команды "вставай"
curl -X POST http://localhost:8000/salute \
  -H "Content-Type: application/json" \
  -d '{"original_utterance": "вставай", "session": {}}'
```

## Примечания

- Сервер должен быть доступен по HTTP/HTTPS из интернета для работы с SmartApp API
- Рекомендуется использовать HTTPS в продакшене (для этого потребуется SSL сертификат)
- Все команды пока только логируются, так как физического робота еще нет
- В будущем можно добавить интеграцию с реальным роботом через HTTP запросы или другие протоколы
