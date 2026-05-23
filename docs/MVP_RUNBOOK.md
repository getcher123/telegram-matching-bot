# MVP Runbook — tg-market-watch

## Запуск

```bash
# Локально (без Docker)
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Создать .env из .env.example и заполнить
cp .env.example .env

# Запустить
uvicorn app.main:app --reload --port 8000

# Или через Docker
docker compose up -d --build
```

## Health Check

```bash
curl http://localhost:8000/health
# → {"status": "ok", "app": "tg-market-watch", "version": "0.1.0"}
```

## Status

```bash
curl http://localhost:8000/status -H "Authorization: Bearer ${API_KEY}"
# → {"app": "running", "config": {...}, "telegram": {...}, ...}
```

## Auth (Telegram user-client)

```bash
# Start auth flow (send code to Telegram)
curl -X POST http://localhost:8000/auth/start \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"phone": "+79123456789"}'
# → {"status": "awaiting_code", "hint": "***"}

# Confirm code
curl -X POST http://localhost:8000/auth/code \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"code": "12345"}'
# → {"status": "authorized"}
```

## Конфигурация

Редактировать `config/watch.yaml`, затем:

```bash
curl -X POST http://localhost:8000/config/reload -H "Authorization: Bearer ${API_KEY}"
```

## Мониторинг

- `/health` — публичный, проверка живости
- `/status` — по API-ключу, детальное состояние компонентов
- Логи: `./var/log/app.log`
- БД: `./var/data/marketwatch.db`

## Структура

```
telegram-user/
├── app/
│   ├── api/routes/     # FastAPI endpoints
│   ├── config/         # YAML config loader + compiler
│   ├── core/           # App state, settings, security
│   ├── engine/         # Pipeline + Rule engine + Dedup
│   ├── extraction/     # Entity extraction
│   ├── normalization/  # Text normalization pipeline
│   ├── storage/        # SQLite/SQLAlchemy storage
│   └── telegram/       # Telethon user-client
├── config/watch.yaml   # Default watch rules
├── Dockerfile
├── docker-compose.yml
└── docs/               # Architecture + Backlog + Orchestrator guide
```

## Правила по умолчанию

| ID | Описание | Требования |
|----|----------|------------|
| `tv_50_plus` | Телевизоры 50+ дюймов | TV intent, dict:tv, diagonal>=50 |
| `macbook_m4_pro` | MacBook M4 Pro | MacBook intent, dict:macbook, storage>=512 |
| `airpods_pro_2` | AirPods Pro 2 | AirPods intent, dict:airpods |