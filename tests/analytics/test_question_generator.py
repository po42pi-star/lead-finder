import uuid
from pathlib import Path

import pytest

from core.analytics.question_generator import QuestionGenerator
from core.config.settings import Settings


@pytest.mark.asyncio
async def test_questions_from_bank(tmp_path):
    sales_dir = tmp_path / "sales"
    sales_dir.mkdir()
    (sales_dir / "sales_questions_bank.md").write_text(
        """---
doc_id: sales_questions_bank_v1
category: sales
---
# Bank
1. **Какой бюджет заложен на закупку?**
2. **Когда планируется запуск объекта?**
""",
        encoding="utf-8",
    )
    settings = Settings.model_construct(
        rag_docs_path=tmp_path,
        openai_api_key="",
    )
    generator = QuestionGenerator(settings, pipeline=None)
    questions = await generator.generate(
        lead_id=uuid.uuid4(),
        segment="installer",
        company_name='ООО "Тест"',
        region="Самара",
        user_role="rop",
    )
    assert len(questions) >= 2
    assert "бюджет" in questions[0]["text"].lower()
