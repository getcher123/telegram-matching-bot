# Тестовые фикстуры для всесторонней проверки `tg-market-watch`

**Документ:** четвёртый дополнительный документ к проекту `tg-market-watch`  
**Назначение:** дать субагентам готовый набор тестовых данных, ожидаемых результатов и pytest-фикстур для самостоятельной разработки и проверки системы.  
**Связанные документы:**

- `telegram_user_market_watch_project.md` — архитектура и алгоритмические принципы.
- `telegram_user_market_watch_backlog.md` — backlog задач разработки.
- `telegram_user_market_watch_agent_orchestrator_guide.md` — протокол работы оркестратора и Codex-субагентов.

Документ можно положить в `docs/telegram_user_market_watch_test_fixtures.md`. Отдельные блоки с содержимым файлов можно вынести в `tests/fixtures/`. Все значения ниже являются тестовыми. Реальные Telegram session-файлы, номера телефонов, API hash, личные chat ID и приватные ссылки в фикстурах не используются.

---

## 1. Что именно должны покрывать эти фикстуры

Фикстуры рассчитаны на всесторонние тесты следующих подсистем:

1. Загрузка и валидация YAML-конфига.
2. Нормализация русскоязычного текста.
3. Исправление смешанной кириллицы и латиницы в известных товарных токенах.
4. Нормализация единиц измерения, валют, цен и числовых значений.
5. Словари синонимов для категорий, брендов, моделей, намерений и негативных признаков.
6. Извлечение сущностей: intent, категория, бренд, модель, поколение, чип, диагональ, цена, состояние.
7. Детерминированный rule engine.
8. Обработка нескольких совпадений в одном сообщении.
9. Scope-aware негативные признаки: аксессуар, ремонт, копия, покупка, часть комплекта.
10. Дедупликация исходных сообщений, edited-событий и fingerprint-дублей.
11. Построение ссылок на Telegram-сообщения.
12. Формирование алертов.
13. API-тесты для `/health`, `/v1/status`, `/v1/config/reload`, `/v1/rules/test`, `/v1/matches/recent`.
14. Storage-тесты: сообщения, решения, матчи, алерты, версии конфига.
15. Регрессионные кейсы на реальные паттерны объявлений.
16. Негативные кейсы, чтобы система не спамила ложными срабатываниями.

---

## 2. Алгоритмические ожидания, закреплённые фикстурами

Субагенты должны считать эти ожидания частью контракта тестов.

### 2.1. Статусы решения rule engine

| Статус | Значение |
|---|---|
| `MATCH` | Сообщение соответствует правилу и должно породить match-record. |
| `NO_MATCH` | Сообщение не соответствует правилу по обязательным признакам. |
| `REJECTED_BY_NEGATIVE` | Сообщение похоже на целевой товар, но отклонено негативным признаком: покупка, ремонт, копия, аксессуар-only, часть товара, продано. |
| `INSUFFICIENT_EVIDENCE` | Найдены отдельные признаки, но их недостаточно для уверенного детерминированного совпадения. |
| `SKIPPED_BY_SCOPE` | Сообщение из чата, который не включён в scope активного правила. |

### 2.2. Правила для MVP

| Rule ID | Условие совпадения |
|---|---|
| `tv_50_plus_sale` | Есть sale intent, категория телевизора, диагональ `>= 50.0` дюймов, нет глобальных негативных признаков. |
| `macbook_m4_pro_sale` | Есть sale intent, категория MacBook, чип `M4 Pro`, нет глобальных негативных признаков. |
| `airpods_pro_2_sale` | Есть sale intent, категория AirPods Pro, поколение `2`, нет глобальных негативных признаков. |

### 2.3. Sale intent

Sale intent считается найденным, если выполнено хотя бы одно условие:

1. В тексте есть явный глагол или фраза продажи: `продам`, `продаю`, `продается`, `отдам за`, `уступлю`, `в продаже`, `цена`.
2. Есть товарная сущность и цена с валютой или разговорной ценой: `35000 ₽`, `35 000 руб`, `35к`, `13к`, `за 1200$`.

Sale intent отменяется глобальным негативным intent, если рядом есть: `куплю`, `ищу`, `нужен`, `подскажите где купить`, `ремонт`, `чиню`, `скупка`, `аренда`, `продано`, `бронь до`, `не продаю`.

### 2.4. Диагональ телевизора

Диагональ извлекается только из размерных выражений, связанных с телевизором:

- `55"`, `55 дюймов`, `55 д`, `55 inch`, `55 inches`, `55 диагональ`.
- `127 см`, если контекст указывает на телевизор. Перевод: `inches = cm / 2.54`.
- `50+`, если рядом есть категория телевизора или слово `диагональ`.

Число без единицы измерения не считается диагональю, если оно выглядит как цена, номер модели, объём памяти или количество.

### 2.5. MacBook M4 Pro

Для `macbook_m4_pro_sale` должны быть одновременно найдены:

- категория MacBook: `macbook`, `mac book`, `макбук`, `мак бук`, `apple laptop` только если рядом есть `macbook`-подобный токен;
- чип `M4 Pro`: `m4 pro`, `м4 про`, `м4про`, `m4pro`.

`MacBook Pro M4` без слова `Pro` после `M4` не равен `M4 Pro`. `Mac mini M4 Pro` не равен MacBook.

### 2.6. AirPods Pro 2

Для `airpods_pro_2_sale` должны быть одновременно найдены:

- категория AirPods;
- линейка Pro;
- поколение 2: `2`, `2nd`, `second generation`, `2 поколение`, `gen 2`, `pro2`.

`AirPods 2` без `Pro` не подходит. `AirPods Pro` без поколения не подходит.

### 2.7. Негативные признаки

Глобальные негативные признаки отклоняют match:

- покупка или поиск: `куплю`, `ищу`, `нужен`, `нужна`, `подскажите где купить`;
- сервис: `ремонт`, `починю`, `диагностика`, `мастерская`;
- копия или подделка: `копия`, `реплика`, `аналог`, `не оригинал`, `1:1`, `люкс копия`;
- статус недоступности: `продано`, `бронь`, `резерв`;
- явное отрицание продажи: `не продаю`, `не продажа`.

Scope-aware негативные признаки отклоняют match только если сообщение продаёт аксессуар или часть вместо целевого товара:

- `чехол для AirPods Pro 2` — отклонить;
- `продам AirPods Pro 2 с чехлом` — не отклонять;
- `кронштейн для телевизора 55` — отклонить;
- `MacBook M4 Pro в комплекте чехол` — не отклонять;
- `клавиатура от MacBook M4 Pro` — отклонить.

---

## 3. Рекомендуемая структура фикстур

```text
tg-market-watch/
  docs/
    telegram_user_market_watch_test_fixtures.md
  tests/
    conftest.py
    fixtures/
      config/
        watch_config.valid.yaml
        watch_config.invalid_duplicate_rule.yaml
        watch_config.invalid_missing_alert_target.yaml
        watch_config.invalid_bad_threshold.yaml
      normalization/
        normalization_cases.yaml
        confusable_cases.yaml
      extraction/
        entity_cases.yaml
      rules/
        message_decision_cases.yaml
        multi_match_cases.yaml
        scope_negative_cases.yaml
      telegram/
        telegram_event_cases.yaml
        link_building_cases.yaml
        edit_event_cases.yaml
      alerts/
        alert_format_cases.yaml
      storage/
        db_seed_messages.yaml
        db_expected_rows.yaml
      api/
        api_request_response_cases.yaml
      dedupe/
        dedupe_event_stream.yaml
      performance/
        performance_smoke_cases.yaml
```

---

## 4. Фикстура `tests/fixtures/config/watch_config.valid.yaml`

```yaml
config_version: "2026-05-23.mvp-fixtures.1"
project: "tg-market-watch"
timezone: "Asia/Tbilisi"
language: "ru"

telegram:
  session_name: "tg_market_watch_test_session"
  api_id_env: "TG_API_ID"
  api_hash_env: "TG_API_HASH"
  phone_env: "TG_PHONE"
  listen_edited_messages: true
  catch_up_on_start: false
  max_catch_up_messages_per_chat: 200
  allowed_chats:
    - id: -1001111000001
      username: "market_msk"
      title: "Барахолка Москва"
      enabled: true
    - id: -1001111000002
      username: "spb_sell_ru"
      title: "Купи продай СПб"
      enabled: true
    - id: -1001111000003
      username: null
      title: "Закрытая барахолка электроники"
      enabled: true
    - id: -1001111000004
      username: "repair_only_ru"
      title: "Ремонт техники"
      enabled: false

alerts:
  target_user_id: 700000001
  target_username: "qa_alert_receiver"
  parse_mode: "markdown_safe"
  disable_web_page_preview: true
  throttle:
    max_alerts_per_minute: 20
    max_alerts_per_chat_per_minute: 8
  retry:
    attempts: 3
    base_delay_ms: 250
    max_delay_ms: 3000

storage:
  driver: "sqlite"
  database_url: "sqlite+aiosqlite:///./var/tg_market_watch_test.sqlite3"
  keep_raw_messages_days: 30
  keep_decisions_days: 90

normalization:
  unicode_form: "NFKC"
  lowercase: true
  replace_yo: true
  strip_zero_width: true
  collapse_spaces: true
  normalize_currency: true
  normalize_quotes: true
  normalize_dash: true
  max_message_length_chars: 12000
  token_joiners:
    - "-"
    - "_"
    - "/"
  zero_width_chars:
    - "\\u200b"
    - "\\u200c"
    - "\\u200d"
    - "\\ufeff"
  latin_to_cyrillic_confusables:
    "a": "а"
    "c": "с"
    "e": "е"
    "k": "к"
    "m": "м"
    "o": "о"
    "p": "р"
    "t": "т"
    "x": "х"
    "y": "у"
  cyrillic_to_latin_confusables:
    "а": "a"
    "с": "c"
    "е": "e"
    "к": "k"
    "м": "m"
    "о": "o"
    "р": "p"
    "т": "t"
    "х": "x"
    "у": "y"
  known_latin_tokens:
    - "airpods"
    - "air"
    - "pods"
    - "macbook"
    - "mac"
    - "book"
    - "m4"
    - "pro"
    - "oled"
    - "qled"
    - "uhd"
    - "mini-led"
    - "bravia"
    - "samsung"
    - "lg"
    - "sony"
    - "tcl"
    - "hisense"
    - "xiaomi"
    - "philips"
  typo_corrections:
    "телевизар": "телевизор"
    "теливизор": "телевизор"
    "телвизор": "телевизор"
    "макбуук": "макбук"
    "мак бук": "макбук"
    "аирподс": "airpods"
    "эйрподс": "airpods"
    "айрподс": "airpods"
    "аир подс": "airpods"
    "air pods": "airpods"
    "m4pro": "m4 pro"
    "м4про": "м4 про"
    "pro2": "pro 2"
    "про2": "про 2"

units:
  inch_aliases:
    - "дюйм"
    - "дюйма"
    - "дюймов"
    - "д"
    - "inch"
    - "inches"
    - "in"
    - "\""
  cm_aliases:
    - "см"
    - "сантиметр"
    - "сантиметра"
    - "сантиметров"
  currency_aliases:
    rub:
      - "₽"
      - "руб"
      - "р"
      - "rub"
      - "рублей"
    usd:
      - "$"
      - "usd"
      - "доллар"
      - "долларов"
    gel:
      - "gel"
      - "лари"
      - "₾"

intent_dictionary:
  sale_positive:
    - "продам"
    - "продаю"
    - "продается"
    - "продажа"
    - "в продаже"
    - "отдам за"
    - "уступлю"
    - "цена"
    - "за"
    - "торг"
    - "торг уместен"
  buy_negative:
    - "куплю"
    - "купим"
    - "ищу"
    - "нужен"
    - "нужна"
    - "нужно"
    - "подскажите где купить"
    - "кто продает"
  service_negative:
    - "ремонт"
    - "починю"
    - "чиню"
    - "диагностика"
    - "мастерская"
    - "сервис"
    - "замена"
    - "настройка"
  unavailable_negative:
    - "продано"
    - "уже продано"
    - "бронь"
    - "в резерве"
    - "резерв"
    - "не продаю"
    - "не продажа"
  exchange_terms:
    - "обмен"
    - "обменяю"
    - "поменяю"

negative_dictionary:
  accessory_terms:
    - "чехол"
    - "кейс"
    - "коробка"
    - "кабель"
    - "зарядка"
    - "блок питания"
    - "адаптер"
    - "кронштейн"
    - "пульт"
    - "клавиатура"
    - "наклейка"
    - "пленка"
    - "защитное стекло"
  part_terms:
    - "левый наушник"
    - "правый наушник"
    - "один наушник"
    - "дисплей"
    - "матрица"
    - "плата"
    - "запчасти"
    - "на запчасти"
    - "донор"
  fake_terms:
    - "копия"
    - "реплика"
    - "аналог"
    - "не оригинал"
    - "неоригинал"
    - "1:1"
    - "люкс копия"
    - "premium copy"

product_dictionary:
  tv:
    category_id: "tv"
    canonical_name: "телевизор"
    aliases:
      - "телевизор"
      - "телик"
      - "телевизер"
      - "тв"
      - "tv"
      - "smart tv"
      - "смарт тв"
      - "oled"
      - "qled"
      - "uhd tv"
      - "bravia"
    brands:
      - "samsung"
      - "lg"
      - "sony"
      - "tcl"
      - "hisense"
      - "xiaomi"
      - "philips"
      - "haier"
      - "panasonic"
  macbook:
    category_id: "macbook"
    canonical_name: "macbook"
    aliases:
      - "macbook"
      - "mac book"
      - "макбук"
      - "мак бук"
      - "мак"
    line_aliases:
      pro:
        - "pro"
        - "про"
      air:
        - "air"
        - "эйр"
    chip_aliases:
      m4_pro:
        - "m4 pro"
        - "m4pro"
        - "м4 про"
        - "м4про"
        - "m 4 pro"
        - "м 4 про"
      m4:
        - "m4"
        - "м4"
      m3_pro:
        - "m3 pro"
        - "м3 про"
  airpods:
    category_id: "airpods"
    canonical_name: "airpods"
    aliases:
      - "airpods"
      - "air pods"
      - "аирподс"
      - "эйрподс"
      - "айрподс"
      - "аир подс"
    line_aliases:
      pro:
        - "pro"
        - "про"
    generation_aliases:
      gen2:
        - "2"
        - "2nd"
        - "second generation"
        - "2 generation"
        - "2 gen"
        - "gen 2"
        - "2 поколение"
        - "второе поколение"
        - "pro 2"
        - "про 2"
      gen1:
        - "1"
        - "1st"
        - "первое поколение"

rules:
  - id: "tv_50_plus_sale"
    title: "Продажа телевизора 50+ дюймов"
    enabled: true
    scope:
      chat_ids:
        - -1001111000001
        - -1001111000002
        - -1001111000003
    require:
      intent: "sale"
      category: "tv"
      diagonal_inches:
        gte: 50.0
    reject_if:
      intents:
        - "buy"
        - "service"
        - "unavailable"
      fake: true
      accessory_only: true
      part_only: true
    alert:
      severity: "normal"
      title: "Телевизор 50+ дюймов"

  - id: "macbook_m4_pro_sale"
    title: "Продажа MacBook с M4 Pro"
    enabled: true
    scope:
      chat_ids:
        - -1001111000001
        - -1001111000002
        - -1001111000003
    require:
      intent: "sale"
      category: "macbook"
      chip: "m4_pro"
    reject_if:
      intents:
        - "buy"
        - "service"
        - "unavailable"
      fake: true
      accessory_only: true
      part_only: true
      product_families:
        - "mac_mini"
        - "ipad"
    alert:
      severity: "high"
      title: "MacBook M4 Pro"

  - id: "airpods_pro_2_sale"
    title: "Продажа AirPods Pro 2"
    enabled: true
    scope:
      chat_ids:
        - -1001111000001
        - -1001111000002
        - -1001111000003
    require:
      intent: "sale"
      category: "airpods"
      line: "pro"
      generation: "gen2"
    reject_if:
      intents:
        - "buy"
        - "service"
        - "unavailable"
      fake: true
      accessory_only: true
      part_only: true
    alert:
      severity: "normal"
      title: "AirPods Pro 2"
```

