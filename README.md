# tg-market-watch

FastAPI-приложение для мониторинга Telegram-групп через user-аккаунт.  
Автоматически отслеживает объявления по детерминированным YAML-правилам и отправляет уведомления.

## Архитектура

```
FastAPI App (lifespan)
  ├── ConfigService        — YAML config, atomic reload, versioning
  ├── TelegramClientService — MTProto user-client (Telethon)
  ├── Normalizer           — Unicode cleanup, confusables, layout, tokenizer
  ├── EntityExtractor      — Intent, category, model, numeric extraction
  ├── RuleEngine           — Deterministic matching, negative logic, evidence
  ├── Storage              — SQLite/PostgreSQL repositories
  ├── AlertDispatcher      — Telegram alert formatting and delivery
  └── ProcessingPipeline   — Orchestrates all stages
```

## Стартовые правила

| Правило | Описание |
|---------|----------|
| `tv_50_plus_sale` | Телевизор с диагональю 50+ дюймов |
| `macbook_m4_pro_sale` | MacBook с чипом M4 Pro |
| `airpods_pro_2_sale` | AirPods Pro 2 |

## Локальный запуск

```bash
# 1. Установка
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 2. Настройка
cp .env.example .env
# Заполните TG_API_ID, TG_API_HASH, TG_PHONE, ADMIN_API_TOKEN

# 3. Запуск
uvicorn app.main:app --reload
```

## API Endpoints

| Method | Path | Описание |
|--------|------|----------|
| GET | `/health` | Проверка здоровья |
| GET | `/status` | Состояние компонентов |
| POST | `/auth/send-code` | Отправка кода Telegram |
| POST | `/auth/confirm-code` | Подтверждение кода |
| POST | `/config/reload` | Перезагрузка YAML |
| POST | `/rules/test` | Тестирование правил |
| GET | `/matches` | История совпадений |

Подробнее — в `docs/telegram_user_market_watch_project.md`.