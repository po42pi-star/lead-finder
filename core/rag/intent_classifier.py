import json
import logging
import time
from typing import Any

from langchain_openai import ChatOpenAI
from openai import APITimeoutError, RateLimitError

from core.config.settings import Settings
from core.rag.models import AudienceRole, DocumentCategory, IntentResult, IntentType, UserRole

logger = logging.getLogger(__name__)

KEYWORD_CATEGORY_MAP: dict[DocumentCategory, list[str]] = {
    DocumentCategory.SYSTEM: [
        "как настроить",
        "интерфейс",
        "экспорт",
        "пароль",
        "роль",
        "faq",
        "систем",
        "скоринг",
        "шаблон",
        "поиск лидов",
        "фильтр поиска",
        "фильтры поиска",
        "настроить фильтр",
        "оквэд",
        "регион",
        "оборот",
        "аналитика",
        "дашборд",
        "метрики",
        "конверсия",
        "воронка",
        "отчёт",
        "лид",
        "hot",
        "warm",
        "cold",
        "qualified",
        "передать менеджеру",
        "статистика",
        "график",
    ],
    DocumentCategory.SALES: [
        "возражен",
        "закрыт",
        "вопрос",
        "spin",
        "meddic",
        "bant",
        "скрипт",
        "переговор",
        "возражение",
        "квалификац",
        "closing",
        "objection",
        "sandler",
        "challenger",
        "отработка",
        "аргумент",
        "склонить",
        "конкурент",
        "цена",
        "бюджет",
        "сделк",
        "клиент",
        "контакт",
        "звонок",
        "встреч",
        "кп",
        "коммерческое предложение",
        "согласование",
        "договор",
        "тендер",
    ],
    DocumentCategory.PRODUCT: [
        "вентилятор",
        "пву",
        "клапан",
        "воздуховод",
        "автоматик",
        "продукт",
        "характеристик",
        "подбор",
        "фильтр",
        "приточн",
        "вытяжн",
        "рекуперат",
        "калорифер",
        "дымосос",
        "заслонк",
        "диаметр",
        "расход",
        "давление",
        "квт",
        "м3",
        "м³",
        "производительность",
        "напор",
        "шум",
        "кпд",
        "секция",
        "теплообменник",
        "двигател",
        "подшипник",
        "установк",
        "система вентиляц",
        "техническое решение",
        "параметр",
        "исполнение",
        "маркировк",
        "сертификат",
        "гост",
    ],
    DocumentCategory.SEGMENTS: [
        "монтажник",
        "проектировщик",
        "подрядчик",
        "промышлен",
        "сегмент",
        "генподрядчик",
        "застройщик",
        "генподряд",
        "стройка",
        "объект",
        "прораб",
        "начальник участка",
        "снабжен",
        "технический директор",
        "проектирование",
        "монтажная организация",
        "профиль клиента",
        "боли",
        "лпр",
        "закупк",
        "смета",
        "подряд",
    ],
    DocumentCategory.COMPANY: [
        "логистик",
        "сертифик",
        "гарант",
        "сервис",
        "доставк",
        "компани",
        "производство",
        "завод",
        "контакт",
        "адрес",
        "представительство",
        "склад",
        "номенклатура",
        "мощность",
        "инженерный центр",
        "оплата",
        "срок изготовления",
        "отгрузка",
        "самовывоз",
        "манипулятор",
        "транспортн",
        "ндс",
        "договор",
        "счёт",
        "заказ",
        "наличие",
        "предзаказ",
        "запасные части",
        "зип",
        "ремонт",
        "то",
        "обслуживание",
        "расширенная гарантия",
        "сервисный контракт",
    ],
}


