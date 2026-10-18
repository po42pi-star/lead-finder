---
doc_id: sales_analytics_schema_v1
category: sales
audience: [manager, rop, analyst]
tags: [аналитика, логирование, схема данных, квалификация, метрики, SPIN, MEDDIC, BANT, Sandler, Challenger, SNAP, AIDA, воронка, конверсия]
last_updated: 2026-05-25
version: 1.0
related_docs: [sales_questions_bank.md, sales_objections.md, sales_closing.md, segment_installers.md, segment_designers.md, segment_contractors.md, segment_industrial.md, system_analytics_guide.md]
---

# Схема аналитики продаж: структура данных для логирования и анализа

## 📋 Назначение документа
Этот документ определяет структуру данных для фиксации взаимодействий с потенциальными клиентами в процессе поиска, квалификации и закрытия сделок. Схема позволяет:
- Сохранять контекст диалога для будущей аналитики (пост-MVP)
- Оценивать эффективность вопросов, отработки возражений и скриптов закрытия
- Строить воронку квалификации по методологиям (SPIN, MEDDIC, BANT)
- Выявлять паттерны успешных и провальных диалогов

> **Важно для MVP:** Даже если аналитика звонков не реализована, сохранение структурированных данных на этом этапе создаст базу для обучения и оптимизации в будущем.

---

## 🗃️ Сущности и поля для логирования

### 1. Сущность: `lead` (Лид / Компания)
Базовая информация о потенциальном клиенте.

| Поле | Тип | Описание | Методология | Пример |
|------|-----|----------|-------------|--------|
| `lead_id` | string | Уникальный идентификатор лида | — | `lead_7f3a9b2c` |
| `company_name` | string | Название компании | — | `ООО "ВентМонтаж"` |
| `segment` | enum | Сегмент клиента | MEDDIC | `installer \| contractor \| designer \| industrial` |
| `region` | string | Регион присутствия | BANT | `Самара, РФ` |
| `source` | string | Источник лида | — | `web_search \| referral \| inbound` |
| `score` | int | Скоринг лида (0-100) | MEDDIC | `78` |
| `status` | enum | Текущий статус | BANT | `new \| qualified \| proposal \| won \| lost` |
| `created_at` | timestamp | Дата создания лида | — | `2026-05-25T10:30:00Z` |
| `updated_at` | timestamp | Дата последнего обновления | — | `2026-05-25T14:22:00Z` |

---

### 2. Сущность: `interaction` (Взаимодействие / Сессия)
Фиксация каждого контакта с лидом (звонок, чат, встреча).

| Поле | Тип | Описание | Методология | Пример |
|------|-----|----------|-------------|--------|
| `interaction_id` | string | Уникальный идентификатор взаимодействия | — | `int_4c8e1d9a` |
| `lead_id` | string | Ссылка на лид | — | `lead_7f3a9b2c` |
| `channel` | enum | Канал коммуникации | SNAP | `voice \| chat \| email \| meeting` |
| `initiator` | enum | Кто инициировал контакт | Sandler | `manager \| client` |
| `duration_sec` | int | Длительность в секундах | — | `420` |
| `start_time` | timestamp | Время начала | — | `2026-05-25T14:00:00Z` |
| `outcome` | enum | Итог взаимодействия | AIDA | `next_step \| closed_won \| closed_lost \| deferred` |
| `next_step` | string | Согласованный следующий шаг | MEDDIC | `send_kp \| technical_meeting \| pilot_order` |
| `next_step_date` | date | Дата следующего шага | BANT | `2026-05-27` |
| `manager_id` | string | ID менеджера | — | `mgr_ivan_01` |

---

### 3. Сущность: `question_log` (Зафиксированный вопрос)
Вопросы, заданные менеджером или сгенерированные системой для квалификации.

| Поле | Тип | Описание | Методология | Пример |
|------|-----|----------|-------------|--------|
| `question_id` | string | Уникальный идентификатор вопроса | — | `q_9a2f5c1b` |
| `interaction_id` | string | Ссылка на взаимодействие | — | `int_4c8e1d9a` |
| `question_text` | string | Текст вопроса | SPIN | «Какой бюджет заложен на закупку?» |
| `methodology_tag` | enum | Привязка к методологии | SPIN/MEDDIC/BANT | `BANT_budget \| SPIN_problem \| MEDDIC_champion` |
| `category` | enum | Категория вопроса | — | `budget \| timeline \| pain \| decision_maker \| technical` |
| `asked_at` | timestamp | Время вопроса | — | `2026-05-25T14:03:12Z` |
| `client_response` | text | Ответ клиента (кратко) | Sandler | «Бюджет ~2 млн, но гибкий» |
| `response_sentiment` | enum | Тональность ответа | Challenger | `positive \| neutral \| negative \| evasive` |
| `qualification_value` | int | Ценность ответа для квалификации (0-10) | MEDDIC | `8` |

---