---

## 5. Невалидные YAML-конфиги

### 5.1. `tests/fixtures/config/watch_config.invalid_duplicate_rule.yaml`

```yaml
config_version: "2026-05-23.invalid.duplicate-rule"
project: "tg-market-watch"
timezone: "Asia/Tbilisi"
language: "ru"
telegram:
  session_name: "tg_market_watch_test_session"
  api_id_env: "TG_API_ID"
  api_hash_env: "TG_API_HASH"
  phone_env: "TG_PHONE"
  allowed_chats:
    - id: -1001111000001
      username: "market_msk"
      title: "Барахолка Москва"
      enabled: true
alerts:
  target_user_id: 700000001
  target_username: "qa_alert_receiver"
normalization:
  lowercase: true
rules:
  - id: "tv_50_plus_sale"
    title: "Первое правило"
    enabled: true
    require:
      intent: "sale"
      category: "tv"
  - id: "tv_50_plus_sale"
    title: "Дубликат rule id"
    enabled: true
    require:
      intent: "sale"
      category: "tv"
```

Ожидаемый результат загрузки: ошибка валидации `DUPLICATE_RULE_ID` со значением `tv_50_plus_sale`.

### 5.2. `tests/fixtures/config/watch_config.invalid_missing_alert_target.yaml`

```yaml
config_version: "2026-05-23.invalid.missing-alert-target"
project: "tg-market-watch"
timezone: "Asia/Tbilisi"
language: "ru"
telegram:
  session_name: "tg_market_watch_test_session"
  api_id_env: "TG_API_ID"
  api_hash_env: "TG_API_HASH"
  phone_env: "TG_PHONE"
  allowed_chats:
    - id: -1001111000001
      username: "market_msk"
      title: "Барахолка Москва"
      enabled: true
alerts:
  parse_mode: "markdown_safe"
normalization:
  lowercase: true
rules:
  - id: "airpods_pro_2_sale"
    title: "AirPods Pro 2"
    enabled: true
    require:
      intent: "sale"
      category: "airpods"
      line: "pro"
      generation: "gen2"
```

Ожидаемый результат загрузки: ошибка валидации `ALERT_TARGET_REQUIRED`.

### 5.3. `tests/fixtures/config/watch_config.invalid_bad_threshold.yaml`

```yaml
config_version: "2026-05-23.invalid.bad-threshold"
project: "tg-market-watch"
timezone: "Asia/Tbilisi"
language: "ru"
telegram:
  session_name: "tg_market_watch_test_session"
  api_id_env: "TG_API_ID"
  api_hash_env: "TG_API_HASH"
  phone_env: "TG_PHONE"
  allowed_chats:
    - id: -1001111000001
      username: "market_msk"
      title: "Барахолка Москва"
      enabled: true
alerts:
  target_user_id: 700000001
normalization:
  lowercase: true
rules:
  - id: "tv_bad_threshold"
    title: "Некорректный порог диагонали"
    enabled: true
    require:
      intent: "sale"
      category: "tv"
      diagonal_inches:
        gte: -50.0
```

Ожидаемый результат загрузки: ошибка валидации `INVALID_NUMERIC_THRESHOLD` для поля `rules[0].require.diagonal_inches.gte`.

---

## 6. Фикстура `tests/fixtures/normalization/normalization_cases.yaml`

```yaml
cases:
  - id: "NORM-001"
    input: "Продам Телевизор Samsung 55 ДЮЙМОВ"
    expected_text: "продам телевизор samsung 55 дюймов"
    expected_tokens: ["продам", "телевизор", "samsung", "55", "дюймов"]

  - id: "NORM-002"
    input: "Продаётся тeлeвизор LG 50\""
    expected_text: "продается телевизор lg 50 \""
    expected_tokens: ["продается", "телевизор", "lg", "50", "\""]

  - id: "NORM-003"
    input: "ПРОДАМ\u00a0ТЕЛИК\u00a0Sony\u00a0Bravia\u00a0127см"
    expected_text: "продам телик sony bravia 127 см"
    expected_tokens: ["продам", "телик", "sony", "bravia", "127", "см"]

  - id: "NORM-004"
    input: "Продам OLED—ТВ 65'', цена 90 000₽"
    expected_text: "продам oled тв 65 \" цена 90000 ₽"
    expected_tokens: ["продам", "oled", "тв", "65", "\"", "цена", "90000", "₽"]

  - id: "NORM-005"
    input: "Прoдaм MacВook M4 Рro"
    expected_text: "продам macbook m4 pro"
    expected_tokens: ["продам", "macbook", "m4", "pro"]

  - id: "NORM-006"
    input: "Продам мак бук м4про"
    expected_text: "продам макбук м4 про"
    expected_tokens: ["продам", "макбук", "м4", "про"]

  - id: "NORM-007"
    input: "Air Pods Pro2, 13к"
    expected_text: "airpods pro 2 13000"
    expected_tokens: ["airpods", "pro", "2", "13000"]

  - id: "NORM-008"
    input: "Аир подс Про 2 — оригинал"
    expected_text: "airpods про 2 оригинал"
    expected_tokens: ["airpods", "про", "2", "оригинал"]

  - id: "NORM-009"
    input: "телевизар TCL 5O дюймов"
    expected_text: "телевизор tcl 50 дюймов"
    expected_tokens: ["телевизор", "tcl", "50", "дюймов"]

  - id: "NORM-010"
    input: "Продам ТВ 50+"
    expected_text: "продам тв 50 +"
    expected_tokens: ["продам", "тв", "50", "+"]

  - id: "NORM-011"
    input: "цена 35к руб"
    expected_text: "цена 35000 руб"
    expected_tokens: ["цена", "35000", "руб"]

  - id: "NORM-012"
    input: "за 1 200$ отдам"
    expected_text: "за 1200 $ отдам"
    expected_tokens: ["за", "1200", "$", "отдам"]

  - id: "NORM-013"
    input: "Продаю AirPods\u200bPro\u200d2"
    expected_text: "продаю airpods pro 2"
    expected_tokens: ["продаю", "airpods", "pro", "2"]

  - id: "NORM-014"
    input: "MacBook_pro/M4-Pro"
    expected_text: "macbook pro m4 pro"
    expected_tokens: ["macbook", "pro", "m4", "pro"]

  - id: "NORM-015"
    input: "Продам телевизор 55д"
    expected_text: "продам телевизор 55 д"
    expected_tokens: ["продам", "телевизор", "55", "д"]

  - id: "NORM-016"
    input: "Продам телевизор 127сантиметров"
    expected_text: "продам телевизор 127 сантиметров"
    expected_tokens: ["продам", "телевизор", "127", "сантиметров"]

  - id: "NORM-017"
    input: "Продается MacBook М4 Рrо"
    expected_text: "продается macbook м4 pro"
    expected_tokens: ["продается", "macbook", "м4", "pro"]

  - id: "NORM-018"
    input: "AIRPODS PRO 2ND GENERATION"
    expected_text: "airpods pro 2nd generation"
    expected_tokens: ["airpods", "pro", "2nd", "generation"]

  - id: "NORM-019"
    input: "Прoдaм тeлик Sаmsung 55"
    expected_text: "продам телик samsung 55"
    expected_tokens: ["продам", "телик", "samsung", "55"]

  - id: "NORM-020"
    input: "Не продаю MacBook M4 Pro"
    expected_text: "не продаю macbook m4 pro"
    expected_tokens: ["не", "продаю", "macbook", "m4", "pro"]

  - id: "NORM-021"
    input: "Ремонт AirPods Pro 2"
    expected_text: "ремонт airpods pro 2"
    expected_tokens: ["ремонт", "airpods", "pro", "2"]

  - id: "NORM-022"
    input: "Чехол для AirPods Pro 2"
    expected_text: "чехол для airpods pro 2"
    expected_tokens: ["чехол", "для", "airpods", "pro", "2"]

  - id: "NORM-023"
    input: "Кронштейн для телевизора 55 дюймов"
    expected_text: "кронштейн для телевизора 55 дюймов"
    expected_tokens: ["кронштейн", "для", "телевизора", "55", "дюймов"]

  - id: "NORM-024"
    input: "Продам MacBook M4Pro"
    expected_text: "продам macbook m4 pro"
    expected_tokens: ["продам", "macbook", "m4", "pro"]

  - id: "NORM-025"
    input: "Продаю ЭйрПодс Про второе поколение"
    expected_text: "продаю airpods про второе поколение"
    expected_tokens: ["продаю", "airpods", "про", "второе", "поколение"]

  - id: "NORM-026"
    input: "Продам телевизор Xiaomi 50-inch"
    expected_text: "продам телевизор xiaomi 50 inch"
    expected_tokens: ["продам", "телевизор", "xiaomi", "50", "inch"]

  - id: "NORM-027"
    input: "Продам телевизор 49.5 дюйма"
    expected_text: "продам телевизор 49.5 дюйма"
    expected_tokens: ["продам", "телевизор", "49.5", "дюйма"]

  - id: "NORM-028"
    input: "Продам TV 50 in"
    expected_text: "продам tv 50 in"
    expected_tokens: ["продам", "tv", "50", "in"]

  - id: "NORM-029"
    input: "Продажа: MacBook\nM4 Pro\n256GB"
    expected_text: "продажа macbook m4 pro 256 gb"
    expected_tokens: ["продажа", "macbook", "m4", "pro", "256", "gb"]

  - id: "NORM-030"
    input: "AirPods Pro II"
    expected_text: "airpods pro 2"
    expected_tokens: ["airpods", "pro", "2"]
```

