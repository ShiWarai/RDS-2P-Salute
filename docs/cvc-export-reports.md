# Выгрузка репортов «исправить команду» (CVC)

Инструкция для выгрузки записей обратной связи по командам из приложения RDS-2P-Salute.

## Условия доступа

- Эндпоинт доступен **только из локальной/внутренней сети** (частные диапазоны IP: 127.x, 10.x, 172.16–172.31.x, 192.168.x).
- Запросы с публичных IP возвращают `403 Forbidden`.

## Адрес и метод

| Параметр | Значение |
|----------|----------|
| Метод | `GET` |
| URL (внутри Docker) | `http://rds-2p-salute-app:8000/v1/admin/command-feedback` |
| URL (с хоста, порт 20000) | `http://localhost:20000/v1/admin/command-feedback` |

Сервис CVC и приложение должны находиться в одной Docker-сети `robot-services-network`. Тогда контейнер CVC обращается по имени хоста `rds-2p-salute-app` и порту `8000`.

## Пример запроса (curl из контейнера CVC)

```bash
curl -s http://rds-2p-salute-app:8000/v1/admin/command-feedback
```

## Пример ответа

```json
[
  {
    "user_id": "jMW6/2C6KthbH9OqSnB5...",
    "robot_id": "1",
    "user_utterance": "опусти робота",
    "classified_function": "lie_down",
    "created_at": 1770128744.1456137,
    "meta": {}
  }
]
```

| Поле | Описание |
|------|----------|
| `user_id` | Идентификатор пользователя (Salute) |
| `robot_id` | Номер робота |
| `user_utterance` | Текст, который сказал пользователь |
| `classified_function` | Функция, которую выполнила система (например `lie_down`, `dismiss`) |
| `created_at` | Unix timestamp момента записи жалобы |
| `meta` | Доп. данные (например `session_id`), может быть пустым объектом |

## Автоматизация выгрузки (CVC)

Рекомендуется периодически вызывать эндпоинт (cron, скрипт в контейнере CVC) и сохранять результат в файл или свою БД. Пример скрипта:

```bash
#!/bin/bash
# Вызов из контейнера, подключённого к robot-services-network
OUTPUT_DIR="${OUTPUT_DIR:-/app/export}"
mkdir -p "$OUTPUT_DIR"
curl -s "http://rds-2p-salute-app:8000/v1/admin/command-feedback" \
  -o "$OUTPUT_DIR/command-feedback-$(date +%Y%m%d-%H%M%S).json"
```

При доступе с публичного IP сервер вернёт `403 Forbidden`; в локальной сети ответ будет `200 OK` и JSON-массив записей.