### 4. Сущность: `objection_log` (Зафиксированное возражение)
Возражения клиента и стратегия их отработки.

| Поле | Тип | Описание | Методология | Пример |
|------|-----|----------|-------------|--------|
| `objection_id` | string | Уникальный идентификатор возражения | — | `obj_3d7b8e4f` |
| `interaction_id` | string | Ссылка на взаимодействие | — | `int_4c8e1d9a` |
| `objection_text` | string | Текст возражения клиента | — | «Цена выше, чем у аналогов» |
| `objection_category` | enum | Категория возражения | Challenger | `price \| timeline \| quality \| trust \| competition` |
| `strategy_used` | string | Применённая стратегия отработки | Sandler/Challenger | `TCO_reframe \| reserve_supplier \| pilot_offer` |
| `response_text` | text | Ответ менеджера/системы | AIDA | «Давайте сравним стоимость владения...» |
| `resolved` | boolean | Было ли возражение снято | SNAP | `true` |
| `resolution_confidence` | int | Уверенность в снятии (0-100) | MEDDIC | `85` |
| `follow_up_needed` | boolean | Требуется ли доп. работа | BANT | `false` |

---

### 5. Сущность: `closing_attempt` (Попытка закрытия)
Фиксация призывов к действию и их результатов.

| Поле | Тип | Описание | Методология | Пример |
|------|-----|----------|-------------|--------|
| `closing_id` | string | Уникальный идентификатор попытки | — | `cls_6e1a4f2d` |
| `interaction_id` | string | Ссылка на взаимодействие | — | `int_4c8e1d9a` |
| `closing_type` | enum | Тип закрытия | AIDA | `soft_close \| direct_close \| after_objection \| situational` |
| `script_used` | string | Использованный скрипт (ID или краткое описание) | SNAP | `close_on_kp_send_v2` |
| `cta_text` | text | Текст призыва к действию | AIDA | «Отправить КП сегодня до 18:00?» |
| `client_reaction` | enum | Реакция клиента | Sandler | `agreed \| declined \| deferred \| no_response` |
| `success` | boolean | Удалось ли закрыть на следующий шаг | MEDDIC | `true` |
| `agreed_next_step` | string | Что согласовано в итоге | BANT | `kp_sent \| meeting_scheduled` |
| `barrier_if_failed` | string | Если не удалось — причина | Challenger | `budget_not_approved \| need_consult_lpr` |

---

### 6. Сущность: `analytics_snapshot` (Сводная аналитика по лиду)
Агрегированные метрики для быстрого скоринга и отчётности.

| Поле | Тип | Описание | Методология | Пример |
|------|-----|----------|-------------|--------|
| `snapshot_id` | string | Уникальный идентификатор снимка | — | `snap_8b3c2a1e` |
| `lead_id` | string | Ссылка на лид | — | `lead_7f3a9b2c` |
| `total_interactions` | int | Всего контактов | — | `3` |
| `questions_asked` | int | Задано квалификационных вопросов | SPIN | `12` |
| `objections_handled` | int | Отработано возражений | Challenger | `2` |
| `closing_attempts` | int | Попыток закрытия | AIDA | `1` |
| `meddic_score` | int | Сводный балл по MEDDIC (0-100) | MEDDIC | `72` |
| `bant_qualification` | object | Статус по компонентам BANT | BANT | `{budget: true, authority: false, need: true, timeline: true}` |
| `champion_identified` | boolean | Найден ли внутренний чемпион | MEDDIC | `true` |
| `last_activity` | timestamp | Дата последней активности | — | `2026-05-25T14:22:00Z` |
| `predicted_outcome` | enum | Прогноз исхода (опционально, пост-MVP) | ML | `likely_win \| likely_loss \| needs_nurture` |

---

## 🧩 Пример JSON для логирования (полный цикл)