---

## 7. Фикстура `tests/fixtures/normalization/confusable_cases.yaml`

```yaml
cases:
  - id: "CONF-001"
    input: "MасВооk M4 Рrо"
    expected_text: "macbook m4 pro"
    expected_canonical_tokens: ["macbook", "m4", "pro"]

  - id: "CONF-002"
    input: "АirРods Рro 2"
    expected_text: "airpods pro 2"
    expected_canonical_tokens: ["airpods", "pro", "2"]

  - id: "CONF-003"
    input: "ТV Sоny Brаvia 55"
    expected_text: "tv sony bravia 55"
    expected_canonical_tokens: ["tv", "sony", "bravia", "55"]

  - id: "CONF-004"
    input: "теlevизор sаmsung 55 дюймов"
    expected_text: "телевизор samsung 55 дюймов"
    expected_canonical_tokens: ["телевизор", "samsung", "55", "дюймов"]

  - id: "CONF-005"
    input: "продам мaкбук м4 прo"
    expected_text: "продам макбук м4 про"
    expected_canonical_tokens: ["продам", "макбук", "м4", "про"]

  - id: "CONF-006"
    input: "aирпoдс прo2"
    expected_text: "airpods про 2"
    expected_canonical_tokens: ["airpods", "про", "2"]
```

---

## 8. Фикстура `tests/fixtures/extraction/entity_cases.yaml`

```yaml
cases:
  - id: "ENT-TV-001"
    text: "Продам телевизор Samsung 55 дюймов, 35000 ₽"
    expected:
      intent: "sale"
      categories: ["tv"]
      brand: "samsung"
      diagonal_inches: 55.0
      price:
        amount: 35000
        currency: "rub"
      negatives: []

  - id: "ENT-TV-002"
    text: "Телик LG 127 см, цена 30000 руб"
    expected:
      intent: "sale"
      categories: ["tv"]
      brand: "lg"
      diagonal_inches: 50.0
      price:
        amount: 30000
        currency: "rub"
      negatives: []

  - id: "ENT-TV-003"
    text: "Куплю телевизор Sony 65 дюймов"
    expected:
      intent: "buy"
      categories: ["tv"]
      brand: "sony"
      diagonal_inches: 65.0
      price: null
      negatives: ["buy"]

  - id: "ENT-TV-004"
    text: "Кронштейн для телевизора 55 дюймов, новый"
    expected:
      intent: "unknown"
      categories: ["tv"]
      diagonal_inches: 55.0
      price: null
      negatives: ["accessory_only"]

  - id: "ENT-TV-005"
    text: "Продам Samsung 55 QLED, 50000"
    expected:
      intent: "sale"
      categories: ["tv"]
      brand: "samsung"
      diagonal_inches: 55.0
      price:
        amount: 50000
        currency: "unknown"
      negatives: []

  - id: "ENT-TV-006"
    text: "Продам монитор 55 дюймов"
    expected:
      intent: "sale"
      categories: ["monitor"]
      diagonal_inches: 55.0
      price: null
      negatives: []

  - id: "ENT-MB-001"
    text: "Продам MacBook Pro 14 M4 Pro 24/512"
    expected:
      intent: "sale"
      categories: ["macbook"]
      brand: "apple"
      line: "pro"
      chip: "m4_pro"
      memory_gb: 24
      storage_gb: 512
      negatives: []

  - id: "ENT-MB-002"
    text: "Продается макбук м4про 16 дюймов"
    expected:
      intent: "sale"
      categories: ["macbook"]
      brand: "apple"
      chip: "m4_pro"
      diagonal_inches: 16.0
      negatives: []

  - id: "ENT-MB-003"
    text: "MacBook Pro M4, 16/512, 180000 руб"
    expected:
      intent: "sale"
      categories: ["macbook"]
      brand: "apple"
      line: "pro"
      chip: "m4"
      memory_gb: 16
      storage_gb: 512
      price:
        amount: 180000
        currency: "rub"
      negatives: []

  - id: "ENT-MB-004"
    text: "Продам Mac mini M4 Pro"
    expected:
      intent: "sale"
      categories: ["mac_mini"]
      brand: "apple"
      chip: "m4_pro"
      negatives: []

  - id: "ENT-MB-005"
    text: "Чехол для MacBook M4 Pro"
    expected:
      intent: "unknown"
      categories: ["macbook"]
      chip: "m4_pro"
      negatives: ["accessory_only"]

  - id: "ENT-MB-006"
    text: "Ремонт MacBook M4 Pro, диагностика"
    expected:
      intent: "service"
      categories: ["macbook"]
      chip: "m4_pro"
      negatives: ["service"]

  - id: "ENT-AP-001"
    text: "Продам AirPods Pro 2 USB-C, оригинал"
    expected:
      intent: "sale"
      categories: ["airpods"]
      line: "pro"
      generation: "gen2"
      negatives: []

  - id: "ENT-AP-002"
    text: "Аирподс Про второе поколение, 13000 руб"
    expected:
      intent: "sale"
      categories: ["airpods"]
      line: "pro"
      generation: "gen2"
      price:
        amount: 13000
        currency: "rub"
      negatives: []

  - id: "ENT-AP-003"
    text: "AirPods 2, новые"
    expected:
      intent: "unknown"
      categories: ["airpods"]
      line: null
      generation: "gen2"
      negatives: []

  - id: "ENT-AP-004"
    text: "Копия AirPods Pro 2, 1:1"
    expected:
      intent: "unknown"
      categories: ["airpods"]
      line: "pro"
      generation: "gen2"
      negatives: ["fake"]

  - id: "ENT-AP-005"
    text: "Левый наушник AirPods Pro 2"
    expected:
      intent: "unknown"
      categories: ["airpods"]
      line: "pro"
      generation: "gen2"
      negatives: ["part_only"]

  - id: "ENT-AP-006"
    text: "Чехол для AirPods Pro 2"
    expected:
      intent: "unknown"
      categories: ["airpods"]
      line: "pro"
      generation: "gen2"
      negatives: ["accessory_only"]

  - id: "ENT-CROSS-001"
    text: "Продам телевизор 55 и AirPods Pro 2"
    expected:
      intent: "sale"
      categories: ["tv", "airpods"]
      diagonal_inches: 55.0
      line: "pro"
      generation: "gen2"
      negatives: []

  - id: "ENT-CROSS-002"
    text: "Продам MacBook M4 Pro с чехлом"
    expected:
      intent: "sale"
      categories: ["macbook"]
      chip: "m4_pro"
      negatives: []

  - id: "ENT-CROSS-003"
    text: "Продам чехол и коробку от MacBook M4 Pro"
    expected:
      intent: "sale"
      categories: ["macbook"]
      chip: "m4_pro"
      negatives: ["accessory_only"]
```

---

## 9. Фикстура `tests/fixtures/rules/message_decision_cases.yaml`

Эта фикстура является главным regression pack для rule engine. Каждый кейс должен прогоняться через полный pipeline: raw text → normalization → entity extraction → rule engine → dedupe decision candidate.

