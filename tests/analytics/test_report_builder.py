import uuid
from decimal import Decimal

from core.analytics.report_builder import ReportBuilder
from core.db.models import LeadORM


def test_build_mandatory_blocks():
    lead = LeadORM(
        id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        company_name='ООО "Тест"',
        segment="installer",
        region="Самара",
        source="demo",
        score=78,
        score_breakdown=[],
        turnover_mln=Decimal("120"),
        employees=50,
        website="https://example.com",
        contact_name="Иванов П.",
        contact_phone="+7 846 000-00-00",
        okved_codes=["43.22"],
        raw_data={"vent_mention": True, "has_tenders_12m": True, "not_bankrupt": True},
    )
    blocks = ReportBuilder().build_mandatory(lead)
    assert "financial" in blocks
    assert "tenders" in blocks
    assert blocks["contacts"].summary
