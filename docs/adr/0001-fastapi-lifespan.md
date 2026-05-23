# ADR-0001: FastAPI lifespan для запуска Telegram listener

## Контекст
Telegram client (Telethon) должен быть запущен на всё время работы приложения. Процесс listener'а живёт дольше отдельного HTTP-запроса.

## Решение
Использовать FastAPI lifespan-контекст для старта и остановки долгоживущих сервисов (Telegram listener, catch-up, alert queue).

## Последствия
- Старт и shutdown всех сервисов централизованы.
- Lifespan корректно закрывает соединения при остановке.
- Ошибка старта компонента не блокирует HTTP API.

## Отклонённые альтернативы
- `BackgroundTasks` — живут только в рамках HTTP-запроса, не подходят.
- Отдельный процесс — усложняет orchestration и health-check.