```yaml
cases:
  - id: "MSG-TV-001"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 101
    date: "2026-05-23T09:00:01+04:00"
    text: "Продам телевизор Samsung 55 дюймов, 35000 ₽"
    expected:
      alert_count: 1
      decisions:
        - rule_id: "tv_50_plus_sale"
          status: "MATCH"
          canonical_product: "tv"
          minimum_evidence:
            intent: "sale"
            diagonal_inches: 55.0
            brand: "samsung"

  - id: "MSG-TV-002"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 102
    date: "2026-05-23T09:00:02+04:00"
    text: "Продаю телик LG 50 дюймов, состояние отличное"
    expected:
      alert_count: 1
      decisions:
        - rule_id: "tv_50_plus_sale"
          status: "MATCH"
          canonical_product: "tv"
          minimum_evidence:
            intent: "sale"
            diagonal_inches: 50.0
            brand: "lg"

  - id: "MSG-TV-003"
    chat_id: -1001111000002
    chat_username: "spb_sell_ru"
    message_id: 103
    date: "2026-05-23T09:00:03+04:00"
    text: "Sony Bravia 127 см, цена 42000 руб, самовывоз"
    expected:
      alert_count: 1
      decisions:
        - rule_id: "tv_50_plus_sale"
          status: "MATCH"
          canonical_product: "tv"
          minimum_evidence:
            intent: "sale"
            diagonal_inches: 50.0
            brand: "sony"

  - id: "MSG-TV-004"
    chat_id: -1001111000002
    chat_username: "spb_sell_ru"
    message_id: 104
    date: "2026-05-23T09:00:04+04:00"
    text: "Отдам за 90000 OLED ТВ 65 дюймов, LG, коробка есть"
    expected:
      alert_count: 1
      decisions:
        - rule_id: "tv_50_plus_sale"
          status: "MATCH"
          canonical_product: "tv"
          minimum_evidence:
            intent: "sale"
            diagonal_inches: 65.0
            brand: "lg"

  - id: "MSG-TV-005"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 105
    date: "2026-05-23T09:00:05+04:00"
    text: "Продам телевизор Xiaomi 49 дюймов"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "tv_50_plus_sale"
          status: "NO_MATCH"
          reject_reason: "DIAGONAL_BELOW_THRESHOLD"
          minimum_evidence:
            diagonal_inches: 49.0

  - id: "MSG-TV-006"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 106
    date: "2026-05-23T09:00:06+04:00"
    text: "Продам телевизор TCL 126 см, хороший"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "tv_50_plus_sale"
          status: "NO_MATCH"
          reject_reason: "DIAGONAL_BELOW_THRESHOLD"
          minimum_evidence:
            diagonal_inches: 49.61

  - id: "MSG-TV-007"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 107
    date: "2026-05-23T09:00:07+04:00"
    text: "Продам телевизор TCL 127 см, почти новый"
    expected:
      alert_count: 1
      decisions:
        - rule_id: "tv_50_plus_sale"
          status: "MATCH"
          minimum_evidence:
            diagonal_inches: 50.0
            brand: "tcl"

  - id: "MSG-TV-008"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 108
    date: "2026-05-23T09:00:08+04:00"
    text: "Куплю телевизор 65 дюймов Samsung"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "tv_50_plus_sale"
          status: "REJECTED_BY_NEGATIVE"
          reject_reason: "BUY_INTENT"

  - id: "MSG-TV-009"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 109
    date: "2026-05-23T09:00:09+04:00"
    text: "Ремонт телевизоров 55 дюймов, выезд мастера"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "tv_50_plus_sale"
          status: "REJECTED_BY_NEGATIVE"
          reject_reason: "SERVICE_INTENT"

  - id: "MSG-TV-010"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 110
    date: "2026-05-23T09:00:10+04:00"
    text: "Продам кронштейн для телевизора 55 дюймов"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "tv_50_plus_sale"
          status: "REJECTED_BY_NEGATIVE"
          reject_reason: "ACCESSORY_ONLY"

  - id: "MSG-TV-011"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 111
    date: "2026-05-23T09:00:11+04:00"
    text: "Samsung 50 QLED, 30000 руб, без торга"
    expected:
      alert_count: 1
      decisions:
        - rule_id: "tv_50_plus_sale"
          status: "MATCH"
          minimum_evidence:
            intent: "sale"
            diagonal_inches: 50.0
            brand: "samsung"

  - id: "MSG-TV-012"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 112
    date: "2026-05-23T09:00:12+04:00"
    text: "Продам тв 48, монитор 55, оба рабочие"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "tv_50_plus_sale"
          status: "NO_MATCH"
          reject_reason: "TV_DIAGONAL_BELOW_THRESHOLD_MONITOR_IGNORED"

  - id: "MSG-TV-013"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 113
    date: "2026-05-23T09:00:13+04:00"
    text: "Продам ТВ 50+ Samsung, есть пульт"
    expected:
      alert_count: 1
      decisions:
        - rule_id: "tv_50_plus_sale"
          status: "MATCH"
          minimum_evidence:
            diagonal_inches: 50.0
            brand: "samsung"

  - id: "MSG-TV-014"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 114
    date: "2026-05-23T09:00:14+04:00"
    text: "Телевизор 50к, срочно"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "tv_50_plus_sale"
          status: "INSUFFICIENT_EVIDENCE"
          reject_reason: "PRICE_LIKE_NUMBER_NOT_DIAGONAL"

  - id: "MSG-TV-015"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 115
    date: "2026-05-23T09:00:15+04:00"
    text: "Прoдaм тeлевизар TCL 5O дюймов"
    expected:
      alert_count: 1
      decisions:
        - rule_id: "tv_50_plus_sale"
          status: "MATCH"
          minimum_evidence:
            diagonal_inches: 50.0
            brand: "tcl"

  - id: "MSG-TV-016"
    chat_id: -1001111000004
    chat_username: "repair_only_ru"
    message_id: 116
    date: "2026-05-23T09:00:16+04:00"
    text: "Продам телевизор Samsung 65 дюймов"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "tv_50_plus_sale"
          status: "SKIPPED_BY_SCOPE"
          reject_reason: "CHAT_DISABLED_OR_NOT_IN_SCOPE"

  - id: "MSG-TV-017"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 117
    date: "2026-05-23T09:00:17+04:00"
    text: "Продано. Телевизор LG 55 дюймов больше не актуально"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "tv_50_plus_sale"
          status: "REJECTED_BY_NEGATIVE"
          reject_reason: "UNAVAILABLE"

  - id: "MSG-TV-018"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 118
    date: "2026-05-23T09:00:18+04:00"
    text: "Продам телевизор Philips диагональ 55, 27000"
    expected:
      alert_count: 1
      decisions:
        - rule_id: "tv_50_plus_sale"
          status: "MATCH"
          minimum_evidence:
            diagonal_inches: 55.0
            brand: "philips"

  - id: "MSG-TV-019"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 119
    date: "2026-05-23T09:00:19+04:00"
    text: "Продам телевизор 55 штук пультов, сам телевизор 43 дюйма"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "tv_50_plus_sale"
          status: "NO_MATCH"
          reject_reason: "COUNT_NUMBER_IGNORED_TV_DIAGONAL_BELOW_THRESHOLD"
          minimum_evidence:
            diagonal_inches: 43.0

  - id: "MSG-TV-020"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 120
    date: "2026-05-23T09:00:20+04:00"
    text: "Продам проектор 100 дюймов"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "tv_50_plus_sale"
          status: "NO_MATCH"
          reject_reason: "CATEGORY_NOT_TV"

  - id: "MSG-MB-001"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 201
    date: "2026-05-23T10:00:01+04:00"
    text: "Продам MacBook Pro 14 M4 Pro 24/512, space black"
    expected:
      alert_count: 1
      decisions:
        - rule_id: "macbook_m4_pro_sale"
          status: "MATCH"
          canonical_product: "macbook"
          minimum_evidence:
            chip: "m4_pro"
            line: "pro"

  - id: "MSG-MB-002"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 202
    date: "2026-05-23T10:00:02+04:00"
    text: "Продается макбук м4 про, 16/512"
    expected:
      alert_count: 1
      decisions:
        - rule_id: "macbook_m4_pro_sale"
          status: "MATCH"
          minimum_evidence:
            chip: "m4_pro"

  - id: "MSG-MB-003"
    chat_id: -1001111000002
    chat_username: "spb_sell_ru"
    message_id: 203
    date: "2026-05-23T10:00:03+04:00"
    text: "Mac Book Pro с М4 Про, цена 220000 руб"
    expected:
      alert_count: 1
      decisions:
        - rule_id: "macbook_m4_pro_sale"
          status: "MATCH"
          minimum_evidence:
            chip: "m4_pro"
            price_amount: 220000

  - id: "MSG-MB-004"
    chat_id: -1001111000002
    chat_username: "spb_sell_ru"
    message_id: 204
    date: "2026-05-23T10:00:04+04:00"
    text: "Продам MacBook M4Pro на гарантии"
    expected:
      alert_count: 1
      decisions:
        - rule_id: "macbook_m4_pro_sale"
          status: "MATCH"
          minimum_evidence:
            chip: "m4_pro"

  - id: "MSG-MB-005"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 205
    date: "2026-05-23T10:00:05+04:00"
    text: "Куплю MacBook M4 Pro 14"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "macbook_m4_pro_sale"
          status: "REJECTED_BY_NEGATIVE"
          reject_reason: "BUY_INTENT"

  - id: "MSG-MB-006"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 206
    date: "2026-05-23T10:00:06+04:00"
    text: "Продам MacBook Pro M4 16/512"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "macbook_m4_pro_sale"
          status: "NO_MATCH"
          reject_reason: "CHIP_M4_PRO_REQUIRED"
          minimum_evidence:
            chip: "m4"

  - id: "MSG-MB-007"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 207
    date: "2026-05-23T10:00:07+04:00"
    text: "Продам Mac mini M4 Pro"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "macbook_m4_pro_sale"
          status: "NO_MATCH"
          reject_reason: "CATEGORY_NOT_MACBOOK"

  - id: "MSG-MB-008"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 208
    date: "2026-05-23T10:00:08+04:00"
    text: "Чехол для MacBook Pro M4 Pro, кожа"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "macbook_m4_pro_sale"
          status: "REJECTED_BY_NEGATIVE"
          reject_reason: "ACCESSORY_ONLY"

  - id: "MSG-MB-009"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 209
    date: "2026-05-23T10:00:09+04:00"
    text: "Ремонт MacBook M4 Pro, замена дисплея"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "macbook_m4_pro_sale"
          status: "REJECTED_BY_NEGATIVE"
          reject_reason: "SERVICE_INTENT"

  - id: "MSG-MB-010"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 210
    date: "2026-05-23T10:00:10+04:00"
    text: "Продам MacBook Pro M3 Pro 18/512"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "macbook_m4_pro_sale"
          status: "NO_MATCH"
          reject_reason: "CHIP_M4_PRO_REQUIRED"
          minimum_evidence:
            chip: "m3_pro"

  - id: "MSG-MB-011"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 211
    date: "2026-05-23T10:00:11+04:00"
    text: "Продам MacBook Air M4"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "macbook_m4_pro_sale"
          status: "NO_MATCH"
          reject_reason: "CHIP_M4_PRO_REQUIRED"

  - id: "MSG-MB-012"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 212
    date: "2026-05-23T10:00:12+04:00"
    text: "Обменяю MacBook Pro M4 Pro на iPhone, продажи нет"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "macbook_m4_pro_sale"
          status: "REJECTED_BY_NEGATIVE"
          reject_reason: "EXCHANGE_WITHOUT_SALE"

  - id: "MSG-MB-013"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 213
    date: "2026-05-23T10:00:13+04:00"
    text: "Не продаю MacBook M4 Pro, спрашивайте только по настройке"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "macbook_m4_pro_sale"
          status: "REJECTED_BY_NEGATIVE"
          reject_reason: "NEGATED_SALE_OR_SERVICE"

  - id: "MSG-MB-014"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 214
    date: "2026-05-23T10:00:14+04:00"
    text: "Прoдaм MасВооk M4 Рrо 24GB"
    expected:
      alert_count: 1
      decisions:
        - rule_id: "macbook_m4_pro_sale"
          status: "MATCH"
          minimum_evidence:
            chip: "m4_pro"
            memory_gb: 24

  - id: "MSG-MB-015"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 215
    date: "2026-05-23T10:00:15+04:00"
    text: "Продам MacBook M4 Pro с чехлом и коробкой"
    expected:
      alert_count: 1
      decisions:
        - rule_id: "macbook_m4_pro_sale"
          status: "MATCH"
          reject_reason: null

  - id: "MSG-MB-016"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 216
    date: "2026-05-23T10:00:16+04:00"
    text: "Клавиатура от MacBook M4 Pro, новая"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "macbook_m4_pro_sale"
          status: "REJECTED_BY_NEGATIVE"
          reject_reason: "PART_OR_ACCESSORY_ONLY"

  - id: "MSG-MB-017"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 217
    date: "2026-05-23T10:00:17+04:00"
    text: "MacBook M4 Pro 14, 2500$, торг"
    expected:
      alert_count: 1
      decisions:
        - rule_id: "macbook_m4_pro_sale"
          status: "MATCH"
          minimum_evidence:
            intent: "sale"
            price_amount: 2500
            price_currency: "usd"

  - id: "MSG-MB-018"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 218
    date: "2026-05-23T10:00:18+04:00"
    text: "MacBook Pro M4 Pro уже продано"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "macbook_m4_pro_sale"
          status: "REJECTED_BY_NEGATIVE"
          reject_reason: "UNAVAILABLE"

  - id: "MSG-MB-019"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 219
    date: "2026-05-23T10:00:19+04:00"
    text: "Продам iPad Pro M4"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "macbook_m4_pro_sale"
          status: "NO_MATCH"
          reject_reason: "CATEGORY_NOT_MACBOOK"

  - id: "MSG-MB-020"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 220
    date: "2026-05-23T10:00:20+04:00"
    text: "Продам Apple laptop M4 Pro, это MacBook Pro 14"
    expected:
      alert_count: 1
      decisions:
        - rule_id: "macbook_m4_pro_sale"
          status: "MATCH"
          minimum_evidence:
            category: "macbook"
            chip: "m4_pro"

  - id: "MSG-AP-001"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 301
    date: "2026-05-23T11:00:01+04:00"
    text: "Продам AirPods Pro 2, оригинал, полный комплект"
    expected:
      alert_count: 1
      decisions:
        - rule_id: "airpods_pro_2_sale"
          status: "MATCH"
          canonical_product: "airpods"
          minimum_evidence:
            line: "pro"
            generation: "gen2"

  - id: "MSG-AP-002"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 302
    date: "2026-05-23T11:00:02+04:00"
    text: "AirPods Pro 2nd generation, 13000 руб"
    expected:
      alert_count: 1
      decisions:
        - rule_id: "airpods_pro_2_sale"
          status: "MATCH"
          minimum_evidence:
            generation: "gen2"
            price_amount: 13000

  - id: "MSG-AP-003"
    chat_id: -1001111000002
    chat_username: "spb_sell_ru"
    message_id: 303
    date: "2026-05-23T11:00:03+04:00"
    text: "Продаю Аирподс Про 2, состояние идеал"
    expected:
      alert_count: 1
      decisions:
        - rule_id: "airpods_pro_2_sale"
          status: "MATCH"
          minimum_evidence:
            line: "pro"
            generation: "gen2"

  - id: "MSG-AP-004"
    chat_id: -1001111000002
    chat_username: "spb_sell_ru"
    message_id: 304
    date: "2026-05-23T11:00:04+04:00"
    text: "Продам air pods pro2 usb-c"
    expected:
      alert_count: 1
      decisions:
        - rule_id: "airpods_pro_2_sale"
          status: "MATCH"
          minimum_evidence:
            generation: "gen2"

  - id: "MSG-AP-005"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 305
    date: "2026-05-23T11:00:05+04:00"
    text: "AirPods Pro 2, 13к, оригинал"
    expected:
      alert_count: 1
      decisions:
        - rule_id: "airpods_pro_2_sale"
          status: "MATCH"
          minimum_evidence:
            intent: "sale"
            price_amount: 13000

  - id: "MSG-AP-006"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 306
    date: "2026-05-23T11:00:06+04:00"
    text: "Продам AirPods 2, не pro"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "airpods_pro_2_sale"
          status: "NO_MATCH"
          reject_reason: "LINE_PRO_REQUIRED"

  - id: "MSG-AP-007"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 307
    date: "2026-05-23T11:00:07+04:00"
    text: "Продам AirPods Pro, MagSafe"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "airpods_pro_2_sale"
          status: "NO_MATCH"
          reject_reason: "GENERATION_2_REQUIRED"

  - id: "MSG-AP-008"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 308
    date: "2026-05-23T11:00:08+04:00"
    text: "Продам AirPods Pro 1"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "airpods_pro_2_sale"
          status: "NO_MATCH"
          reject_reason: "GENERATION_2_REQUIRED"
          minimum_evidence:
            generation: "gen1"

  - id: "MSG-AP-009"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 309
    date: "2026-05-23T11:00:09+04:00"
    text: "Чехол для AirPods Pro 2"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "airpods_pro_2_sale"
          status: "REJECTED_BY_NEGATIVE"
          reject_reason: "ACCESSORY_ONLY"

  - id: "MSG-AP-010"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 310
    date: "2026-05-23T11:00:10+04:00"
    text: "Левый наушник AirPods Pro 2, оригинал"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "airpods_pro_2_sale"
          status: "REJECTED_BY_NEGATIVE"
          reject_reason: "PART_ONLY"

  - id: "MSG-AP-011"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 311
    date: "2026-05-23T11:00:11+04:00"
    text: "Копия AirPods Pro 2, 1:1, новые"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "airpods_pro_2_sale"
          status: "REJECTED_BY_NEGATIVE"
          reject_reason: "FAKE_PRODUCT"

  - id: "MSG-AP-012"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 312
    date: "2026-05-23T11:00:12+04:00"
    text: "Куплю AirPods Pro 2"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "airpods_pro_2_sale"
          status: "REJECTED_BY_NEGATIVE"
          reject_reason: "BUY_INTENT"

  - id: "MSG-AP-013"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 313
    date: "2026-05-23T11:00:13+04:00"
    text: "Ремонт AirPods Pro 2, замена сеточки"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "airpods_pro_2_sale"
          status: "REJECTED_BY_NEGATIVE"
          reject_reason: "SERVICE_INTENT"

  - id: "MSG-AP-014"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 314
    date: "2026-05-23T11:00:14+04:00"
    text: "Кто продает AirPods Pro 2? нужен комплект"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "airpods_pro_2_sale"
          status: "REJECTED_BY_NEGATIVE"
          reject_reason: "BUY_QUESTION"

  - id: "MSG-AP-015"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 315
    date: "2026-05-23T11:00:15+04:00"
    text: "Продам AirPods Pro II, чек есть"
    expected:
      alert_count: 1
      decisions:
        - rule_id: "airpods_pro_2_sale"
          status: "MATCH"
          minimum_evidence:
            generation: "gen2"

  - id: "MSG-AP-016"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 316
    date: "2026-05-23T11:00:16+04:00"
    text: "AirPods Pro 2 продано, спасибо"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "airpods_pro_2_sale"
          status: "REJECTED_BY_NEGATIVE"
          reject_reason: "UNAVAILABLE"

  - id: "MSG-AP-017"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 317
    date: "2026-05-23T11:00:17+04:00"
    text: "Продам AirPods Pro 2 с дополнительным чехлом"
    expected:
      alert_count: 1
      decisions:
        - rule_id: "airpods_pro_2_sale"
          status: "MATCH"
          reject_reason: null

  - id: "MSG-AP-018"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 318
    date: "2026-05-23T11:00:18+04:00"
    text: "Продается кейс зарядки AirPods Pro 2"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "airpods_pro_2_sale"
          status: "REJECTED_BY_NEGATIVE"
          reject_reason: "ACCESSORY_ONLY"

  - id: "MSG-AP-019"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 319
    date: "2026-05-23T11:00:19+04:00"
    text: "Продам ЭйрПодс Про второе поколение"
    expected:
      alert_count: 1
      decisions:
        - rule_id: "airpods_pro_2_sale"
          status: "MATCH"
          minimum_evidence:
            generation: "gen2"

  - id: "MSG-AP-020"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 320
    date: "2026-05-23T11:00:20+04:00"
    text: "Продам AirPods Max"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "airpods_pro_2_sale"
          status: "NO_MATCH"
          reject_reason: "CATEGORY_OR_LINE_NOT_MATCHED"

  - id: "MSG-CROSS-001"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 401
    date: "2026-05-23T12:00:01+04:00"
    text: "Продам комплект: телевизор Samsung 55 и AirPods Pro 2"
    expected:
      alert_count: 2
      decisions:
        - rule_id: "tv_50_plus_sale"
          status: "MATCH"
          minimum_evidence:
            diagonal_inches: 55.0
        - rule_id: "airpods_pro_2_sale"
          status: "MATCH"
          minimum_evidence:
            generation: "gen2"

  - id: "MSG-CROSS-002"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 402
    date: "2026-05-23T12:00:02+04:00"
    text: "MacBook M4 Pro и телевизор LG 65, всё продаю одним лотом"
    expected:
      alert_count: 2
      decisions:
        - rule_id: "tv_50_plus_sale"
          status: "MATCH"
          minimum_evidence:
            diagonal_inches: 65.0
        - rule_id: "macbook_m4_pro_sale"
          status: "MATCH"
          minimum_evidence:
            chip: "m4_pro"

  - id: "MSG-CROSS-003"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 403
    date: "2026-05-23T12:00:03+04:00"
    text: "Продам телевизор 43, MacBook M4 Pro и копию AirPods Pro 2"
    expected:
      alert_count: 1
      decisions:
        - rule_id: "tv_50_plus_sale"
          status: "NO_MATCH"
          reject_reason: "DIAGONAL_BELOW_THRESHOLD"
        - rule_id: "macbook_m4_pro_sale"
          status: "MATCH"
        - rule_id: "airpods_pro_2_sale"
          status: "REJECTED_BY_NEGATIVE"
          reject_reason: "FAKE_PRODUCT"

  - id: "MSG-CROSS-004"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 404
    date: "2026-05-23T12:00:04+04:00"
    text: "Ищу телевизор 55 и MacBook M4 Pro, рассмотрю варианты"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "tv_50_plus_sale"
          status: "REJECTED_BY_NEGATIVE"
          reject_reason: "BUY_INTENT"
        - rule_id: "macbook_m4_pro_sale"
          status: "REJECTED_BY_NEGATIVE"
          reject_reason: "BUY_INTENT"

  - id: "MSG-CROSS-005"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 405
    date: "2026-05-23T12:00:05+04:00"
    text: "Срочно! 55 Samsung, M4 Pro, Pro 2, звоните"
    expected:
      alert_count: 0
      decisions:
        - rule_id: "tv_50_plus_sale"
          status: "INSUFFICIENT_EVIDENCE"
          reject_reason: "MISSING_CLEAR_CATEGORY_OR_INTENT"
        - rule_id: "macbook_m4_pro_sale"
          status: "INSUFFICIENT_EVIDENCE"
          reject_reason: "MISSING_MACBOOK_CATEGORY"
        - rule_id: "airpods_pro_2_sale"
          status: "INSUFFICIENT_EVIDENCE"
          reject_reason: "MISSING_AIRPODS_CATEGORY"
```

