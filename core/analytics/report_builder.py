from core.analytics.schemas import AnalyticsBlock, AnalyticsItem, ConfidenceLevel
from core.db.models import LeadORM

SEGMENT_TITLES = {
    "installer": "монтаж",
    "designer": "проектирование",
    "contractor": "генподряд",
    "industrial": "промышленность",
}


class ReportBuilder:
    def build_mandatory(self, lead: LeadORM) -> dict[str, AnalyticsBlock]:
        raw = lead.raw_data or {}
        okved = ", ".join(lead.okved_codes or []) or "не указан"
        return {
            "financial": AnalyticsBlock(
                title="Финансовые признаки",
                summary=self._financial_summary(lead),
                items=[
                    AnalyticsItem(
                        text=f"Оборот: {float(lead.turnover_mln)} млн ₽" if lead.turnover_mln else "Оборот: нет данных",
                        confidence=ConfidenceLevel.OK if lead.turnover_mln else ConfidenceLevel.WARNING,
                        source=lead.source,
                    ),
                    AnalyticsItem(
                        text="Сайт компании указан" if lead.website else "Сайт не обнаружен",
                        confidence=ConfidenceLevel.OK if lead.website else ConfidenceLevel.WARNING,
                        source="website_check",
                    ),
                    AnalyticsItem(
                        text="Признаки активности за 6 мес. (вакансии/новости)",
                        confidence=ConfidenceLevel.OK if raw.get("web_active_6m") else ConfidenceLevel.WARNING,
                        source="web_monitoring",
                    ),
                ],
            ),
            "tenders": AnalyticsBlock(
                title="Тендерная активность",
                summary=self._tender_summary(lead, raw),
                items=[
                    AnalyticsItem(
                        text=raw.get("tender_summary", "Данные по тендерам уточняются из zakupki.gov.ru"),
                        confidence=ConfidenceLevel.OK if raw.get("has_tenders_12m") else ConfidenceLevel.WARNING,
                        source="zakupki.gov.ru",
                    ),
                ],
            ),
            "technical": AnalyticsBlock(
                title="Техническая совместимость",
                summary=f"ОКВЭД: {okved}",
                items=[
                    AnalyticsItem(
                        text=f"Сегмент: {SEGMENT_TITLES.get(lead.segment, lead.segment)}",
                        confidence=ConfidenceLevel.OK,
                        source="profile_match",
                    ),
                    AnalyticsItem(
                        text="Упоминание вентиляции/ОВиК" if raw.get("vent_mention") else "Упоминание вентиляции не найдено",
                        confidence=ConfidenceLevel.OK if raw.get("vent_mention") else ConfidenceLevel.WARNING,
                        source="site_parse",
                    ),
                    AnalyticsItem(
                        text=f"Регион проектов: {lead.region or 'не указан'}",
                        confidence=ConfidenceLevel.OK if lead.region else ConfidenceLevel.WARNING,
                        source="registry",
                    ),
                ],
            ),
            "contacts": AnalyticsBlock(
                title="Контакты и ЛПР",
                summary=self._contacts_summary(lead),
                items=[
                    AnalyticsItem(
                        text=lead.contact_name or "ЛПР не определён",
                        confidence=ConfidenceLevel.OK if lead.contact_name else ConfidenceLevel.WARNING,
                        source="site_or_tender",
                    ),
                    AnalyticsItem(
                        text=lead.contact_phone or lead.contact_email or "Контактные данные не найдены",
                        confidence=ConfidenceLevel.OK if lead.contact_phone or lead.contact_email else ConfidenceLevel.ERROR,
                        source="site_or_tender",
                    ),
                ],
            ),
            "risks": AnalyticsBlock(
                title="Риски",
                summary="Нет признаков ликвидации/банкротства" if raw.get("not_bankrupt", True) else "Требуется проверка рисков",
                items=[
                    AnalyticsItem(
                        text="Признаки ликвидации не обнаружены",
                        confidence=ConfidenceLevel.OK,
                        source="fns_egrul",
                    ),
                    AnalyticsItem(
                        text="Исполнительные производства: данных нет (MVP)",
                        confidence=ConfidenceLevel.WARNING,
                        source="fssp_placeholder",
                    ),
                ],
            ),
        }

    def build_optional(
        self,
        lead: LeadORM,
        questions: list[dict],
    ) -> dict:
        segment = lead.segment
        hypotheses = self._product_hypotheses(segment, lead)
        checklist = self._checklist(segment, lead)
        competitors = self._competitors(lead)
        return {
            "product_hypotheses": AnalyticsBlock(
                title="Гипотезы по продуктам",
                items=[AnalyticsItem(text=item, source="product_match") for item in hypotheses],
            ).model_dump(),
            "questions": questions,
            "competitors": AnalyticsBlock(
                title="Конкурентный контекст",
                items=[AnalyticsItem(text=item, source="open_sources") for item in competitors],
            ).model_dump(),
            "checklist": AnalyticsBlock(
                title="Чек-лист подготовки к звонку",
                items=[AnalyticsItem(text=item, source="playbook") for item in checklist],
            ).model_dump(),
        }

    @staticmethod
    def _financial_summary(lead: LeadORM) -> str:
        if lead.turnover_mln and lead.turnover_mln >= 200:
            return "✅ Активен"
        if lead.turnover_mln and lead.turnover_mln >= 50:
            return "✅ Активен"
        if lead.website:
            return "⚠️ Слабая активность"
        return "❌ Нет данных"

    @staticmethod
    def _tender_summary(lead: LeadORM, raw: dict) -> str:
        if raw.get("tender_summary"):
            return str(raw["tender_summary"])
        if raw.get("has_tenders_12m"):
            return "Участие в госзакупках за 12 мес. подтверждено"
        return "Тендерная активность не подтверждена"

    @staticmethod
    def _contacts_summary(lead: LeadORM) -> str:
        parts = []
        if lead.contact_name:
            parts.append(lead.contact_name)
        if lead.contact_phone:
            parts.append(lead.contact_phone)
        return " | ".join(parts) if parts else "ЛПР требует уточнения"

    @staticmethod
    def _product_hypotheses(segment: str, lead: LeadORM) -> list[str]:
        mapping = {
            "installer": [
                "Канальные вентиляторы для объектов текущего монтажа",
                "Воздуховоды и фасонные элементы под сроки объекта",
                "Автоматика, если в тендере есть диспетчеризация",
            ],
            "designer": [
                "ПВУ и вентиляционные установки под проектные спецификации",
                "Клапаны и автоматика для согласования с ТЗ",
            ],
            "contractor": [
                "Комплексное предложение ПВУ + воздуховоды + монтажные аксессуары",
                "Промышленные вентиляторы для крупных объектов",
            ],
            "industrial": [
                "Промышленные вентиляторы для цехов",
                "Взрывозащищённое/пищевое исполнение при спецтребованиях",
            ],
        }
        base = mapping.get(segment, mapping["installer"])
        if lead.turnover_mln and lead.turnover_mln >= 100:
            base.append("Индивидуальные условия логистики и отгрузки за 24–48 ч")
        return base

    @staticmethod
    def _checklist(segment: str, lead: LeadORM) -> list[str]:
        items = [
            "Уточнить сроки сдачи объекта и окно закупки",
            "Подготовить КП с акцентом на сроки отгрузки НЕВАТОМ",
            "Предложить бесплатную консультацию инженера",
        ]
        if not lead.contact_name:
            items.insert(0, "Определить ЛПР (техдиректор / закупки / ГИП)")
        if segment == "designer":
            items.append("Запросить проектную документацию/спецификацию")
        return items

    @staticmethod
    def _competitors(lead: LeadORM) -> list[str]:
        raw_text = str(lead.raw_data).lower()
        hints = []
        for brand in ("systemair", "vts", "rivacold", "ruvent", "вентс"):
            if brand in raw_text:
                hints.append(f"На источниках упоминается: {brand}")
        if not hints:
            hints.append("Прямые упоминания конкурентов не найдены — уточнить на звонке")
        return hints
