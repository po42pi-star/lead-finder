import re
import uuid
from pathlib import Path

from core.config.settings import Settings
from core.rag.models import DocumentCategory, SearchRequest, UserRole
from core.rag.retrieval import RetrievalPipeline


SEGMENT_DOC = {
    "installer": "segment_installers.md",
    "designer": "segment_designers.md",
    "contractor": "segment_contractors.md",
    "industrial": "segment_industrial.md",
}

QUESTION_PATTERN = re.compile(
    r"^\d+\.\s+\*\*(.+?)\*\*\s*$",
    re.MULTILINE,
)


class QuestionGenerator:
    def __init__(self, settings: Settings, pipeline: RetrievalPipeline | None = None) -> None:
        self._settings = settings
        self._pipeline = pipeline
        self._bank_path = settings.rag_docs_path / "sales" / "sales_questions_bank.md"

    async def generate(
        self,
        *,
        lead_id: uuid.UUID,
        segment: str,
        company_name: str,
        region: str | None,
        user_role: str,
    ) -> list[dict]:
        from_bank = self._from_question_bank(segment, company_name, region)
        if len(from_bank) >= 10:
            return from_bank[:12]

        if self._pipeline and self._settings.openai_api_key:
            rag_questions = await self._from_rag(segment, company_name, user_role)
            merged = from_bank + rag_questions
            seen: set[str] = set()
            unique: list[dict] = []
            for item in merged:
                key = item["text"].lower()
                if key in seen:
                    continue
                seen.add(key)
                unique.append(item)
            return unique[:12]

        return from_bank[:10] if from_bank else self._fallback_questions(segment, company_name)

    def _from_question_bank(
        self,
        segment: str,
        company_name: str,
        region: str | None,
    ) -> list[dict]:
        if not self._bank_path.exists():
            return []
        content = self._bank_path.read_text(encoding="utf-8")
        questions = [match.group(1).strip() for match in QUESTION_PATTERN.finditer(content)]
        personalized = []
        for index, text in enumerate(questions[:15]):
            personalized.append(
                {
                    "question_id": str(uuid.uuid4()),
                    "text": self._personalize(text, company_name, region),
                    "source": "sales_questions_bank.md",
                    "methodology_tag": self._guess_methodology(text),
                    "category": self._guess_category(text),
                }
            )
        segment_file = SEGMENT_DOC.get(segment)
        if segment_file:
            segment_path = self._settings.rag_docs_path / "segments" / segment_file
            if segment_path.exists():
                segment_text = segment_path.read_text(encoding="utf-8")
                for line in segment_text.splitlines():
                    if line.strip().startswith("- ") and "?" in line:
                        text = line.strip()[2:].strip()
                        personalized.append(
                            {
                                "question_id": str(uuid.uuid4()),
                                "text": self._personalize(text, company_name, region),
                                "source": segment_file,
                                "methodology_tag": "SPIN_situation",
                                "category": "technical",
                            }
                        )
        return personalized

    async def _from_rag(self, segment: str, company_name: str, user_role: str) -> list[dict]:
        assert self._pipeline is not None
        query = (
            f"Сформируй 5 квалификационных вопросов для звонка компании {company_name} "
            f"сегмента {segment}. Используй sales_questions_bank и segment_{segment}."
        )
        try:
            role = UserRole(user_role)
        except ValueError:
            role = UserRole.MANAGER
        request = SearchRequest(
            query=query,
            user_role=role,
            category_override=DocumentCategory.SALES,
        )
        try:
            response, _ = await self._pipeline.search(request)
            lines = [
                line.strip(" -•\t")
                for line in response.answer.splitlines()
                if line.strip() and ("?" in line or line[0].isdigit())
            ]
            return [
                {
                    "question_id": str(uuid.uuid4()),
                    "text": line.lstrip("0123456789.").strip(),
                    "source": "rag:sales+segments",
                    "methodology_tag": "SPIN_problem",
                    "category": "pain",
                }
                for line in lines[:5]
                if len(line) > 10
            ]
        except Exception:
            return []

    def _fallback_questions(self, segment: str, company_name: str) -> list[dict]:
        templates = [
            f"Какие объекты {company_name} сейчас ведёт в работе?",
            "По какому графику планируется монтаж/поставка оборудования?",
            "Кто принимает финальное решение по выбору поставщика?",
            "Какой бюджет заложен на закупку в этом квартале?",
            "Есть ли сложности с текущими поставками вентиляционного оборудования?",
            "Рассматриваете ли альтернативных поставщиков?",
            "Какие критерии для вас важнее: цена, сроки или сервис?",
            "Нужна ли диспетчеризация/автоматика в проекте?",
            "Какие сроки сдачи объекта заложены?",
            "Можем ли подключить инженера НЕВАТОМ для бесплатной консультации?",
        ]
        return [
            {
                "question_id": str(uuid.uuid4()),
                "text": text,
                "source": f"fallback:{segment}",
                "methodology_tag": "BANT_need",
                "category": "timeline",
            }
            for text in templates
        ]

    @staticmethod
    def _personalize(text: str, company_name: str, region: str | None) -> str:
        result = text.replace("вашей компании", company_name).replace("в вашей компании", f"в {company_name}")
        if region and "объект" in result.lower():
            result = f"{result} (регион: {region})"
        return result

    @staticmethod
    def _guess_methodology(text: str) -> str:
        lower = text.lower()
        if "бюджет" in lower:
            return "BANT_budget"
        if "срок" in lower or "когда" in lower:
            return "BANT_timeline"
        if "кто" in lower or "лпр" in lower or "решение" in lower:
            return "MEDDIC_champion"
        if "боль" in lower or "тормозит" in lower:
            return "Sandler_pain"
        return "SPIN_situation"

    @staticmethod
    def _guess_category(text: str) -> str:
        lower = text.lower()
        if "бюджет" in lower:
            return "budget"
        if "срок" in lower or "когда" in lower:
            return "timeline"
        if "кто" in lower:
            return "decision_maker"
        if "критер" in lower:
            return "technical"
        return "pain"