---

## 10. Фикстура `tests/fixtures/rules/scope_negative_cases.yaml`

Эти кейсы нужны, чтобы негативные слова не ломали полезные срабатывания, когда они относятся не к самому продаваемому товару.

```yaml
cases:
  - id: "SCOPE-NEG-001"
    text: "Продам AirPods Pro 2 с чехлом Spigen"
    expected:
      rule_id: "airpods_pro_2_sale"
      status: "MATCH"
      reason: "accessory_included_not_accessory_only"

  - id: "SCOPE-NEG-002"
    text: "Продам чехол Spigen для AirPods Pro 2"
    expected:
      rule_id: "airpods_pro_2_sale"
      status: "REJECTED_BY_NEGATIVE"
      reason: "accessory_only"

  - id: "SCOPE-NEG-003"
    text: "Продам MacBook M4 Pro, в комплекте чехол, зарядка, коробка"
    expected:
      rule_id: "macbook_m4_pro_sale"
      status: "MATCH"
      reason: "main_product_is_macbook"

  - id: "SCOPE-NEG-004"
    text: "Продам зарядку и коробку от MacBook M4 Pro"
    expected:
      rule_id: "macbook_m4_pro_sale"
      status: "REJECTED_BY_NEGATIVE"
      reason: "accessory_only"

  - id: "SCOPE-NEG-005"
    text: "Продам телевизор 55 с пультом и кронштейном"
    expected:
      rule_id: "tv_50_plus_sale"
      status: "MATCH"
      reason: "accessories_included_not_accessory_only"

  - id: "SCOPE-NEG-006"
    text: "Продам пульт и кронштейн для телевизора 55"
    expected:
      rule_id: "tv_50_plus_sale"
      status: "REJECTED_BY_NEGATIVE"
      reason: "accessory_only"

  - id: "SCOPE-NEG-007"
    text: "Продам AirPods Pro 2, не копия, оригинал"
    expected:
      rule_id: "airpods_pro_2_sale"
      status: "MATCH"
      reason: "negated_fake_term"

  - id: "SCOPE-NEG-008"
    text: "Продам копию AirPods Pro 2, не оригинал"
    expected:
      rule_id: "airpods_pro_2_sale"
      status: "REJECTED_BY_NEGATIVE"
      reason: "fake_product"

  - id: "SCOPE-NEG-009"
    text: "Телевизор 55 не продаю, объявление для оценки цены"
    expected:
      rule_id: "tv_50_plus_sale"
      status: "REJECTED_BY_NEGATIVE"
      reason: "negated_sale"

  - id: "SCOPE-NEG-010"
    text: "Продам телевизор 55, не ремонт, полностью рабочий"
    expected:
      rule_id: "tv_50_plus_sale"
      status: "MATCH"
      reason: "negated_service_term"
```

---

## 11. Фикстура `tests/fixtures/telegram/link_building_cases.yaml`

```yaml
cases:
  - id: "LINK-001"
    chat_id: -1001111000001
    chat_username: "market_msk"
    message_id: 101
    expected_link: "https://t.me/market_msk/101"

  - id: "LINK-002"
    chat_id: -1001111000002
    chat_username: "spb_sell_ru"
    message_id: 203
    expected_link: "https://t.me/spb_sell_ru/203"

  - id: "LINK-003"
    chat_id: -1001111000003
    chat_username: null
    message_id: 777
    expected_link: "https://t.me/c/1111000003/777"

  - id: "LINK-004"
    chat_id: -1009876543210
    chat_username: null
    message_id: 42
    expected_link: "https://t.me/c/9876543210/42"

  - id: "LINK-005"
    chat_id: -1001111000001
    chat_username: "market_msk"
    topic_id: 9001
    message_id: 9010
    expected_link: "https://t.me/market_msk/9010"
```

---

## 12. Фикстура `tests/fixtures/telegram/telegram_event_cases.yaml`

```yaml
events:
  - id: "EVT-001"
    event_type: "new_message"
    chat:
      id: -1001111000001
      username: "market_msk"
      title: "Барахолка Москва"
    sender:
      id: 600000101
      username: "seller_tv_55"
      display_name: "Иван"
      is_bot: false
    message:
      id: 101
      date: "2026-05-23T09:00:01+04:00"
      text: "Продам телевизор Samsung 55 дюймов, 35000 ₽"
      grouped_id: null
      reply_to_message_id: null
      forwarded_from: null
    expected:
      process: true
      message_key: "-1001111000001:101"
      link: "https://t.me/market_msk/101"

  - id: "EVT-002"
    event_type: "new_message"
    chat:
      id: -1001111000003
      username: null
      title: "Закрытая барахолка электроники"
    sender:
      id: 600000202
      username: null
      display_name: "Мария"
      is_bot: false
    message:
      id: 777
      date: "2026-05-23T09:05:00+04:00"
      text: "MacBook M4 Pro 14, 2500$, торг"
      grouped_id: null
      reply_to_message_id: null
      forwarded_from: null
    expected:
      process: true
      message_key: "-1001111000003:777"
      link: "https://t.me/c/1111000003/777"

  - id: "EVT-003"
    event_type: "new_message"
    chat:
      id: -1001111000004
      username: "repair_only_ru"
      title: "Ремонт техники"
    sender:
      id: 600000303
      username: "repair_master"
      display_name: "Мастер"
      is_bot: false
    message:
      id: 501
      date: "2026-05-23T09:10:00+04:00"
      text: "Продам телевизор Samsung 65 дюймов"
      grouped_id: null
      reply_to_message_id: null
      forwarded_from: null
    expected:
      process: false
      skip_reason: "chat_disabled"

  - id: "EVT-004"
    event_type: "new_message"
    chat:
      id: -1001111000001
      username: "market_msk"
      title: "Барахолка Москва"
    sender:
      id: 600000404
      username: "seller_media"
      display_name: "Олег"
      is_bot: false
    message:
      id: 502
      date: "2026-05-23T09:12:00+04:00"
      text: "Продам AirPods Pro 2, фото ниже"
      grouped_id: 880000001
      reply_to_message_id: null
      forwarded_from: null
    expected:
      process: true
      message_key: "-1001111000001:502"
      grouped_key: "-1001111000001:880000001"
      link: "https://t.me/market_msk/502"

  - id: "EVT-005"
    event_type: "new_message"
    chat:
      id: -1001111000001
      username: "market_msk"
      title: "Барахолка Москва"
    sender:
      id: 600000505
      username: "system_bot"
      display_name: "Group Helper"
      is_bot: true
    message:
      id: 503
      date: "2026-05-23T09:13:00+04:00"
      text: "Правила группы обновлены"
      grouped_id: null
      reply_to_message_id: null
      forwarded_from: null
    expected:
      process: true
      message_key: "-1001111000001:503"
      expected_matches: 0
```

