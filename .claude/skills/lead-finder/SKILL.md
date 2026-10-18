---
name: lead-finder
description: Работа с репозиторием Lead Finder (FastAPI + React, поиск и квалификация B2B-лидов с RAG-ассистентом). Используй, когда нужно разобраться в структуре проекта, запустить сервис, внести изменения в бэкенд или интерфейс, обновить README, найти и исправить ошибку или подготовить проект к публикации на GitHub.
---

# Lead Finder: как работать с этим репозиторием

Пилот системы для отдела продаж производителя вентиляции: поиск компаний в открытых реестрах,
скоринг 0–100, отчёт и вопросы к звонку, ИИ-ассистент по базе знаний (RAG).

## Секреты — главное правило

- Ключи лежат в `.env`. **Никогда не читай `.env` целиком и не выводи значения ключей** —
  ни в ответе, ни в коде, ни в README, ни в коммите. Можно проверять только *наличие* переменной:
  `python3 -c "import re;print([l.split('=')[0] for l in open('.env') if re.match(r'^[A-Z_]+=.+',l)])"`.
- Новая настройка → добавь её в `core/config/settings.py` (с `alias`), в `.env.example` с
  заглушкой `your-api-key` и попроси пользователя вписать реальное значение в `.env` самому.
- В логах httpx на уровне INFO печатает полные URL — у 2ГИС ключ передаётся в URL. Не вставляй
  куски логов с `key=` в README, issues и ответы.

## Структура

```
main.py                    FastAPI-приложение: роутеры, CORS, init_db при старте
handlers/<area>_router.py  HTTP-слой: только валидация и вызов сервиса
services/<area>_service.py бизнес-логика: search, analytics, chat, rag
core/search/connectors/    источники: fns_egr (ФНС), dadata, dgis (2ГИС), zakupki, registry (АВОК)
core/search/scoring.py     LeadScorer: баллы и их расшифровка (веса — в settings / .env)
core/analytics/            report_builder (блоки отчёта), question_generator (вопросы к звонку)
core/rag/                  chunker → embeddings → chroma_store → retrieval; intent_classifier
core/chat/                 режимы search/help, подсказки, память сессии
core/db/models.py          SQLAlchemy-модели (SQLite: data/app.db, таблицы создаются сами)
core/config/settings.py    все настройки, читаются из .env
rag_docs/                  база знаний в Markdown (company, products, sales, segments, system)
frontend/src/lib/          api.ts (все запросы), types.ts (зеркало Pydantic-схем), format.ts
frontend/src/components/   ui.tsx (Button, Card, Badge, Input…), ScoreBadge.tsx
frontend/src/features/     search/, analytics/, chat/ — по папке на раздел
frontend/e2e/smoke.mjs     сквозной тест в Google Chrome
start.sh                   запуск всего одной командой
```

Поток запроса: `frontend/src/lib/api.ts` → прокси Vite `/api` → `handlers/` → `services/` → `core/`.

## Запуск

```bash
./start.sh                 # бэкенд :8000 + интерфейс :5173, откроет браузер
NO_BROWSER=1 ./start.sh    # то же без браузера — для фоновых проверок
```

Запускай `start.sh` в фоне (`run_in_background`) и жди готовности:
`until curl -s localhost:8000/health >/dev/null; do sleep 1; done`.
Порт занят → `lsof -i :8000` / `lsof -i :5173`, останови старый процесс.
Swagger с описанием всех эндпоинтов: http://localhost:8000/docs.

Бэкенд без `--reload`: после правок Python перезапусти `start.sh`. Vite подхватывает правки сам.

## Внесение изменений

**Бэкенд**
- Новый эндпоинт: схема в `core/<area>/schemas.py` → метод в `services/` → роут в `handlers/`.
  Роутеры не лезут во внутренние поля сервисов (`service._loader` и т.п.) — только публичные методы,
  иначе тесты с `Mock(spec=...)` падают.
- Колонки UUID в SQLite принимают только `uuid.UUID`, не строку — приводи значения с фронтенда
  (см. `_as_uuid` в `services/chat_service.py`).
- Новый источник данных: класс в `core/search/connectors/` с `async fetch(filters) -> list[RawLeadCandidate]`,
  подключить в `SearchService.__init__` и `_collect_candidates`. Ошибки источника логировать и
  возвращать `[]` — поиск не должен падать из-за одного реестра.
- Изменил веса скоринга → обнови `.env.example` и таблицу уровней в README.

**Интерфейс**
- Поменял Pydantic-схему → синхронно поправь `frontend/src/lib/types.ts`.
- Новые запросы — только через объект `api` в `lib/api.ts`, адрес сервера в код не зашивать.
- Используй компоненты из `components/ui.tsx` и цвета темы (`brand-*`, `hot/warm/cold/low` в `index.css`).
- Тексты интерфейса — на русском. Ответы ассистента рендерятся через `react-markdown`, не через
  `dangerouslySetInnerHTML` (защита от XSS).
- Пороги скоринга (80/50/30) заданы в `lib/format.ts` и совпадают с `rag_docs/system/system_search_guide.md` —
  меняй их вместе.

**База знаний**
- Правишь `rag_docs/` → переиндексируй: `curl -X POST localhost:8000/rag/ingest -H 'Content-Type: application/json' -d '{"path":"","force_rebuild":true}'`.

## Проверка ошибок

```bash
.venv/bin/pytest -q                       # бэкенд
cd frontend && npm test                   # юнит-тесты интерфейса
cd frontend && npm run build              # типы TypeScript + сборка
cd frontend && npm run test:e2e           # сквозной сценарий (нужен запущенный start.sh)
```

После каждой правки прогоняй хотя бы тесты затронутой части; перед завершением задачи — всё.
Нашёл баг → сначала тест, который его воспроизводит, потом исправление.

Известные сообщения, которые **не являются ошибками**:
- `chromadb.telemetry ... capture() takes 1 positional argument` — шум телеметрии ChromaDB.
- `2GIS API error ... incorrect key` — недействителен `DGIS_API_KEY`, поиск работает без 2ГИС.
- `Zakupki RSS fetch failed: CERTIFICATE_VERIFY_FAILED` — нет сертификата Минцифры в системе.

Если поиск вернул только компании с бейджем «Демо-данные» — реальные источники ничего не нашли;
смотри предупреждения коннекторов в выводе `start.sh`.

## Обновление README

README — витрина проекта, держи его в соответствии с кодом:
- новая функция → строка в таблице «Что умеет»;
- новый источник или сменился его статус → таблица «Источники данных»;
- новая переменная окружения → упомяни в «Запуск», если без неё не стартует;
- изменилась структура папок → блок «Структура»;
- изменился внешний вид → обнови скриншоты в `docs/images/` (start, search, analytics, assistant;
  1440×900, можно снять скриптом на основе `frontend/e2e/smoke.mjs` с `page.screenshot`).
Пиши просто: читатель — не обязательно программист.

## Подготовка к публикации

1. Запусти проверку — она ищет утёкшие ключи и прогоняет тесты и сборку:
   ```bash
   python3 .claude/skills/lead-finder/scripts/check_release.py
   ```
2. Если есть git: убедись, что `.env`, `data/`, `.venv/`, `node_modules/` не попадают в коммит
   (`git status --ignored` — они должны быть в списке игнорируемых).
3. Обнови README и скриншоты, если менялось поведение.
4. **Не делай `git commit` / `git push` без явного подтверждения пользователя** — покажи, что
   именно уйдёт в коммит, и дождись ответа.
