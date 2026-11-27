# pdf service

Сервис для асинхронной генерации PDF-документов на основе данных о турах. Генерация происходит в фоне, фронтенд получает уведомление о готовности через SSE.

## Архитектура

Сервис разделен на два слоя:
1. **Web (Gateway):** FastAPI-приложение. Принимает HTTP-запросы, валидирует данные, ставит задачи в Celery и управляет SSE-соединениями.
2. **Worker (Celery):** Фоновый воркер. Рендерит HTML в PDF (WeasyPrint), сохраняет файлы в БД (PostgreSQL) и уведомляет Gateway через Redis Cache.


## Сценарий работы

1.  **Отправка заявки:** Фронт отправляет `POST /api/pdf/generate_tour` с JSON-данными тура.
2.  **Валидация:** Gateway проверяет данные (Pydantic). Если всё ок, ставит задачу в Celery и возвращает `202 Accepted` с `request_id`.
3.  **Ожидание:** Фронт открывает SSE `GET /api/pdf/events/{request_id}` и ждет.
4.  **Генерация:** Worker берет задачу, рендерит PDF, сохраняет в БД и публикует сообщение в Redis.
5.  **Уведомление:** Gateway, ищет PDF в кэше по ключу, находит и отправляет его в SSE.
6.  **Скачивание:** Фронт получает `{"status": "ready", "url": "..."}` и скачивает файл по `GET /api/pdf/download/{request_id}`.

## Эндпоинты
- `POST /api/pdf/generate_tour` - создать заявку на генерацию PDF.
- `GET /api/pdf/events/{request_id}` - SSE-поток для ожидания результата (соединение держится до 30 секунд).
- `GET /api/pdf/status_pdf/{request_id}` - получить статус отпределенной заявки.
- `GET /api/pdf/download/{request_id}` - скачать готовый PDF.
- `GET /api/pdf/history` - история генераций (только для авторизованных).

## Время жизни 
- **Redis как кэш:** Сообщение о готовности (`{"status": "ready", "url": "..."}`) сохраняется в Redis по ключу `task_updates:{request_id}` и хранится 1 час. Если фронт подключился к SSE с задержкой, он все равно прочитает статус из кэша, потому что `EventConsumer` использует поллинг.
- **Celery Result Backend (Redis db=1)**: Результат выполнения задачи (статус, id) хранится в Redis 1 час (настройка `result_expires=3600` в `celery_app.py`).
- **PostgreSQL (БД)**: Сгенерированный PDF-файл хранится в базе данных бессрочно (пока его не удалят вручную или не настроят автоочистку). Ссылка на скачивание (`/api/pdf/download/{request_id}`) будет работать всегда, пока запись есть в БД.
## Разграничение доступа

*   **Гость:** Может сгенерировать и скачать PDF. Файл сохраняется в БД, но не привязывается к пользователю (не попадает в историю).
*   **Авторизованный пользователь:** Может сгенерировать, скачать и посмотреть историю своих поездок.

Для авторизации используется заголовок `X-User-ID` (или `X-User-Claims`).

## Локальный запуск 
**Web (FastAPI)** - этот процесс принимает HTTP-запросы, валидирует данные, управляет SSE-соединениями и отдает готовые PDF. Он работает как обычный веб-сервер.

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
# В docker-compose.yml это прописано как command для сервиса web.
```

**Worker (Celery)** - этот процесс не имеет HTTP-портов. Он слушает очередь Redis (брокер), берет задачи на генерацию PDF, рендерит их через WeasyPrint и сохраняет результат в PostgreSQL.

```bash
celery -A app.broker.celery_app worker --loglevel=info
```

## Запуск через Docker Compose

```bash
# собрать образы
docker compose -f docker-compose.local.yml build

# запустить все контейнеры в фоне
docker compose -f docker-compose.local.yml up -d
```

- Поднимется PostgreSQL (база данных).
- Поднимется Redis (брокер задач).
- Запустится Web (FastAPI на порту 8000).
- Запустится Worker (Celery, который будет ждать задачи).

## Проверка работоспособности

```bash
# логи Web (FastAPI)
docker compose -f docker-compose.local.yml logs -f web

# логи Worker (Celery)
docker compose -f docker-compose.local.yml logs -f celery-worker
```