---

## 13. Фикстура `tests/fixtures/telegram/edit_event_cases.yaml`

```yaml
event_streams:
  - id: "EDIT-001"
    description: "Сообщение сначала не матчится, после редактирования становится матчем"
    events:
      - event_type: "new_message"
        chat_id: -1001111000001
        chat_username: "market_msk"
        message_id: 601
        edit_date: null
        text: "Продам телевизор Samsung 49 дюймов"
      - event_type: "message_edited"
        chat_id: -1001111000001
        chat_username: "market_msk"
        message_id: 601
        edit_date: "2026-05-23T13:00:05+04:00"
        text: "Продам телевизор Samsung 55 дюймов"
    expected:
      alerts_sent: 1
      final_status_by_rule:
        tv_50_plus_sale: "MATCH"

  - id: "EDIT-002"
    description: "Сообщение уже породило алерт, затем стало продано; новый алерт не отправлять"
    events:
      - event_type: "new_message"
        chat_id: -1001111000001
        chat_username: "market_msk"
        message_id: 602
        edit_date: null
        text: "Продам AirPods Pro 2, 13000"
      - event_type: "message_edited"
        chat_id: -1001111000001
        chat_username: "market_msk"
        message_id: 602
        edit_date: "2026-05-23T13:05:05+04:00"
        text: "Продано AirPods Pro 2, спасибо"
    expected:
      alerts_sent: 1
      final_status_by_rule:
        airpods_pro_2_sale: "REJECTED_BY_NEGATIVE"
      create_update_record: true

  - id: "EDIT-003"
    description: "Матч после редактирования остаётся матчем; дубль не отправлять"
    events:
      - event_type: "new_message"
        chat_id: -1001111000001
        chat_username: "market_msk"
        message_id: 603
        edit_date: null
        text: "Продам MacBook M4 Pro, 220000"
      - event_type: "message_edited"
        chat_id: -1001111000001
        chat_username: "market_msk"
        message_id: 603
        edit_date: "2026-05-23T13:10:05+04:00"
        text: "Продам MacBook M4 Pro, 215000, торг"
    expected:
      alerts_sent: 1
      final_status_by_rule:
        macbook_m4_pro_sale: "MATCH"
      duplicate_alert_suppressed: true
```

---

## 14. Фикстура `tests/fixtures/dedupe/dedupe_event_stream.yaml`

```yaml
streams:
  - id: "DEDUP-001"
    description: "Повтор одного и того же Telegram message id"
    events:
      - chat_id: -1001111000001
        message_id: 701
        text: "Продам телевизор Samsung 55 дюймов"
        event_type: "new_message"
      - chat_id: -1001111000001
        message_id: 701
        text: "Продам телевизор Samsung 55 дюймов"
        event_type: "new_message"
    expected:
      processed_messages: 1
      alerts_sent: 1
      suppressed_duplicates: 1

  - id: "DEDUP-002"
    description: "Одинаковый текст в разных чатах не считается дублем по message key"
    events:
      - chat_id: -1001111000001
        message_id: 702
        text: "Продам AirPods Pro 2, 13000"
        event_type: "new_message"
      - chat_id: -1001111000002
        message_id: 702
        text: "Продам AirPods Pro 2, 13000"
        event_type: "new_message"
    expected:
      processed_messages: 2
      alerts_sent: 2
      suppressed_duplicates: 0

  - id: "DEDUP-003"
    description: "Fingerprint-дубль в том же чате подавляется, если включён text fingerprint window"
    dedupe_config:
      text_fingerprint_window_minutes: 30
      suppress_same_chat_same_text: true
    events:
      - chat_id: -1001111000001
        message_id: 703
        date: "2026-05-23T14:00:00+04:00"
        text: "Продам MacBook M4 Pro 24/512"
        event_type: "new_message"
      - chat_id: -1001111000001
        message_id: 704
        date: "2026-05-23T14:10:00+04:00"
        text: "Продам MacBook M4 Pro 24/512"
        event_type: "new_message"
    expected:
      processed_messages: 2
      alerts_sent: 1
      suppressed_duplicates: 1

  - id: "DEDUP-004"
    description: "Тот же текст после окна дедупликации снова алертится"
    dedupe_config:
      text_fingerprint_window_minutes: 30
      suppress_same_chat_same_text: true
    events:
      - chat_id: -1001111000001
        message_id: 705
        date: "2026-05-23T14:00:00+04:00"
        text: "Продам AirPods Pro 2, 13000"
        event_type: "new_message"
      - chat_id: -1001111000001
        message_id: 706
        date: "2026-05-23T14:45:00+04:00"
        text: "Продам AirPods Pro 2, 13000"
        event_type: "new_message"
    expected:
      processed_messages: 2
      alerts_sent: 2
      suppressed_duplicates: 0

  - id: "DEDUP-005"
    description: "Один message с двумя правилами создаёт два match-record, но один grouped alert допустим"
    alert_grouping:
      group_matches_from_same_message: true
    events:
      - chat_id: -1001111000001
        message_id: 707
        date: "2026-05-23T14:50:00+04:00"
        text: "Продам телевизор 55 и AirPods Pro 2"
        event_type: "new_message"
    expected:
      processed_messages: 1
      match_records: 2
      alert_messages_sent: 1
```

---

## 15. Фикстура `tests/fixtures/alerts/alert_format_cases.yaml`

```yaml
cases:
  - id: "ALERT-001"
    input:
      rule_id: "tv_50_plus_sale"
      rule_title: "Телевизор 50+ дюймов"
      severity: "normal"
      chat_title: "Барахолка Москва"
      chat_username: "market_msk"
      message_id: 101
      message_link: "https://t.me/market_msk/101"
      sender_display_name: "Иван"
      sender_username: "seller_tv_55"
      original_text: "Продам телевизор Samsung 55 дюймов, 35000 ₽"
      evidence:
        - label: "intent"
          value: "sale"
          fragment: "продам"
        - label: "category"
          value: "tv"
          fragment: "телевизор"
        - label: "diagonal_inches"
          value: "55.0"
          fragment: "55 дюймов"
        - label: "price"
          value: "35000 rub"
          fragment: "35000 ₽"
    expected_text: |-
      🔎 Найдено: Телевизор 50+ дюймов
      Правило: tv_50_plus_sale
      Чат: Барахолка Москва
      Автор: Иван (@seller_tv_55)
      Ссылка: https://t.me/market_msk/101

      Доказательства:
      • intent = sale: «продам»
      • category = tv: «телевизор»
      • diagonal_inches = 55.0: «55 дюймов»
      • price = 35000 rub: «35000 ₽»

      Текст:
      Продам телевизор Samsung 55 дюймов, 35000 ₽

  - id: "ALERT-002"
    input:
      rule_id: "macbook_m4_pro_sale"
      rule_title: "MacBook M4 Pro"
      severity: "high"
      chat_title: "Закрытая барахолка электроники"
      chat_username: null
      message_id: 777
      message_link: "https://t.me/c/1111000003/777"
      sender_display_name: "Мария"
      sender_username: null
      original_text: "MacBook M4 Pro 14, 2500$, торг"
      evidence:
        - label: "intent"
          value: "sale"
          fragment: "2500$"
        - label: "category"
          value: "macbook"
          fragment: "MacBook"
        - label: "chip"
          value: "m4_pro"
          fragment: "M4 Pro"
    expected_text: |-
      🔥 Найдено: MacBook M4 Pro
      Правило: macbook_m4_pro_sale
      Чат: Закрытая барахолка электроники
      Автор: Мария
      Ссылка: https://t.me/c/1111000003/777

      Доказательства:
      • intent = sale: «2500$»
      • category = macbook: «MacBook»
      • chip = m4_pro: «M4 Pro»

      Текст:
      MacBook M4 Pro 14, 2500$, торг

  - id: "ALERT-003"
    input:
      rule_id: "airpods_pro_2_sale"
      rule_title: "AirPods Pro 2"
      severity: "normal"
      chat_title: "Купи продай СПб"
      chat_username: "spb_sell_ru"
      message_id: 304
      message_link: "https://t.me/spb_sell_ru/304"
      sender_display_name: "Анна"
      sender_username: "airpods_seller"
      original_text: "Продам air pods pro2 usb-c"
      evidence:
        - label: "intent"
          value: "sale"
          fragment: "продам"
        - label: "category"
          value: "airpods"
          fragment: "air pods"
        - label: "line"
          value: "pro"
          fragment: "pro"
        - label: "generation"
          value: "gen2"
          fragment: "pro2"
    expected_text: |-
      🔎 Найдено: AirPods Pro 2
      Правило: airpods_pro_2_sale
      Чат: Купи продай СПб
      Автор: Анна (@airpods_seller)
      Ссылка: https://t.me/spb_sell_ru/304

      Доказательства:
      • intent = sale: «продам»
      • category = airpods: «air pods»
      • line = pro: «pro»
      • generation = gen2: «pro2»

      Текст:
      Продам air pods pro2 usb-c

  - id: "ALERT-004"
    input:
      grouped_matches:
        - rule_id: "tv_50_plus_sale"
          rule_title: "Телевизор 50+ дюймов"
          evidence_summary: "диагональ 55.0"
        - rule_id: "airpods_pro_2_sale"
          rule_title: "AirPods Pro 2"
          evidence_summary: "pro, gen2"
      chat_title: "Барахолка Москва"
      message_link: "https://t.me/market_msk/401"
      original_text: "Продам комплект: телевизор Samsung 55 и AirPods Pro 2"
    expected_text: |-
      🔎 Найдено несколько совпадений: 2
      Чат: Барахолка Москва
      Ссылка: https://t.me/market_msk/401

      Совпадения:
      • tv_50_plus_sale — Телевизор 50+ дюймов — диагональ 55.0
      • airpods_pro_2_sale — AirPods Pro 2 — pro, gen2

      Текст:
      Продам комплект: телевизор Samsung 55 и AirPods Pro 2
```

---

## 16. Фикстура `tests/fixtures/storage/db_seed_messages.yaml`

```yaml
messages:
  - id: 1
    message_key: "-1001111000001:101"
    chat_id: -1001111000001
    chat_username: "market_msk"
    chat_title: "Барахолка Москва"
    message_id: 101
    sender_id: 600000101
    sender_username: "seller_tv_55"
    sender_display_name: "Иван"
    date: "2026-05-23T09:00:01+04:00"
    raw_text: "Продам телевизор Samsung 55 дюймов, 35000 ₽"
    normalized_text: "продам телевизор samsung 55 дюймов 35000 ₽"
    text_fingerprint: "sha256:9ad1b7f02e0a79228b5b4b5d6d8f2f3ab2f98bd6ce627f10812a4d37ac4f1001"
    processed_at: "2026-05-23T09:00:02+04:00"

  - id: 2
    message_key: "-1001111000001:205"
    chat_id: -1001111000001
    chat_username: "market_msk"
    chat_title: "Барахолка Москва"
    message_id: 205
    sender_id: 600000205
    sender_username: "buyer_mb"
    sender_display_name: "Покупатель"
    date: "2026-05-23T10:00:05+04:00"
    raw_text: "Куплю MacBook M4 Pro 14"
    normalized_text: "куплю macbook m4 pro 14"
    text_fingerprint: "sha256:9ad1b7f02e0a79228b5b4b5d6d8f2f3ab2f98bd6ce627f10812a4d37ac4f1002"
    processed_at: "2026-05-23T10:00:06+04:00"

  - id: 3
    message_key: "-1001111000002:304"
    chat_id: -1001111000002
    chat_username: "spb_sell_ru"
    chat_title: "Купи продай СПб"
    message_id: 304
    sender_id: 600000304
    sender_username: "airpods_seller"
    sender_display_name: "Анна"
    date: "2026-05-23T11:00:04+04:00"
    raw_text: "Продам air pods pro2 usb-c"
    normalized_text: "продам airpods pro 2 usb c"
    text_fingerprint: "sha256:9ad1b7f02e0a79228b5b4b5d6d8f2f3ab2f98bd6ce627f10812a4d37ac4f1003"
    processed_at: "2026-05-23T11:00:05+04:00"
```