class IntentClassifier:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def classify(
        self,
        query: str,
        user_role: UserRole,
        category_override: DocumentCategory | None = None,
    ) -> IntentResult:
        if category_override:
            result = IntentResult(
                category=category_override,
                audience=[AudienceRole(user_role.value)],
                intent=IntentType.SEARCH,
            )
        elif self._settings.intent_use_llm and self._settings.openai_api_key:
            result = await self._classify_with_llm(query, user_role)
        else:
            result = self._classify_with_rules(query, user_role)

        logger.info("Classified query=%r as category=%s intent=%s", query, result.category.value, result.intent.value)
        return result

    def _classify_with_rules(self, query: str, user_role: UserRole) -> IntentResult:
        lowered = query.lower()
        scores: dict[DocumentCategory, int] = {
            category: 0 for category in DocumentCategory
        }
        for category, keywords in KEYWORD_CATEGORY_MAP.items():
            for keyword in keywords:
                if keyword in lowered:
                    scores[category] += 1

        best_category = max(scores, key=scores.get)
        if scores[best_category] == 0:
            best_category = DocumentCategory.SALES

        intent = IntentType.HELP if best_category == DocumentCategory.SYSTEM else IntentType.SEARCH
        if any(word in lowered for word in ("техническ", "характеристик", "подбор", "м³")):
            intent = IntentType.TECHNICAL

        logger.debug("Intent scores: %s", {k.value: v for k, v in scores.items()})
        return IntentResult(
            category=best_category,
            audience=[AudienceRole(user_role.value)],
            intent=intent,
        )

    async def _classify_with_llm(self, query: str, user_role: UserRole) -> IntentResult:
        prompt = (
            "Классифицируй запрос пользователя. Верни ТОЛЬКО JSON, без пояснений, без markdown.\n\n"
            "Допустимые категории (category):\n"
            "- system — вопросы по интерфейсу, настройкам, экспорту, ролям\n"
            "- product — вопросы о продуктах НЕВАТОМ (вентиляторы, ПВУ, клапаны)\n"
            "- sales — продажные скрипты, возражения, квалификация, закрытие\n"
            "- segments — работа с конкретными сегментами (монтажники, проектировщики)\n"
            "- company — логистика, гарантия, сертификация, поддержка\n\n"
            "Допустимые намерения (intent):\n"
            "- search — поиск информации\n"
            "- help — помощь по системе\n"
            "- technical — технический подбор/расчёт\n\n"
            "Примеры:\n"
            'Запрос: «Как экспортировать в Excel?» → {"category": "system", "audience": ["rop"], "intent": "help"}\n'
            'Запрос: «Какие вопросы задать монтажнику?» → {"category": "sales", "audience": ["manager"], "intent": "search"}\n'
            'Запрос: «Подберите вентилятор для 5000 м³/ч» → {"category": "product", "audience": ["manager"], "intent": "technical"}\n\n'
            'Формат ответа: {"category": "...", "audience": ["..."], "intent": "..."}'
        )
        llm = ChatOpenAI(
            model=self._settings.openai_chat_model,
            api_key=self._settings.openai_api_key,
            base_url=self._settings.openai_base_url,
            temperature=0,
            max_retries=0,
        )
        attempt = 0
        while True:
            try:
                response = await llm.ainvoke(
                    [
                        ("system", prompt),
                        ("user", f"Запрос: {query}\nРоль: {user_role.value}"),
                    ]
                )
                payload = self._parse_llm_json(str(response.content))
                return IntentResult(
                    category=DocumentCategory(payload["category"]),
                    audience=[
                        AudienceRole(item) for item in payload.get("audience", [user_role.value])
                    ],
                    intent=IntentType(payload.get("intent", IntentType.SEARCH.value)),
                )
            except (RateLimitError, APITimeoutError) as exc:
                attempt += 1
                if attempt > self._settings.openai_max_retries:
                    logger.warning("Intent LLM failed, falling back to rules: %s", exc)
                    return self._classify_with_rules(query, user_role)
                await self._sleep_backoff(attempt)
            except (json.JSONDecodeError, KeyError, ValueError) as exc:
                logger.warning("Intent LLM parse failed, falling back to rules: %s", exc)
                return self._classify_with_rules(query, user_role)

    async def _sleep_backoff(self, attempt: int) -> None:
        import asyncio

        delay = self._settings.openai_retry_base_delay_sec * (2 ** (attempt - 1))
        await asyncio.sleep(delay)

    @staticmethod
    def _parse_llm_json(content: str) -> dict[str, Any]:
        start = content.find("{")
        end = content.rfind("}")
        if start < 0 or end < 0:
            raise json.JSONDecodeError("No JSON object", content, 0)
        return json.loads(content[start : end + 1])

