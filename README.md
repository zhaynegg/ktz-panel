# KTZ Digital Twin

Full-stack прототип дашборда цифрового двойника локомотива с потоковой телеметрией, индексом здоровья, replay-режимом и экспортом отчётов.

## Что умеет

- realtime-поток телеметрии по WebSocket
- индекс здоровья с top-факторами риска
- алерты и визуальная приоритизация состояния
- replay последних 5–15 минут
- светлая и тёмная тема
- экспорт `PDF` summary и `CSV`
- хранение краткосрочной истории до `72 часов`
- базовая аутентификация и Swagger/OpenAPI

## Стек

- Frontend: `Next.js 15`, `React 19`, `TypeScript`, `Recharts`
- Backend: `FastAPI`, `Pydantic`, `Uvicorn`
- Realtime: `WebSocket`
- History storage: `SQLite` for short-term telemetry history

## Структура

- [`frontend`](C:/Users/Alias/OneDrive/Documents/Playground/ktz-panel-main-merged/frontend) — интерфейс дашборда
- [`backend`](C:/Users/Alias/OneDrive/Documents/Playground/ktz-panel-main-merged/backend) — API, симулятор, health index, alerts, export
- [`scripts`](C:/Users/Alias/OneDrive/Documents/Playground/ktz-panel-main-merged/scripts) — simulator logic

Ключевые backend-модули:

- [`backend/app/services/simulator.py`](C:/Users/Alias/OneDrive/Documents/Playground/ktz-panel-main-merged/backend/app/services/simulator.py)
- [`backend/app/services/processing.py`](C:/Users/Alias/OneDrive/Documents/Playground/ktz-panel-main-merged/backend/app/services/processing.py)
- [`backend/app/services/alerts.py`](C:/Users/Alias/OneDrive/Documents/Playground/ktz-panel-main-merged/backend/app/services/alerts.py)
- [`backend/app/services/history_store.py`](C:/Users/Alias/OneDrive/Documents/Playground/ktz-panel-main-merged/backend/app/services/history_store.py)
- [`backend/app/core/history_repository.py`](C:/Users/Alias/OneDrive/Documents/Playground/ktz-panel-main-merged/backend/app/core/history_repository.py)

Ключевые frontend-модули:

- [`frontend/app/page.tsx`](C:/Users/Alias/OneDrive/Documents/Playground/ktz-panel-main-merged/frontend/app/page.tsx)
- [`frontend/components/dashboard/DashboardView.tsx`](C:/Users/Alias/OneDrive/Documents/Playground/ktz-panel-main-merged/frontend/components/dashboard/DashboardView.tsx)
- [`frontend/hooks/useReplayController.ts`](C:/Users/Alias/OneDrive/Documents/Playground/ktz-panel-main-merged/frontend/hooks/useReplayController.ts)
- [`frontend/utils/dashboard.ts`](C:/Users/Alias/OneDrive/Documents/Playground/ktz-panel-main-merged/frontend/utils/dashboard.ts)

## Быстрый запуск

### 1. Backend

```cmd
cd C:\Users\Alias\OneDrive\Documents\Playground\ktz-panel-main-merged\backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Если используется локальное виртуальное окружение:

```cmd
cd C:\Users\Alias\OneDrive\Documents\Playground\ktz-panel-main-merged\backend
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```cmd
cd C:\Users\Alias\OneDrive\Documents\Playground\ktz-panel-main-merged\frontend
npm install
npm.cmd run dev
```

### 3. Открыть приложение

- frontend: [http://localhost:3000](http://localhost:3000)
- backend docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- backend health: [http://localhost:8000/health](http://localhost:8000/health)

## Вход

По умолчанию:

- логин: `admin`
- пароль: `admin123`

Настраивается через [`backend/.env`](C:/Users/Alias/OneDrive/Documents/Playground/ktz-panel-main-merged/backend/.env).

## История и экспорт

### CSV

- последние записи: `/api/v1/telemetry/export/csv?last_n=500`
- последние 24 часа: `/api/v1/telemetry/export/csv/range?hours=24`
- последние 72 часа: `/api/v1/telemetry/export/csv/range?hours=72`

### History API

- последние кадры: `/api/v1/telemetry/history?last_n=600`
- история по времени: `/api/v1/telemetry/history/range?hours=24`
- graph по времени: `/api/v1/telemetry/graph/range?hours=24`

Persistent history хранится в:

- [`backend/data/telemetry_history.sqlite3`](C:/Users/Alias/OneDrive/Documents/Playground/ktz-panel-main-merged/backend/data/telemetry_history.sqlite3)

Retention по умолчанию: `72 часа`.

## Конфигурация

Примеры переменных окружения:

- [`backend/.env.example`](C:/Users/Alias/OneDrive/Documents/Playground/ktz-panel-main-merged/backend/.env.example)
- [`frontend/.env.example`](C:/Users/Alias/OneDrive/Documents/Playground/ktz-panel-main-merged/frontend/.env.example)

Важные настройки backend:

- `CORS_ORIGINS`
- `AUTH_USERNAME`, `AUTH_PASSWORD`
- `HEALTH_CONFIG_PATH`
- `TELEMETRY_HISTORY_DB_PATH`
- `TELEMETRY_HISTORY_RETENTION_HOURS`
- `OPENAI_API_KEY`

## Демо-сценарий

1. Запустить backend и frontend.
2. Войти в дашборд.
3. Показать live-телеметрию и индекс здоровья.
4. Инжектировать аномалию.
5. Перейти в `REPLAY` и перемотать последние 5–15 минут.
6. Скачать `PDF` summary и `CSV 24ч/72ч`.

## Что ещё можно улучшить

- нагрузочный сценарий `x10` с явной демонстрацией стабильности
- отдельная архитектурная диаграмма для презентации
- более глубокая production-проработка realtime и storage