---

## 17. Фикстура `tests/fixtures/storage/db_expected_rows.yaml`

```yaml
match_records:
  - id: 1
    message_key: "-1001111000001:101"
    rule_id: "tv_50_plus_sale"
    status: "MATCH"
    message_link: "https://t.me/market_msk/101"
    config_version: "2026-05-23.mvp-fixtures.1"
    evidence_json:
      intent: "sale"
      category: "tv"
      brand: "samsung"
      diagonal_inches: 55.0
      price:
        amount: 35000
        currency: "rub"
    created_at: "2026-05-23T09:00:02+04:00"

  - id: 2
    message_key: "-1001111000001:205"
    rule_id: "macbook_m4_pro_sale"
    status: "REJECTED_BY_NEGATIVE"
    message_link: "https://t.me/market_msk/205"
    config_version: "2026-05-23.mvp-fixtures.1"
    evidence_json:
      intent: "buy"
      category: "macbook"
      chip: "m4_pro"
      reject_reason: "BUY_INTENT"
    created_at: "2026-05-23T10:00:06+04:00"

  - id: 3
    message_key: "-1001111000002:304"
    rule_id: "airpods_pro_2_sale"
    status: "MATCH"
    message_link: "https://t.me/spb_sell_ru/304"
    config_version: "2026-05-23.mvp-fixtures.1"
    evidence_json:
      intent: "sale"
      category: "airpods"
      line: "pro"
      generation: "gen2"
    created_at: "2026-05-23T11:00:05+04:00"

alert_records:
  - id: 1
    match_record_id: 1
    message_key: "-1001111000001:101"
    rule_id: "tv_50_plus_sale"
    target_user_id: 700000001
    status: "SENT"
    telegram_alert_message_id: 900001
    sent_at: "2026-05-23T09:00:03+04:00"

  - id: 2
    match_record_id: 3
    message_key: "-1001111000002:304"
    rule_id: "airpods_pro_2_sale"
    target_user_id: 700000001
    status: "SENT"
    telegram_alert_message_id: 900002
    sent_at: "2026-05-23T11:00:06+04:00"

config_versions:
  - id: 1
    version: "2026-05-23.mvp-fixtures.1"
    sha256: "sha256:e5f802b2c2512e92f7632eddddf7f3d23aa9401f6e8bdeabf9a1c4ec6f5f0001"
    loaded_at: "2026-05-23T08:55:00+04:00"
    active: true
```

---

## 18. Фикстура `tests/fixtures/api/api_request_response_cases.yaml`

```yaml
cases:
  - id: "API-HEALTH-001"
    method: "GET"
    path: "/health"
    request_json: null
    expected_status: 200
    expected_json:
      status: "ok"
      service: "tg-market-watch"
      telegram_client: "connected"
      config_loaded: true
      storage: "ok"

  - id: "API-STATUS-001"
    method: "GET"
    path: "/v1/status"
    request_json: null
    expected_status: 200
    expected_json_subset:
      active_config_version: "2026-05-23.mvp-fixtures.1"
      enabled_rules: 3
      enabled_chats: 3
      alert_target_user_id: 700000001

  - id: "API-RULES-TEST-001"
    method: "POST"
    path: "/v1/rules/test"
    request_json:
      chat_id: -1001111000001
      chat_username: "market_msk"
      text: "Продам телевизор Samsung 55 дюймов, 35000 ₽"
    expected_status: 200
    expected_json_subset:
      normalized_text: "продам телевизор samsung 55 дюймов 35000 ₽"
      matches:
        - rule_id: "tv_50_plus_sale"
          status: "MATCH"
          alert_would_be_sent: true
      non_matches:
        - rule_id: "macbook_m4_pro_sale"
          status: "NO_MATCH"
        - rule_id: "airpods_pro_2_sale"
          status: "NO_MATCH"

  - id: "API-RULES-TEST-002"
    method: "POST"
    path: "/v1/rules/test"
    request_json:
      chat_id: -1001111000001
      chat_username: "market_msk"
      text: "Куплю AirPods Pro 2"
    expected_status: 200
    expected_json_subset:
      matches: []
      non_matches:
        - rule_id: "airpods_pro_2_sale"
          status: "REJECTED_BY_NEGATIVE"
          reject_reason: "BUY_INTENT"

  - id: "API-RELOAD-001"
    method: "POST"
    path: "/v1/config/reload"
    request_json:
      config_path: "tests/fixtures/config/watch_config.valid.yaml"
    expected_status: 200
    expected_json_subset:
      status: "reloaded"
      config_version: "2026-05-23.mvp-fixtures.1"
      rules_loaded: 3
      chats_loaded: 4
      chats_enabled: 3

  - id: "API-RELOAD-002"
    method: "POST"
    path: "/v1/config/reload"
    request_json:
      config_path: "tests/fixtures/config/watch_config.invalid_duplicate_rule.yaml"
    expected_status: 422
    expected_json_subset:
      status: "validation_error"
      error_code: "DUPLICATE_RULE_ID"
      value: "tv_50_plus_sale"

  - id: "API-MATCHES-RECENT-001"
    method: "GET"
    path: "/v1/matches/recent?limit=2"
    request_json: null
    expected_status: 200
    expected_json_subset:
      items:
        - message_key: "-1001111000002:304"
          rule_id: "airpods_pro_2_sale"
          status: "MATCH"
        - message_key: "-1001111000001:101"
          rule_id: "tv_50_plus_sale"
          status: "MATCH"
      limit: 2
```

---

## 19. Фикстура `tests/fixtures/performance/performance_smoke_cases.yaml`

Эти кейсы не должны заменять нагрузочное тестирование, но помогают поймать очевидные деградации. В каждом сообщении должен выполняться полный pipeline без внешней сети и без обращения к Telegram.

```yaml
settings:
  max_total_runtime_ms_for_100_messages: 1000
  max_single_message_runtime_ms: 50
  run_count: 100

message_pool:
  - "Продам телевизор Samsung 55 дюймов, 35000 ₽"
  - "Продам телевизор LG 65 OLED, 90000"
  - "Куплю телевизор 75 дюймов"
  - "Ремонт телевизоров Sony Bravia"
  - "Кронштейн для телевизора 55 дюймов"
  - "MacBook M4 Pro 14, 2500$, торг"
  - "Продам MacBook Pro M3 Pro"
  - "Куплю MacBook M4 Pro"
  - "Чехол для MacBook M4 Pro"
  - "Продам MacBook M4 Pro с чехлом"
  - "Продам AirPods Pro 2, оригинал"
  - "AirPods Pro 2nd generation, 13000 руб"
  - "Копия AirPods Pro 2, 1:1"
  - "Кейс зарядки AirPods Pro 2"
  - "Продам AirPods Max"
  - "Продам комплект: телевизор 55 и AirPods Pro 2"
  - "Ищу телевизор 55 и MacBook M4 Pro"
  - "Продано MacBook M4 Pro"
  - "Sony Bravia 127 см, цена 42000 руб"
  - "Прoдaм MасВооk M4 Рrо 24GB"

expected_summary:
  total_messages: 100
  minimum_matches: 25
  maximum_matches: 45
  must_not_raise: true
  external_network_calls_allowed: false
```

---

## 20. Готовый `tests/conftest.py` для загрузки фикстур

Этот файл можно использовать как базу для pytest. Он не импортирует модули приложения и поэтому безопасен для bootstrap-этапа. Субагенты могут добавлять поверх него fixture-функции для конкретных сервисов приложения.

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml


TESTS_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = TESTS_DIR / "fixtures"


