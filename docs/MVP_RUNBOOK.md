# MVP Runbook — tg-market-watch

## 1. Переменные окружения

Создать `.env` в корне проекта:

```env
TG_API_ID=ваш_id
TG_API_HASH=ваш_хеш
TG_PHONE=+995593117959
TG_PASSWORD=ваш_2fa_пароль
ADMIN_API_TOKEN=dev-secret
```

> ⚠️ **TG_API_ID** и **TG_API_HASH** — с https://my.telegram.org  
> **TG_PHONE** — номер аккаунта Telegram  
> **TG_PASSWORD** — только если включена 2FA

## 2. Авторизация Telethon (первый запуск)

При первом запуске Telethon запросит код:

```bash
python3 -c "
import asyncio, os
from telethon import TelegramClient

async def auth():
    client = TelegramClient('var/telegram/session.marketwatch',
        int(os.environ['TG_API_ID']), os.environ['TG_API_HASH'])
    await client.connect()
    result = await client.send_code_request(os.environ['TG_PHONE'])
    print(f'phone_code_hash: {result.phone_code_hash}')

    code = input('Code from Telegram: ')
    try:
        await client.sign_in(phone=os.environ['TG_PHONE'], code=code,
            phone_code_hash=result.phone_code_hash)
        print('Authorized!')
    except SessionPasswordNeededError:
        await client.sign_in(password=os.environ['TG_PASSWORD'])
        print('Authorized with 2FA!')
    me = await client.get_me()
    print(f'Logged in as @{me.username}')
    await client.disconnect()

asyncio.run(auth())
"
```

**Сессионный файл:** `var/telegram/session.marketwatch.session` — **не терять**, без него заново авторизация.

## 3. Запуск приложения

```bash
# Локально
cd /opt/data/workspace/telegram-user
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

После запуска:
- FastAPI на http://localhost:8000
- Telegram-клиент авторизуется по существующей сессии
- Начинается мониторинг настроенных чатов
- Совпадения отправляются на `@getcher`

## 4. Мониторинг чатов

Настроены:

| Чат | Юзернейм |
|-----|----------|
| Барахолка Грузия | @baraholka_ge |
| Батуми Барахолка | @batumy_baraholka |

Изменить — в `config/watch.yaml`, секция `telegram.monitored_chats`.

## 5. Правила поиска

| ID | Описание | Условия |
|----|----------|---------|
| `tv_50_plus_sale` | Телевизор 50+ дюймов | Продажа + TV + диагональ >= 50 |
| `macbook_m4_pro_sale` | MacBook M4 Pro | Продажа + MacBook + M4 Pro |
| `airpods_pro_2_sale` | AirPods Pro 2 | Продажа + AirPods + Pro + 2 gen |

Правила исключают: покупку, ремонт, обзоры, аренду, аксессуары, подделки.

## 6. Проверки

```bash
# Health (публичный)
curl http://localhost:8000/health

# Status (по токену)
curl http://localhost:8000/status -H "Authorization: Bearer dev-secret"

# Ожидаемый ответ статуса:
# {"status":"ready","telegram_connected":true,"authorized":true,
#  "enabled_rules":3,"messages_processed_total":N,"matches_total":N}
```

## 7. Алерты

Совпадения отправляются в Telegram на **@getcher** в формате:
```
⚡ Совпадение: Телевизор 50+ дюймов
📄 Сообщение: Продам телевизор 55 дюймов...
🔗 https://t.me/c/xxxxx/yyy
📊 Счёт: 110 / 100
```

## 8. Структура файлов

```
telegram-user/
├── app/
│   ├── api/routes/       # FastAPI endpoints
│   ├── config/           # YAML config loader + compiler
│   ├── core/             # App state, settings, security
│   ├── engine/           # Pipeline + Rule engine + Dedup
│   ├── extraction/       # Entity extraction
│   ├── normalization/    # Text normalization pipeline
│   ├── storage/          # SQLite/SQLAlchemy storage
│   └── telegram/         # Telethon user-client
├── config/watch.yaml     # Watch rules
├── var/telegram/         # Telethon session (не коммитить!)
├── Dockerfile
├── docker-compose.yml
└── docs/
```

## 9. Важные файлы

| Файл | Назначение |
|------|-----------|
| `config/watch.yaml` | Правила мониторинга и алертов |
| `var/telegram/session.marketwatch.session` | **Сессия Telethon — не удалять** |
| `.env` | TG_API_ID, TG_API_HASH, TG_PHONE, TG_PASSWORD |
| `app/main.py` | Жизненный цикл приложения |
| `app/telegram/client.py` | Telethon-клиент |

## 10. Остановка

```bash
kill $(lsof -t -i:8000)  # или Ctrl+C
```

При рестарте сессия Telethon подхватывается автоматически — повторная авторизация не нужна.