```json
{
  "lead": {
    "lead_id": "lead_7f3a9b2c",
    "company_name": "ООО \"ВентМонтаж\"",
    "segment": "installer",
    "region": "Самара, РФ",
    "source": "web_search",
    "score": 78,
    "status": "qualified"
  },
  "interaction": {
    "interaction_id": "int_4c8e1d9a",
    "lead_id": "lead_7f3a9b2c",
    "channel": "voice",
    "initiator": "manager",
    "duration_sec": 420,
    "start_time": "2026-05-25T14:00:00Z",
    "outcome": "next_step",
    "next_step": "send_kp",
    "next_step_date": "2026-05-27",
    "manager_id": "mgr_ivan_01"
  },
  "questions": [
    {
      "question_id": "q_9a2f5c1b",
      "interaction_id": "int_4c8e1d9a",
      "question_text": "Какой бюджет заложен на закупку оборудования в этом квартале?",
      "methodology_tag": "BANT_budget",
      "category": "budget",
      "asked_at": "2026-05-25T14:03:12Z",
      "client_response": "Бюджет ~2 млн, но гибкий",
      "response_sentiment": "positive",
      "qualification_value": 8
    },
    {
      "question_id": "q_1b4e7d3a",
      "interaction_id": "int_4c8e1d9a",
      "question_text": "Что сейчас больше всего тормозит закупку или замену оборудования?",
      "methodology_tag": "Sandler_pain",
      "category": "pain",
      "asked_at": "2026-05-25T14:05:40Z",
      "client_response": "Сроки поставки у текущего поставщика",
      "response_sentiment": "neutral",
      "qualification_value": 9
    }
  ],
  "objections": [
    {
      "objection_id": "obj_3d7b8e4f",
      "interaction_id": "int_4c8e1d9a",
      "objection_text": "Цена выше, чем у аналогов",
      "objection_category": "price",
      "strategy_used": "TCO_reframe",
      "response_text": "Давайте сравним не только цену, но и стоимость владения: наши вентиляторы экономят до 18% на электричестве...",
      "resolved": true,
      "resolution_confidence": 85,
      "follow_up_needed": false
    }
  ],
  "closing_attempts": [
    {
      "closing_id": "cls_6e1a4f2d",
      "interaction_id": "int_4c8e1d9a",
      "closing_type": "soft_close",
      "script_used": "close_on_kp_send_v2",
      "cta_text": "Отправлю КП сегодня до 18:00. Чтобы оно было максимально полезным, уточните: под какой объект и какие параметры в приоритете?",
      "client_reaction": "agreed",
      "success": true,
      "agreed_next_step": "kp_sent",
      "barrier_if_failed": null
    }
  ]
}
```

---

## 📊 Аналитические срезы для отчётности (пост-MVP)

| Срез | Метрики | Методология | Цель |
|------|---------|-------------|------|
| Эффективность вопросов | Конверсия ответа → квалификация по каждому `methodology_tag` | SPIN / MEDDIC | Оптимизировать банк вопросов |
| Отработка возражений | % снятых возражений по `objection_category` и `strategy_used` | Challenger / Sandler | Выявить лучшие стратегии |
| Закрытие сделок | Конверсия `closing_type` → success | AIDA / BANT | Улучшить скрипты закрытия |
| Воронка квалификации | Доля лидов, прошедших каждый этап BANT/MEDDIC | BANT / MEDDIC | Найти узкие места в процессе |
| Сегментный анализ | Конверсия по `segment` и `region` | SNAP | Адаптировать подход под сегменты |
| Прогнозирование | Точность `predicted_outcome` vs фактический результат | ML (пост-MVP) | Автоматизировать скоринг |

---

## 🔐 Требования к хранению и доступу

| Аспект | Требование |
|--------|------------|
| Конфиденциальность | Персональные данные (ФИО, телефоны) хранятся в зашифрованном виде; доступ по ролям (менеджер — только свои лиды, РОП — все) |
| Актуальность | Данные обновляются в реальном времени при каждом взаимодействии; агрегированные метрики пересчитываются раз в сутки |
| Ретенция | Детальные логи хранятся 12 месяцев; агрегированные метрики — бессрочно |
| Экспорт | Возможность выгрузки в CSV/JSON для внешней аналитики (по запросу РОПа) |
| Аудит | Логирование изменений статусов и ключевых полей лида (кто, когда, что изменил) |

---

## ❓ FAQ по использованию схемы

**В:** Обязательно ли заполнять все поля?  
**О:** Для MVP — только обязательные: `lead_id`, `interaction_id`, `question_text`/`objection_text`/`cta_text`, `outcome`. Остальные — по возможности.

**В:** Кто заполняет данные: менеджер или система?  
**О:** Гибридно: система автоматически логирует временные метки, ID, скрипты; менеджер кратко фиксирует ответы клиента и реакции (1-2 клика или голосом).

**В:** Как использовать данные для обучения модели?  
**О:** После накопления 100+ взаимодействий можно: 1) выявить паттерны успешных диалогов; 2) дообучить промпты на реальных ответах; 3) оптимизировать скоринг лидов.

**В:** Можно ли изменить схему позже?  
**О:** Да. Схема версионируется (`sales_analytics_schema_v1`). При изменениях старые данные мигрируются или помечаются `schema_version`.

---

## 🔗 Ссылки на связанные документы

- `sales_questions_bank.md` — источник вопросов для логирования
- `sales_objections.md` — справочник стратегий отработки возражений
- `sales_closing.md` — библиотека скриптов закрытия
- `segment_*.md` — контекст для сегментной аналитики
- `system_analytics_guide.md` — инструкция по интерпретации метрик

---

## 🏷 Ключевые слова для поиска

аналитика, логирование, схема данных, квалификация, метрики, воронка, конверсия, SPIN, MEDDIC, BANT, Sandler, Challenger, SNAP, AIDA, вопрос, возражение, закрытие, взаимодействие, лид, скоринг, отчётность, НЕВАТОМ, вентиляция, B2B, продажи