def load_yaml_fixture(relative_path: str) -> dict[str, Any]:
    path = FIXTURES_DIR / relative_path
    if not path.exists():
        raise FileNotFoundError(f"Fixture file does not exist: {path}")
    with path.open("r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file)
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise TypeError(f"Fixture must contain a YAML mapping at top level: {path}")
    return loaded


def load_json_fixture(relative_path: str) -> dict[str, Any]:
    path = FIXTURES_DIR / relative_path
    if not path.exists():
        raise FileNotFoundError(f"Fixture file does not exist: {path}")
    with path.open("r", encoding="utf-8") as file:
        loaded = json.load(file)
    if not isinstance(loaded, dict):
        raise TypeError(f"Fixture must contain a JSON object at top level: {path}")
    return loaded


@pytest.fixture(scope="session")
def fixture_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def valid_watch_config() -> dict[str, Any]:
    return load_yaml_fixture("config/watch_config.valid.yaml")


@pytest.fixture(scope="session")
def invalid_duplicate_rule_config() -> dict[str, Any]:
    return load_yaml_fixture("config/watch_config.invalid_duplicate_rule.yaml")


@pytest.fixture(scope="session")
def invalid_missing_alert_target_config() -> dict[str, Any]:
    return load_yaml_fixture("config/watch_config.invalid_missing_alert_target.yaml")


@pytest.fixture(scope="session")
def invalid_bad_threshold_config() -> dict[str, Any]:
    return load_yaml_fixture("config/watch_config.invalid_bad_threshold.yaml")


@pytest.fixture(scope="session")
def normalization_cases() -> list[dict[str, Any]]:
    return load_yaml_fixture("normalization/normalization_cases.yaml")["cases"]


@pytest.fixture(scope="session")
def confusable_cases() -> list[dict[str, Any]]:
    return load_yaml_fixture("normalization/confusable_cases.yaml")["cases"]


@pytest.fixture(scope="session")
def entity_cases() -> list[dict[str, Any]]:
    return load_yaml_fixture("extraction/entity_cases.yaml")["cases"]


@pytest.fixture(scope="session")
def message_decision_cases() -> list[dict[str, Any]]:
    return load_yaml_fixture("rules/message_decision_cases.yaml")["cases"]


@pytest.fixture(scope="session")
def scope_negative_cases() -> list[dict[str, Any]]:
    return load_yaml_fixture("rules/scope_negative_cases.yaml")["cases"]


@pytest.fixture(scope="session")
def telegram_event_cases() -> list[dict[str, Any]]:
    return load_yaml_fixture("telegram/telegram_event_cases.yaml")["events"]


@pytest.fixture(scope="session")
def link_building_cases() -> list[dict[str, Any]]:
    return load_yaml_fixture("telegram/link_building_cases.yaml")["cases"]


@pytest.fixture(scope="session")
def edit_event_streams() -> list[dict[str, Any]]:
    return load_yaml_fixture("telegram/edit_event_cases.yaml")["event_streams"]


@pytest.fixture(scope="session")
def dedupe_streams() -> list[dict[str, Any]]:
    return load_yaml_fixture("dedupe/dedupe_event_stream.yaml")["streams"]


@pytest.fixture(scope="session")
def alert_format_cases() -> list[dict[str, Any]]:
    return load_yaml_fixture("alerts/alert_format_cases.yaml")["cases"]


@pytest.fixture(scope="session")
def api_request_response_cases() -> list[dict[str, Any]]:
    return load_yaml_fixture("api/api_request_response_cases.yaml")["cases"]


@pytest.fixture(scope="session")
def db_seed_messages() -> list[dict[str, Any]]:
    return load_yaml_fixture("storage/db_seed_messages.yaml")["messages"]


@pytest.fixture(scope="session")
def db_expected_rows() -> dict[str, Any]:
    return load_yaml_fixture("storage/db_expected_rows.yaml")


@pytest.fixture(scope="session")
def performance_smoke_cases() -> dict[str, Any]:
    return load_yaml_fixture("performance/performance_smoke_cases.yaml")
```

---

## 21. Примеры pytest-тестов, которые агенты должны реализовать

Код ниже задаёт контракт. Имена импортов приложения фиксируют ожидаемую модульную структуру, но субагент может изменить только путь импорта, если в проекте уже принят другой путь. Логика проверок должна сохраниться.

### 21.1. `tests/test_normalization_contract.py`

```python
from __future__ import annotations

from typing import Any

import pytest

from app.normalization.normalizer import Normalizer
from app.config.loader import ConfigLoader


@pytest.fixture(scope="session")
def normalizer(valid_watch_config: dict[str, Any]) -> Normalizer:
    config = ConfigLoader.from_mapping(valid_watch_config)
    return Normalizer(config.normalization, config.product_dictionary, config.units)


@pytest.mark.parametrize("case", argvalues=[], ids=[])
def test_normalization_case_template(case: dict[str, Any]) -> None:
    assert case


def test_all_normalization_cases(normalizer: Normalizer, normalization_cases: list[dict[str, Any]]) -> None:
    for case in normalization_cases:
        result = normalizer.normalize(case["input"])
        assert result.text == case["expected_text"], case["id"]
        assert result.tokens == case["expected_tokens"], case["id"]


def test_all_confusable_cases(normalizer: Normalizer, confusable_cases: list[dict[str, Any]]) -> None:
    for case in confusable_cases:
        result = normalizer.normalize(case["input"])
        assert result.text == case["expected_text"], case["id"]
        assert result.canonical_tokens == case["expected_canonical_tokens"], case["id"]
```

### 21.2. `tests/test_rule_engine_contract.py`

```python
from __future__ import annotations

from typing import Any

import pytest

from app.config.loader import ConfigLoader
from app.pipeline.message_pipeline import MessagePipeline
from app.telegram.models import RawMessage


@pytest.fixture(scope="session")
def pipeline(valid_watch_config: dict[str, Any]) -> MessagePipeline:
    config = ConfigLoader.from_mapping(valid_watch_config)
    return MessagePipeline(config=config)


def _make_raw_message(case: dict[str, Any]) -> RawMessage:
    return RawMessage(
        chat_id=case["chat_id"],
        chat_username=case.get("chat_username"),
        chat_title=case.get("chat_title") or "Тестовый чат",
        message_id=case["message_id"],
        date=case["date"],
        sender_id=case.get("sender_id") or 600000000,
        sender_username=case.get("sender_username"),
        sender_display_name=case.get("sender_display_name") or "Тестовый автор",
        text=case["text"],
    )


def test_message_decision_cases(pipeline: MessagePipeline, message_decision_cases: list[dict[str, Any]]) -> None:
    for case in message_decision_cases:
        raw_message = _make_raw_message(case)
        result = pipeline.process(raw_message)
        expected = case["expected"]

        assert result.alert_count == expected["alert_count"], case["id"]

        decisions_by_rule = {decision.rule_id: decision for decision in result.decisions}
        for expected_decision in expected["decisions"]:
            rule_id = expected_decision["rule_id"]
            assert rule_id in decisions_by_rule, case["id"]
            actual = decisions_by_rule[rule_id]
            assert actual.status == expected_decision["status"], case["id"]
            if "reject_reason" in expected_decision:
                assert actual.reject_reason == expected_decision["reject_reason"], case["id"]

            for key, value in expected_decision.get("minimum_evidence", {}).items():
                assert actual.evidence.get(key) == value, f"{case['id']} evidence.{key}"
```

### 21.3. `tests/test_alert_format_contract.py`

```python
from __future__ import annotations

from typing import Any

from app.alerts.formatter import AlertFormatter


def test_alert_format_cases(alert_format_cases: list[dict[str, Any]]) -> None:
    formatter = AlertFormatter()
    for case in alert_format_cases:
        actual = formatter.format_from_mapping(case["input"])
        assert actual == case["expected_text"], case["id"]
```

### 21.4. `tests/test_link_builder_contract.py`

```python
from __future__ import annotations

from app.telegram.links import build_message_link


def test_link_building_cases(link_building_cases: list[dict[str, object]]) -> None:
    for case in link_building_cases:
        actual = build_message_link(
            chat_id=int(case["chat_id"]),
            chat_username=case.get("chat_username"),
            message_id=int(case["message_id"]),
            topic_id=case.get("topic_id"),
        )
        assert actual == case["expected_link"], case["id"]
```

### 21.5. `tests/test_dedupe_contract.py`

```python
from __future__ import annotations

from typing import Any

from app.dedupe.service import DedupeService
from app.pipeline.message_pipeline import MessagePipeline
from app.config.loader import ConfigLoader


def test_dedupe_streams(valid_watch_config: dict[str, Any], dedupe_streams: list[dict[str, Any]]) -> None:
    config = ConfigLoader.from_mapping(valid_watch_config)

    for stream in dedupe_streams:
        dedupe = DedupeService()
        pipeline = MessagePipeline(config=config, dedupe_service=dedupe)
        counters = {
            "processed_messages": 0,
            "alerts_sent": 0,
            "suppressed_duplicates": 0,
            "match_records": 0,
            "alert_messages_sent": 0,
        }

        for event in stream["events"]:
            result = pipeline.process_event_mapping(event)
            counters["processed_messages"] += int(result.processed)
            counters["alerts_sent"] += result.alert_count
            counters["suppressed_duplicates"] += int(result.duplicate_suppressed)
            counters["match_records"] += len(result.match_records)
            counters["alert_messages_sent"] += result.alert_message_count

        for key, value in stream["expected"].items():
            assert counters[key] == value, f"{stream['id']} {key}"
```

---

## 22. Матрица приёмки тестовых фикстур

| Подсистема | Минимум для приёмки | Эти фикстуры |
|---|---:|---:|
| Config validation | 1 valid + 3 invalid | 1 valid + 3 invalid |
| Normalization | 20 кейсов | 30 кейсов |
| Confusables | 5 кейсов | 6 кейсов |
| Entity extraction | 15 кейсов | 21 кейс |
| Rule engine | 50 кейсов | 65 кейсов |
| Scope-aware negative | 8 кейсов | 10 кейсов |
| Telegram link building | 4 кейса | 5 кейсов |
| Edited messages | 3 сценария | 3 сценария |
| Dedupe | 4 сценария | 5 сценариев |
| Alert formatting | 3 кейса | 4 кейса |
| Storage seed/expected | 2 match rows | 3 match rows + 2 alert rows |
| API contract | 5 кейсов | 7 кейсов |
| Performance smoke | 1 набор | 1 набор из 20 сообщений × 100 прогонов |

---

## 23. Как оркестратору выдавать задачи субагентам по этому документу

### 23.1. Задача для QA-субагента: разложить фикстуры по файлам

**Цель:** создать структуру `tests/fixtures/` и перенести все YAML/Python блоки из этого документа в реальные файлы.

**Критерии приёмки:**

- Все пути из раздела 3 существуют.
- `python -m pytest --collect-only` не падает из-за отсутствующих fixture-файлов.
- Все YAML-файлы успешно читаются через `yaml.safe_load`.
- В фикстурах нет реальных секретов, session-файлов, номеров телефонов и приватных пользовательских данных.

### 23.2. Задача для Normalization-субагента

**Цель:** реализовать `Normalizer`, который проходит `normalization_cases.yaml` и `confusable_cases.yaml`.

**Критерии приёмки:**

- Все `NORM-*` кейсы проходят.
- Все `CONF-*` кейсы проходят.
- Нормализатор детерминирован: повторный вызов на том же input возвращает тот же объект или тот же JSON.
- Нормализатор не делает внешних сетевых вызовов.

### 23.3. Задача для Extraction-субагента

**Цель:** реализовать извлечение сущностей по `entity_cases.yaml`.

**Критерии приёмки:**

- Все `ENT-*` кейсы проходят.
- Цена `13к` превращается в `13000`.
- `127 см` превращается в `50.0` дюймов.
- `126 см` в rule engine не проходит порог 50 дюймов.
- `MacBook Pro M4` не превращается в `M4 Pro`.

### 23.4. Задача для Rule Engine-субагента

**Цель:** реализовать детерминированный rule engine по `message_decision_cases.yaml` и `scope_negative_cases.yaml`.

**Критерии приёмки:**

- Все `MSG-*` кейсы проходят.
- Все `SCOPE-NEG-*` кейсы проходят.
- В одном сообщении может быть несколько `MATCH`.
- Негативные признаки имеют правильный scope.
- В решении есть объяснимые evidence-поля.

### 23.5. Задача для Telegram-субагента

**Цель:** реализовать модели событий и link builder по `telegram_event_cases.yaml` и `link_building_cases.yaml`.

**Критерии приёмки:**

- Все ссылки строятся точно как в `LINK-*`.
- Disabled chat не обрабатывается.
- Закрытый чат без username получает ссылку через `/c/` и числовой id без префикса `-100`.
- `grouped_id` сохраняется в metadata.

### 23.6. Задача для Alert-субагента

**Цель:** реализовать форматирование алертов по `alert_format_cases.yaml`.

**Критерии приёмки:**

- Форматированные строки совпадают посимвольно.
- Username автора скрывается, если `sender_username = null`.
- Для severity `high` используется заголовок с `🔥`, для `normal` — `🔎`.
- Grouped alert корректно объединяет несколько совпадений одного сообщения.

### 23.7. Задача для Storage-субагента

**Цель:** реализовать сохранение сообщений, решений, match-records, alert-records и config versions.

**Критерии приёмки:**

- Seed из `db_seed_messages.yaml` загружается в тестовую БД.
- После обработки ожидаемых сообщений БД содержит строки из `db_expected_rows.yaml`.
- Повторная обработка того же `message_key` не создаёт duplicate alert.
- `config_version` сохраняется в каждом `match_record`.

### 23.8. Задача для API-субагента

**Цель:** реализовать API-контракты по `api_request_response_cases.yaml`.

**Критерии приёмки:**

- Все `API-*` кейсы проходят через FastAPI TestClient или async HTTP client.
- `/v1/rules/test` не отправляет реальные Telegram-алерты.
- `/v1/config/reload` атомарно применяет только валидный конфиг.
- Ошибки валидации возвращают стабильные `error_code`.

---

## 24. Правила расширения фикстур

1. Новый баг сначала добавляется как failing fixture, затем исправляется код.
2. Каждый новый товарный rule должен иметь минимум:
   - 5 positive cases;
   - 5 negative cases;
   - 2 scope-aware negative cases;
   - 1 multi-match case;
   - 1 alert formatting case.
3. Нельзя удалять старые regression-кейсы без отдельного решения оркестратора.
4. Если меняется ожидаемый результат, в описании PR или agent result должен быть указан reason: `algorithm_changed`, `fixture_was_wrong`, `scope_changed`, `config_changed`.
5. Все фикстуры должны оставаться полностью локальными и не требовать Telegram, сети, секретов или внешних API.

---

## 25. Минимальный smoke-набор для MVP-gate

До принятия MVP должны проходить эти группы тестов:

```text
tests/test_config_contract.py
tests/test_normalization_contract.py
tests/test_entity_extraction_contract.py
tests/test_rule_engine_contract.py
tests/test_scope_negative_contract.py
tests/test_link_builder_contract.py
tests/test_alert_format_contract.py
tests/test_dedupe_contract.py
tests/test_api_contract.py
tests/test_storage_contract.py
```

MVP нельзя считать принятым, если есть хотя бы один ложноположительный алерт по кейсам:

```text
MSG-TV-008
MSG-TV-009
MSG-TV-010
MSG-TV-014
MSG-TV-017
MSG-MB-005
MSG-MB-006
MSG-MB-007
MSG-MB-008
MSG-MB-009
MSG-MB-012
MSG-MB-013
MSG-AP-006
MSG-AP-007
MSG-AP-009
MSG-AP-010
MSG-AP-011
MSG-AP-012
MSG-AP-013
MSG-AP-014
SCOPE-NEG-002
SCOPE-NEG-004
SCOPE-NEG-006
SCOPE-NEG-008
SCOPE-NEG-009
```

MVP нельзя считать принятым, если есть хотя бы один ложноотрицательный результат по кейсам:

```text
MSG-TV-001
MSG-TV-002
MSG-TV-003
MSG-TV-004
MSG-TV-007
MSG-TV-011
MSG-TV-013
MSG-TV-015
MSG-TV-018
MSG-MB-001
MSG-MB-002
MSG-MB-003
MSG-MB-004
MSG-MB-014
MSG-MB-015
MSG-MB-017
MSG-MB-020
MSG-AP-001
MSG-AP-002
MSG-AP-003
MSG-AP-004
MSG-AP-005
MSG-AP-015
MSG-AP-017
MSG-AP-019
MSG-CROSS-001
MSG-CROSS-002
SCOPE-NEG-001
SCOPE-NEG-003
SCOPE-NEG-005
SCOPE-NEG-007
SCOPE-NEG-010
```
